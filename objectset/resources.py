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
from restlib2.params import Parametizer, param_cleaners
from preserialize.serialize import serialize

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


class SetParametizer(Parametizer):
    embed = False

    def clean_embed(self, value):
        return param_cleaners.clean_bool(value)


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
        template = self.template or {}
        relation = self.model._set_object_rel

        if kwargs.get('embed', False):
            template.setdefault('exclude', [relation])
        elif self.object_template:
            template.setdefault('related', {})
            if relation not in template['related']:
                template['related'][relation] = self.object_template

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
        instance = self.get_object(pk=pk)
        if instance is None:
            return True
        request.instance = instance

    def get(self, request, pk):
        return serialize(request.instance, **self.template)

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
    pass


class SetOperationsResource(BaseSetResource):
    def post(request, pk, *args):
        pass


def get_url_patterns(resources):
    """Returns urlpatterns for the defined resources.

    `resources` is a dict corresponding to each resource:

        - `sets` => SetsResource
        - `set` => SetResource
        - `operations` => SetOperatiosnResource
        - `objects` => SetObjectsResource

    """
    return patterns(
        '',
        url(r'^$', resources['sets'](), name='sets'),
        url(r'^(?P<pk>\d+)/$', resources['set'](), name='set'),
        url(r'^(?P<pk>\d+)/objects/$', resources['objects'](), name='objects'),
        url(r'^(?P<pk>\d+)/(?:(and|or|xor|sub)/(\d+)/)+/$',
            resources['operations'](), name='operations'),
    )
