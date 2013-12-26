from django.core.exceptions import ImproperlyConfigured
try:
    import restlib2  # noqa
    import preserialize  # noqa
except ImportError:
    raise ImproperlyConfigured('restlib2 and django-preserialize must be '
                               'installed to use the resource classes')

from django.conf.urls import patterns, url
from django.http import HttpResponse
from restlib2.resources import Resource
from restlib2.http import codes
from restlib2.params import Parametizer, BoolParam
from preserialize.serialize import serialize
from .models import ObjectSet, SetObject
from .forms import objectset_form_factory


SET_OPERATIONS = {
    'and': '__and__',
    'or': '__or__',
    'xor': '__xor__',
    'sub': '__sub__',
}

INPLACE_SET_OPERATIONS = {
    'and': '__iand__',
    'or': '__ior__',
    'xor': '__ixor__',
    'sub': '__isub__',
}


def set_objects_prehook(queryset):
    "Prehook for set objects to exclude tracked deleted objects."
    if issubclass(queryset.model, SetObject):
        queryset = queryset.exclude(removed=True)
    return queryset


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
        # TODO
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
            instance = form.save()
            params = self.get_params(request)
            template = self.get_serialize_template(request, **params)
            return serialize(instance, **template)
        return HttpResponse(dict(form.errors),
                            status=codes.unprocessable_enity)


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
            form.save()
            return HttpResponse(status=codes.no_content)
        return HttpResponse(dict(form.errors),
                            status=codes.unprocessable_enity)

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


def get_url_patterns(Model, resources=None, prefix=None):
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

    # Define a prefix for the url names to prevent conflicts
    if not prefix:
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
