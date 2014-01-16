from django.db import models
from django.contrib.auth.models import User
from objectset.models import ObjectSet, SetObject


class Record(models.Model):
    def __unicode__(self):
        return unicode(self.pk)


class RecordSet(ObjectSet):
    records = models.ManyToManyField(Record, through='RecordSetObject')


class RecordSetObject(SetObject):
    object_set = models.ForeignKey(RecordSet)
    set_object = models.ForeignKey(Record)

    class Meta(object):
        unique_together = ('object_set', 'set_object')


class SimpleRecordSet(ObjectSet):
    records = models.ManyToManyField(Record)


class ProtectedRecordSet(ObjectSet):
    user = models.ForeignKey(User, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    records = models.ManyToManyField(Record)
