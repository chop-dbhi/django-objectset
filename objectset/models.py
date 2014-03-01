import django
from datetime import datetime
from django.db import models, transaction
from django.db.models.query import QuerySet, EmptyQuerySet
from django.db.models.manager import ManagerDescriptor
from django.core.exceptions import ImproperlyConfigured
from .exceptions import ObjectSetError
from .decorators import cached_property

BULK_SUPPORTED = django.VERSION >= (1, 4)


class ObjectSetManagerDescriptor(ManagerDescriptor):
    """Manager descriptor customized to allow model instances to access the
    `objects` property. This returns a QuerySet of the objects the set
    contains.
    """
    def __init__(self, manager):
        self.manager = manager

    def __get__(self, instance, type=None):
        if instance is not None:
            return instance._objects()
        return super(ObjectSetManagerDescriptor, self).__get__(instance, type)


class ObjectSetManager(models.Manager):
    "Manager for the `ObjectSet` model."
    def contribute_to_class(self, model, name):
        "Override to use custom manager descriptor."
        super(ObjectSetManager, self).contribute_to_class(model, name)
        setattr(model, name, ObjectSetManagerDescriptor(self))


class ObjectSet(models.Model):
    """Encapsulates a set of objects of a particular type and provides
    common set operations such as union, intersection, and difference.

    `ObjectSet` must be subclassed to add the many-to-many relationship
    to the _object_ of interest.

    The method docstrings below will use the example of a Team and Players
    where `Team` is the set, `Player` is the object, and `TeamPlayer` is
    the many-to-many table.

        Team <- TeamPlayer -> Player
    """
    # Stored count of the set size. Since most operations are incremental
    # and are applied with objects in memory, this is a more efficient
    # way to keep track of the count as suppose to performing a database
    # count each time.
    count = models.PositiveIntegerField(default=0, editable=False)
    created = models.DateTimeField(default=datetime.now, editable=False)
    modified = models.DateTimeField(default=datetime.now, editable=False)

    # Custom manager to give instance-level access to `objects` which returns
    # the objects this set contains. This proxies to `_objects()`
    objects = ObjectSetManager()

    class Meta(object):
        abstract = True

    @transaction.commit_on_success
    def __init__(self, *args, **kwargs):
        # Set to an empty queryset
        self._pending = self._object_class.objects.none()

        queryset = None
        save = kwargs.pop('save', False)

        # Assume this is a list, tuple, queryset of objects
        if args and hasattr(args[0], '__iter__'):
            args = list(args)
            queryset = args.pop(0)
        elif 'objects' in kwargs:
            queryset = kwargs.pop('objects')

        if queryset is not None:
            # Create a queryset if this is a list of tuple of instances
            if not isinstance(queryset, QuerySet) and len(queryset):
                # If these are list of models, extra their primary keys
                # otherwise a assume a list of pks
                if isinstance(queryset[0], models.Model):
                    pks = [x.pk for x in queryset]
                else:
                    pks = queryset
                queryset = self._object_class.objects.filter(pk__in=pks)

            self._pending = queryset

        super(ObjectSet, self).__init__(*args, **kwargs)

        if save:
            self.save()

    def __len__(self):
        "Returns the length (size) of this set."
        return self.count

    def __nonzero__(self):
        "Prevents the set from being falsy."
        return True

    def __repr__(self):
        return '{0}({1})'.format(self.__class__.__name__, repr(self.objects))

    def __iter__(self):
        "Iterates over the objects in the set."
        return iter(self.objects)

    def __contains__(self, obj):
        "Returns True if `obj` is in this set."
        return self._set_object_exists(obj)

    def __and__(self, other):
        "Performs an intersection of this set and `other`."
        return self.__class__(other.objects & self.objects)

    def __or__(self, other):
        "Performs an union of this set and `other`."
        return self.__class__(other.objects | self.objects)

    def __xor__(self, other):
        "Performs an exclusive union of this set and `other`."
        excluded = models.Q(pk__in=(other.objects & self.objects))
        return self.__class__((other.objects | self.objects)
                              .exclude(excluded))

    def __sub__(self, other):
        "Removes objects from this set that are in `other`."
        excluded = models.Q(pk__in=other.objects)
        return self.__class__(self.objects.exclude(excluded))

    def __iand__(self, other):
        "Performs an inplace intersection of this set and `other`."
        self._pending = other.objects & self.objects
        return self

    def __ior__(self, other):
        "Performs and inplace union of this set and `other`."
        self._pending = other.objects | self.objects
        return self

    def __ixor__(self, other):
        "Performs an inplace exclusive union of this set and `other`."
        excluded = models.Q(pk__in=(other.objects & self.objects))
        self._pending = (other.objects | self.objects).exclude(excluded)
        return self

    def __isub__(self, other):
        "Inplace removal of objects from this set that are in `other`."
        excluded = models.Q(pk__in=other.objects)
        self._pending = self.objects.exclude(excluded)
        return self

    @cached_property
    def _set_object_rel(self):
        """Return the relation name of the many-to-many model between this
        set class and the object model. This can be specified explicitly via
        the `set_object_rel` property or it will be detected if there is only
        one many-to-many on this class, e.g. `Team.team_players`
        """
        # Not defined, so it is assumed to only have one M2M field
        if not hasattr(self, 'set_object_rel'):
            m2m_fields = self._meta.many_to_many

            if not m2m_fields:
                raise ImproperlyConfigured('At least one many-to-many '
                                           'relationship must exist on object '
                                           'sets.')

            if len(m2m_fields) != 1:
                raise ImproperlyConfigured('No explicit set object relation '
                                           'has been defined, but more than '
                                           'one many-to-many relationship '
                                           'exists on this object set. Define '
                                           '`set_object_rel` name on the '
                                           'class.')

            self.set_object_rel = m2m_fields[0].name

        return self.set_object_rel

    @cached_property
    def _through_set_rel(self):
        """Returns the name of the relation on the through model that goes to
        the set, e.g. `TeamPlayer.team`
        """
        through = self._set_object_class

        if hasattr(through, 'object_set_rel'):
            return through.object_set_rel

        field = None

        for f in through._meta.fields:
            if isinstance(f, models.ForeignKey) and f.rel.to is self.__class__:
                if field is None:
                    field = f
                    continue

                raise ImproperlyConfigured('No explicit through model set '
                                           'field relation has been defined, '
                                           'but more than one exists.')

        if field is None:
            raise ImproperlyConfigured('No through model set field relation '
                                       'was found.')

        return field.name

    @cached_property
    def _through_object_rel(self):
        """Returns the name of the relation on the through model that goes to
        the object, e.g. TeamPlayer.player
        """
        through = self._set_object_class

        if hasattr(through, 'set_object_rel'):
            return through.object_set_rel

        field = None

        for f in through._meta.fields:
            if isinstance(f, models.ForeignKey) and \
                    f.rel.to is self._object_class:
                if field is None:
                    field = f
                    continue

                raise ImproperlyConfigured('No explicit through model object '
                                           'field relation has been defined, '
                                           'but more than one exists.')

        if field is None:
            raise ImproperlyConfigured('No through model object field '
                                       'relation was found.')

        return field.name

    @cached_property
    def _set_object_class(self):
        "The class of the through model, e.g. TeamPlayer"
        return getattr(self.__class__, self._set_object_rel).through

    @cached_property
    def _object_class(self):
        "The class of the object model, e.g. Player"
        return getattr(self.__class__, self._set_object_rel).field.rel.to

    @cached_property
    def _set_object_class_supported(self):
        """Returns true if the set object class subclasses SetObject for
        extended features.
        """
        return issubclass(self._set_object_class, SetObject)

    def _objects(self):
        "Returns a QuerySet of objects in this set including pending ones."
        if not self.pk:
            return self._pending

        kwargs = {}

        if self._set_object_class_supported:
            kwargs['removed'] = False

        objects = self._object_class.objects.all()
        pks = self._set_objects(**kwargs)\
            .values_list('{0}__pk'.format(self._through_object_rel))

        return objects.filter(pk__in=pks) | self._pending

    def _set_objects(self, **kwargs):
        """Returns a queryset of set objects. Keyword arguments are passed as
        filters the set objects queryset.
        """
        kwargs[self._through_set_rel] = self
        return self._set_object_class.objects.filter(**kwargs)

    def _get_set_object(self, obj, **kwargs):
        """Attempts to return an intermediate set object or None for the
        specified object.
        """
        kwargs[self._through_object_rel] = obj

        try:
            return self._set_objects(**kwargs).get(**kwargs)
        except self._set_object_class.DoesNotExist:
            pass

    def _set_object_exists(self, obj, **kwargs):
        "Returns a boolean if the object is contained in this set."
        kwargs[self._through_object_rel] = obj
        return self._set_objects(**kwargs).exists()

    def _make_set_object(self, obj, **defaults):
        "Makes a new set object."
        kwargs = {self._through_object_rel: obj, self._through_set_rel: self}
        kwargs.update(defaults)
        return self._set_object_class(**kwargs)

    def _check_pk(self):
        if not self.pk:
            raise ObjectSetError

    def _check_type(self, obj):
        if not isinstance(obj, self._object_class):
            raise TypeError("Only objects of type '{0}' can be added to the "
                            "set".format(self._object_class.__name__))

    def _add(self, obj, added):
        """Check for an existing object that has been removed and mark
        it has not removed, otherwise create a new object and mark it
        as added.
        """
        self._check_type(obj)

        _obj = self._get_set_object(obj)

        if not self._set_object_class_supported:
            if _obj:
                return False
            _obj = self._make_set_object(obj)
        else:
            if _obj:
                # Already exists, nothing to do
                if not _obj.removed:
                    return False
                _obj.removed = False
                _obj.added = added
            else:
                _obj = self._make_set_object(obj, added=added)

        _obj.save()

        return True

    @property
    def added(self):
        "Returns the set of objects that have been added to this set."
        # Not saved or added flag not supported; return empty set
        if not self.pk or not self._set_object_class_supported:
            return self.__class__()

        objects = self._object_class.objects.all()
        pks = self._set_objects(added=True)\
            .values_list('{0}__pk'.format(self._through_object_rel))

        return self.__class__(objects.filter(pk__in=pks))

    @property
    def removed(self):
        "Returns the set of objects that have been removed from this set."
        # Not saved or added flag not supported; return empty set
        if not self.pk or not self._set_object_class_supported:
            return self.__class__()

        objects = self._object_class.objects.all()
        pks = self._set_objects(removed=True)\
            .values_list('{0}__pk'.format(self._through_object_rel))

        return self.__class__(objects.filter(pk__in=pks))

    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        # If this is new, use bulk if supported
        new = self.pk is None
        super(ObjectSet, self).save(*args, **kwargs)

        # Handle pending data after the set has been saved
        if self._pending is not None \
                and not isinstance(self._pending, EmptyQuerySet):
            pending = list(self._pending.only('pk'))
            self._pending = self._object_class.objects.none()
            if new and BULK_SUPPORTED:
                self.bulk(pending)
            else:
                self.replace(pending)

    @transaction.commit_on_success
    def bulk(self, objs, added=False):
        """Attempts to bulk load objects. Although this is the most efficient
        way to add objects, if any fail to be added, none will be added.

        This should be used when the set is empty and needs to be populated.
        """
        if not BULK_SUPPORTED:
            raise EnvironmentError('This method requires Django 1.4 or above')

        self._check_pk()
        _objs = []
        loaded = 0

        for obj in iter(objs):
            self._check_type(obj)
            _obj = self._make_set_object(obj)
            if self._set_object_class_supported:
                _obj.added = added
            _objs.append(_obj)
            loaded += 1

        self._set_object_class.objects.bulk_create(_objs)
        self.count += loaded
        self.save()
        return loaded

    @transaction.commit_on_success
    def add(self, obj, added=False):
        "Adds `obj` to the set."
        self._check_pk()
        added = self._add(obj, added)
        if added:
            self.count += 1
            self.modified = datetime.now()
            self.save()
        return added

    @transaction.commit_on_success
    def remove(self, obj, delete=False):
        "Removes `obj` from the set."
        self._check_pk()
        self._check_type(obj)

        _obj = self._get_set_object(obj)
        if not _obj:
            return False

        if delete or not self._set_object_class_supported:
            _obj.delete()
        else:
            if _obj.removed:
                return False
            _obj.removed = True
            _obj.save()
        self.count -= 1
        self.modified = datetime.now()
        self.save()
        return True

    @transaction.commit_on_success
    def update(self, objs, added=True):
        "Update the current set with the objects not already in the set."
        self._check_pk()
        added = 0
        for obj in iter(objs):
            added += int(self._add(obj, added))
        self.count += added
        self.modified = datetime.now()
        self.save()
        return added

    @transaction.commit_on_success
    def clear(self, delete=False):
        "Remove all objects from the set."
        self._check_pk()
        removed = self.count
        if delete or not self._set_object_class_supported:
            self._set_objects().delete()
        else:
            self._set_objects(removed=False).update(removed=True)
        self.count = 0
        self.modified = datetime.now()
        self.save()
        return removed

    @transaction.commit_on_success
    def replace(self, objs, delete=False, added=True):
        "Replace the current set with the new objects."
        self._check_pk()
        self.clear(delete=delete)
        # On a real delete, a bulk load is faster
        if delete or not self._set_object_class_supported:
            return self.bulk(objs, added=added)
        return self.update(objs, added=added)

    def purge(self):
        "Deletes objects in the set marked as `removed`."
        self._check_pk()
        if self._set_object_class_supported:
            self._set_objects(removed=True).delete()


class SetObject(models.Model):
    """Adds additional information about the objects that have been `added`
    and `removed` from the original set.

    For instance, additional objects that are added which do not match the
    conditions currently associated with the `ObjectSet` should be flagged
    as `added`. If in the future they match the conditions, the flag can be
    removed.

    Any objects that are removed from the set should be marked as `removed`
    even if they were added at one time. This is too keep track of the objects
    that have been explicitly removed from the set.

    To implement, define the foreign key to the objectset and object classes:

    class BookSetObject(ObjectSet):
        bookset = models.ForeignKey(BookSet)
        book = models.ForeignKey(Book)
    """
    added = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)

    class Meta(object):
        abstract = True
