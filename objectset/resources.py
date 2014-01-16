from django.core.exceptions import ImproperlyConfigured
try:
    import restlib2  # noqa
    import preserialize  # noqa
except ImportError:
    raise ImproperlyConfigured('restlib2 and django-preserialize must be '
                               'installed to use the resource classes')

from functools import partial
from django.conf.urls import patterns, url
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from restlib2.resources import Resource
from restlib2.http import codes
from restlib2.params import Parametizer, BoolParam
from preserialize.serialize import serialize
from .models import ObjectSet
from .forms import objectset_form_factory


SET_OPERATORS = {
    'and': '__iand__',
    'or': '__ior__',
    'xor': '__ixor__',
    'sub': '__isub__',
}


def apply_operations(instance, operations, queryset=None):
    """Applies a series of operations to an existing instance.

    The operation syntax is:

        {
            'set': <id> | [...],
            'operator': 'and' | 'or' | 'xor' | 'sub',
        }

    where `set` can be the primary key of an existing set or a list of
    object primary keys to be treated as a temporary set for the operation.
    `operator` is one of the supported set operators.
    """

    # Derive a queryset of available sets
    if queryset is None:
        queryset = instance.__class__.objects.all()

    for operation in operations:
        operand = operation.get('set')
        operator = operation.get('operator')

        # Ensure this is a valid operation
        if operator not in SET_OPERATORS:
            raise ValueError('Invalid set operation')

        if operand is None:
            raise ValueError('Set operand cannot be empty')

        # Treat operand as set id
        elif isinstance(operand, int):
            try:
                operand = queryset.get(pk=operand)
            except queryset.model.DoesNotExist:
                raise ValueError('Set operand does not exist')

        # Treat operand as list of object ids
        elif isinstance(operand, (list, tuple)):
            operand = queryset.model(operand)

        else:
            raise ValueError('Unknown operand type')

        # Apply operation
        getattr(instance, SET_OPERATORS[operator])(operand)

    return instance


class SetParametizer(Parametizer):
    embed = BoolParam()


class BaseSetResource(Resource):
    parametizer = SetParametizer

    model = None

    template = None

    object_template = None

    form_class = None

    url_names = None

    url_reverse_names = None

    def set_links_posthook(self, instance, attrs, request):
        uri = request.build_absolute_uri

        attrs['_links'] = {
            'self': {
                'href': uri(reverse(self.url_reverse_names['set'],
                            kwargs={'pk': instance.pk}))
            },
            'parent': {
                'href': uri(reverse(self.url_reverse_names['sets']))
            },
            'objects': {
                'href': uri(reverse(self.url_reverse_names['objects'],
                            kwargs={'pk': instance.pk})),
            },
        }
        return attrs

    def get_params(self, request):
        return self.parametizer().clean(request.GET)

    def get_serialize_object_template(self, request, **kwargs):
        "Prepare the object serialize template."
        if self.object_template:
            object_template = self.object_template
        else:
            object_template = {
                'fields': [':local'],
            }
        return object_template

    def get_serialize_template(self, request, **kwargs):
        "Prepare the serialize template"
        instance = self.model()
        relation = instance._set_object_rel

        object_template = self.get_serialize_object_template(request, **kwargs)

        if self.template:
            template = self.template
        else:
            # Use the generic 'objects' key for the target relation.
            # This makes it simpler to consume by clients
            template = {
                'fields': [':local', 'objects'],
                'exclude': [relation],
                'posthook': partial(self.set_links_posthook, request=request),
                'aliases': {
                    'objects': relation,
                },
                'related': {
                    relation: object_template,
                }
            }

            # If it is requested to not be embedded, exclude the target
            # relation and the 'objects' alias from the template
            if not kwargs.get('embed', False):
                template['exclude'].append('objects')

        return template

    def get_queryset(self, request):
        return self.model.objects.all()

    def get_object(self, request, **kwargs):
        try:
            return self.get_queryset(request).get(**kwargs)
        except self.model.DoesNotExist:
            pass


class SetsResource(BaseSetResource):
    def get(self, request):
        params = self.get_params(request)
        template = self.get_serialize_template(request, **params)
        return serialize(self.get_queryset(request), **template)

    def post(self, request):
        form = self.form_class(request.data)

        if form.is_valid():
            instance = form.save(commit=False)

            if 'operations' in request.data and request.data['operations']:
                queryset = self.get_queryset(request)
                try:
                    apply_operations(instance, request.data['operations'],
                                     queryset=queryset)
                except ValueError:
                    return HttpResponse(status=codes.unprocessable_entity)
            instance.save()
            params = self.get_params(request)
            template = self.get_serialize_template(request, **params)

            return serialize(instance, **template)

        return HttpResponse(dict(form.errors),
                            status=codes.unprocessable_entity)


class SetResource(BaseSetResource):
    def is_not_found(self, request, response, pk):
        instance = self.get_object(request, pk=pk)
        if instance is None:
            return True
        request.instance = instance

    def get(self, request, pk):
        params = self.get_params(request)
        template = self.get_serialize_template(request, **params)
        return serialize(request.instance, **template)

    def put(self, request, pk):
        form = self.form_class(request.data, instance=request.instance)

        if form.is_valid():
            instance = form.save(commit=False)

            if 'operations' in request.data and request.data['operations']:
                queryset = self.get_queryset(request)
                try:
                    apply_operations(instance, request.data['operations'],
                                     queryset=queryset)
                except ValueError:
                    return HttpResponse(status=codes.unprocessable_entity)
            instance.save()

            return HttpResponse(status=codes.no_content)

        return HttpResponse(dict(form.errors),
                            status=codes.unprocessable_entity)

    def delete(self, request, pk):
        request.instance.delete()
        return HttpResponse(status=codes.no_content)


class SetObjectsResource(BaseSetResource):
    def is_not_found(self, request, response, pk):
        instance = self.get_object(request, pk=pk)
        if instance is None:
            return True
        request.instance = instance

    def get(self, request, pk):
        queryset = request.instance.objects
        params = self.get_params(request)
        template = self.get_serialize_object_template(request, **params)
        return serialize(queryset, **template)


def get_url_patterns(Model, resources=None, prefix=''):
    """Returns urlpatterns for the defined resources.

    `resources` is a dict corresponding to each resource:

        - `base` => BaseSetResource
        - `sets` => SetsResource
        - `set` => SetResource
        - `objects` => SetObjectsResource

    If only the `base` is provided, the three other classes will be defined
    using the base class.

    `prefix` will be prepended to the URL paths.
    """
    # A few checks to keep things sane..
    if not issubclass(Model, ObjectSet):
        raise TypeError('{0} must subclass ObjectSet'.format(Model.__name__))

    if not resources:
        resources = {}

    # Define missing classes
    if 'base' not in resources:
        model_name = Model.__name__.lower()

        url_names = {
            'set': model_name,
            'sets': model_name,
            'objects': '{0}-objects'.format(model_name),
        }

        base_class = type('BaseSetResource', (BaseSetResource,), {
            'model': Model,
            'form_class': objectset_form_factory(Model),
            'url_names': url_names,
            'url_reverse_names': url_names.copy(),
        })

        resources['base'] = base_class

    if 'sets' not in resources:
        bases = (resources['base'], SetsResource)
        resources['sets'] = type('SetsResource', bases, {})

    if 'set' not in resources:
        bases = (resources['base'], SetResource)
        resources['set'] = type('SetResource', bases, {})

    if 'objects' not in resources:
        bases = (resources['base'], SetObjectsResource)
        resources['objects'] = type('SetObjectsResource', bases, {})

    url_names = getattr(resources['base'], 'url_names', None)
    url_reverse_names = getattr(resources['base'], 'url_reverse_names', None)

    # If url_names are not defined, assume the url_reverse_names can be used.
    # url_reverse_names may be different if the urls are namespaced.
    if not url_names:
        if not url_reverse_names:
            raise AttributeError('url_names or url_reverse_names must be '
                                 'defined on the BaseSetResource class')
        url_names = url_reverse_names

    if prefix and not prefix.endswith('/'):
        prefix = prefix + '/'

    return patterns(
        '',

        url(r'^{0}$'.format(prefix),
            resources['sets'](), name=url_names['sets']),

        url(r'^{0}(?P<pk>\d+)/$'.format(prefix),
            resources['set'](), name=url_names['set']),

        url(r'^{0}(?P<pk>\d+)/objects/$'.format(prefix),
            resources['objects'](), name=url_names['objects']),
    )
