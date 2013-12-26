from django import forms
from .models import ObjectSet


def objectset_form_factory(Model, queryset=None):
    """Takes an ObjectSet subclass and defines a base form class.

    In addition, an optional queryset can be supplied to limit the choices
    for the objects.

    This uses the generic `objects` field rather being named after a specific
    type.
    """
    # A few checks to keep things sane..
    if not issubclass(Model, ObjectSet):
        raise TypeError('{0} must subclass ObjectSet'.format(Model.__name__))

    instance = Model()

    if queryset is None:
        queryset = instance._object_class._default_manager.all()
    elif queryset.model is not instance._object_class:
        raise TypeError('ObjectSet of type {0}, not {1}'
                        .format(instance._object_class.__name__,
                                queryset.model.__name__))

    label = getattr(Model, instance._set_object_rel).field.verbose_name

    class form_class(forms.ModelForm):
        objects = forms.ModelMultipleChoiceField(queryset, label=label,
                                                 required=False)

        def save(self, *args, **kwargs):
            self.instance._pending = self.cleaned_data.get('objects')
            return super(form_class, self).save(*args, **kwargs)

        class Meta(object):
            model = Model
            exclude = (instance._set_object_rel,)

    form_class.__name__ = '{0}Form'.format(Model.__name__)

    return form_class
