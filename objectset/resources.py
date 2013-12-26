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
from .models import ObjectSet, SetObject
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


def set_objects_prehook(queryset):
    "Prehook for set objects to exclude tracked deleted objects."
    if issubclass(queryset.model, SetObject):
        queryset = queryset.exclude(removed=True)
    return queryset


def set_links_posthook(instance, attrs, request):
    uri = request.build_absolute_uri
    # This prefix is intended to be shared across resources for the same
    # set type
    prefix = '{0}-'.format(instance.__class__.__name__.lower())

    attrs['_links'] = {
        'self': {
            'href': uri(reverse('{0}set'.format(prefix),
                        kwargs={'pk': instance.pk}))
        },
        'objects': {
            'href': uri(reverse('{0}objects'.format(prefix),
                        kwargs={'pk': instance.pk})),
        },
    }
    return attrs


class SetParametizer(Parametizer):
    embed = BoolParam()


class BaseSetResource(Resource):
    parametizer = SetParametizer

    model = None

    template = None

    object_template = None

    form_class = None

    def get_params(self, request):
        return self.parametizer().clean(request.GET)

    def get_serialize_template(self, request, **kwargs):
        "Prepare the serialize template"
        instance = self.model()
        relation = instance._set_object_rel

        if self.object_template:
            object_template = self.object_template
        else:
            object_template = {
                'fields': [':local'],
                'prehook': set_objects_prehook,
            }

        if self.template:
            template = self.template
        else:
            # Use the generic 'objects' key for the target relation.
            # This makes it simpler to consume by clients
            template = {
                'fields': [':local', 'objects'],
                'exclude': [relation],
                'posthook': partial(set_links_posthook, request=request),
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

    def get_serialize_template(self, request, **kwargs):
        return {'fields': [':local']}

    def get(self, request, pk):
        queryset = request.instance._objects
        params = self.get_params(request)
        template = self.get_serialize_template(request, **params)
        return serialize(queryset, **template)


def get_url_patterns(Model, resources=None):
    """Returns urlpatterns for the defined resources.

    `resources` is a dict corresponding to each resource:

        - `sets` => SetsResource
        - `set` => SetResource
        - `objects` => SetObjectsResource

    """
    # A few checks to keep things sane..
    if not issubclass(Model, ObjectSet):
        raise TypeError('{0} must subclass ObjectSet'.format(Model.__name__))

    if not resources:
        resources = {}

    default_form_class = objectset_form_factory(Model)

    if 'sets' not in resources:
        class DefaultSetsResource(SetsResource):
            model = Model
            form_class = default_form_class

        resources['sets'] = DefaultSetsResource

    if 'set' not in resources:
        class DefaultSetResource(SetResource):
            model = Model
            form_class = default_form_class

        resources['set'] = DefaultSetResource

    if 'objects' not in resources:
        class DefaultSetObjectsResource(SetObjectsResource):
            model = Model
            form_class = default_form_class

        resources['objects'] = DefaultSetObjectsResource

    prefix = '{0}-'.format(Model.__name__.lower())

    return patterns(
        '',
        url(r'^$', resources['sets'](),
            name='{0}sets'.format(prefix)),
        url(r'^(?P<pk>\d+)/$', resources['set'](),
            name='{0}set'.format(prefix)),
        url(r'^(?P<pk>\d+)/objects/$', resources['objects'](),
            name='{0}objects'.format(prefix)),
    )
