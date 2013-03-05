import time
from django.test import TestCase
from django.db import IntegrityError
from django.db.models.query import QuerySet, EmptyQuerySet
from objectset.models import ObjectSetError
from .models import Record, RecordSet, RecordSetObject, SimpleRecordSet


class SetTestCase(TestCase):
    def test_properties(self):
        s = SimpleRecordSet()
        self.assertEqual(s._set_object_class, SimpleRecordSet.records.through)
        self.assertEqual(s._object_class, Record)

        self.assertEqual(s._set_object_class_supported, False)

        self.assertEqual(s._set_object_rel, 'records')
        self.assertEqual(s._through_set_rel, 'simplerecordset')
        self.assertEqual(s._through_object_rel, 'record')

    def test_init(self):
        objs = [Record(pk=i) for i in xrange(1, 5)]
        s = SimpleRecordSet(objs)
        self.assertTrue(isinstance(s._pending, QuerySet))
        s.save()
        self.assertTrue(isinstance(s._pending, EmptyQuerySet))
        self.assertEqual(s.count, 4)
        self.assertEqual(s.pk, 1)

    def test_repr(self):
        objs = [Record(pk=i) for i in xrange(1, 5)]
        self.assertEqual(repr(SimpleRecordSet(objs)), 'SimpleRecordSet([<Record: 1>, <Record: 2>, <Record: 3>, <Record: 4>])')


    def test_or(self):
        s1 = SimpleRecordSet([Record(pk=i) for i in xrange(1, 5)], save=True)
        s2 = SimpleRecordSet([Record(pk=i) for i in xrange(3, 7)], save=True)
        s3 = s1 | s2
        s3.save()

        self.assertEqual(sorted([o.pk for o in s3]), range(1, 7))

    def test_and(self):
        s1 = SimpleRecordSet([Record(pk=i) for i in xrange(1, 5)], save=True)
        s2 = SimpleRecordSet([Record(pk=i) for i in xrange(3, 7)], save=True)
        s3 = s1 & s2
        s3.save()

        self.assertEqual(sorted([o.pk for o in s3]), [3, 4])

    def test_xor(self):
        s1 = SimpleRecordSet([Record(pk=i) for i in xrange(1, 5)], save=True)
        s2 = SimpleRecordSet([Record(pk=i) for i in xrange(3, 7)], save=True)
        s3 = s1 ^ s2
        s3.save()

        self.assertEqual(sorted([o.pk for o in s3]), [1, 2, 5, 6])

    def test_sub(self):
        s1 = SimpleRecordSet([Record(pk=i) for i in xrange(1, 5)], save=True)
        s2 = SimpleRecordSet([Record(pk=i) for i in xrange(3, 7)], save=True)
        s3 = s1 - s2
        s3.save()

        self.assertEqual(sorted([o.pk for o in s3]), [1, 2])

    def test_multi_op(self):
        s1 = SimpleRecordSet([Record(pk=i) for i in xrange(1, 5)], save=True)
        s2 = SimpleRecordSet([Record(pk=i) for i in xrange(3, 7)], save=True)
        s3 = s1 - s2 | s1
        s3.save()
        self.assertEqual(sorted([o.pk for o in s3]), range(1, 5))

        s4 = s2 - s1 ^ s2
        s4.save()
        self.assertEqual(sorted([o.pk for o in s4]), [3, 4])

    def test_empty_set(self):
        s = SimpleRecordSet()
        s.save()
        self.assertEqual(s.count, 0)

    def test_methods_require_pk(self):
        s = SimpleRecordSet()
        r1 = Record(pk=1)

        self.assertRaises(ObjectSetError, s.add, r1)
        self.assertRaises(ObjectSetError, s.remove, r1)
        self.assertRaises(ObjectSetError, s.replace, r1)
        self.assertRaises(ObjectSetError, s.clear)
        self.assertRaises(ObjectSetError, s.purge)

    def test_invalid_type(self):
        s = SimpleRecordSet()
        s.save()

        self.assertRaises(TypeError, s.add, 1)

    def test_add(self):
        s = SimpleRecordSet()
        s.save()

        r1 = Record(pk=1)
        self.assertTrue(s.add(r1))
        self.assertEqual(s.count, 1)
        self.assertFalse(s.add(r1))
        self.assertEqual(s.count, 1)

        self.assertTrue(s.remove(r1))
        self.assertEqual(s.count, 0)
        self.assertTrue(s.add(r1))
        self.assertEqual(s.count, 1)

        self.assertEqual(s._set_objects().count(), 1)

    def test_bulk(self):
        s = SimpleRecordSet()
        s.save()

        objs = [Record(pk=i) for i in xrange(5)]
        objs2 = [Record(pk=i) for i in xrange(5, 10)]

        # Load 5
        self.assertEqual(s.bulk(objs), 5)
        self.assertEqual(s.count, 5)

        # Another 5
        self.assertEqual(s.bulk(objs2), 5)
        self.assertEqual(s.count, 10)

        # But not again..
        self.assertRaises(IntegrityError, s.bulk, [objs[3]])

    def test_remove(self):
        s = SimpleRecordSet()
        s.save()

        r1 = Record(pk=1)
        self.assertTrue(s.add(r1))
        self.assertTrue(s.remove(r1))
        self.assertEqual(s.count, 0)
        self.assertFalse(s.remove(r1))

        self.assertEqual(s._set_objects().count(), 0)

    def test_update(self):
        s = SimpleRecordSet()
        s.save()

        # Initial 5
        self.assertEqual(s.update([Record(pk=i) for i in xrange(0, 10, 2)]), 5)
        self.assertEqual(s.count, 5)

        # Adding the same doesn't do anything
        self.assertEqual(s.update([Record(pk=i) for i in xrange(0, 10, 2)]), 0)
        self.assertEqual(s.count, 5)

        # Add everything, only 5 get added
        self.assertEqual(s.update([Record(pk=i) for i in xrange(10)]), 5)
        self.assertEqual(s.count, 10)

    def test_replace(self):
        s = SimpleRecordSet()
        s.save()

        s.update([Record(pk=i) for i in xrange(3)])
        self.assertEqual(s.replace([Record(pk=i) for i in xrange(2, 6)]), 4)

        self.assertEqual(s._set_objects().count(), 4)

    def test_clear(self):
        s = SimpleRecordSet()
        s.save()

        s.update([Record(pk=i) for i in xrange(10)])
        self.assertEqual(s.clear(), 10)
        self.assertEqual(s.count, 0)

        self.assertEqual(s._set_objects().count(), 0)

    def test_perf(self):
        "Compares performance of bulk load vs. an update"
        s = SimpleRecordSet()
        s.save()

        Record.objects.all().delete()

        # Only test 100. SQLite limitation..
        objs = [Record(pk=i) for i in xrange(100)]
        Record.objects.bulk_create(objs)

        t0 = time.time()
        s.update(objs)
        t1 = time.time() - t0

        s._set_objects().delete()

        t0 = time.time()
        s.bulk(objs)
        t2 = time.time() - t0

        # 10-fold difference
        self.assertTrue(t2 * 10 < t1)

    def test_iter(self):
        s = SimpleRecordSet()
        s.save()
        objs = [Record(pk=i) for i in xrange(1, 11)]
        s.bulk(objs)
        self.assertEqual(list(s), objs)

    def test_contains(self):
        s = SimpleRecordSet()
        s.save()
        objs = [Record(pk=i) for i in xrange(1, 11)]
        s.bulk(objs)
        self.assertTrue(objs[0] in s)
        self.assertTrue(objs[7] in s)
        self.assertFalse(Record(pk=12) in s)


class SetObjectSetTestCase(TestCase):
    def test_properties(self):
        s = RecordSet()
        self.assertEqual(s._set_object_class, RecordSetObject)
        self.assertEqual(s._object_class, Record)

        self.assertEqual(s._set_object_class_supported, True)

        self.assertEqual(s._set_object_rel, 'records')
        self.assertEqual(s._through_set_rel, 'object_set')
        self.assertEqual(s._through_object_rel, 'set_object')

    def test_remove(self):
        s = RecordSet()
        s.save()

        r1 = Record(pk=1)
        self.assertTrue(s.add(r1))
        self.assertTrue(s.remove(r1))
        self.assertEqual(s.count, 0)
        self.assertFalse(s.remove(r1))

        # The `removed` record still exists
        self.assertEqual(s._set_objects().count(), 1)

    def test_remove_delete(self):
        s = RecordSet()
        s.save()

        r1 = Record(pk=1)
        self.assertTrue(s.add(r1))
        self.assertEqual(s.count, 1)
        s.remove(r1, delete=True)
        self.assertEqual(s.count, 0)

        # Real delete
        self.assertEqual(s._set_objects().count(), 0)

    def test_replace(self):
        s = RecordSet()
        s.save()

        s.update([Record(pk=i) for i in xrange(3)])
        self.assertEqual(s.replace([Record(pk=i) for i in xrange(2, 6)]), 4)

        # The `removed` records still exist
        self.assertEqual(s._set_objects().count(), 6)

    def test_replace_delete(self):
        s = RecordSet()
        s.save()

        s.bulk([Record(pk=i) for i in xrange(3)])
        self.assertEqual(s.count, 3)
        self.assertEqual(s.replace([Record(pk=i) for i in xrange(2, 6)], delete=True), 4)
        self.assertEqual(s.count, 4)

        # Original ones removed
        self.assertEqual(s._set_objects().count(), 4)

    def test_clear(self):
        s = RecordSet()
        s.save()

        s.update([Record(pk=i) for i in xrange(10)])
        self.assertEqual(s.clear(), 10)
        self.assertEqual(s.count, 0)

        # The `removed` records still exist
        self.assertEqual(s._set_objects().count(), 10)

    def test_clear_delete(self):
        s = RecordSet()
        s.save()

        s.bulk([Record(pk=i) for i in xrange(10)])
        self.assertEqual(s.clear(delete=True), 10)

        # The `removed` records have been deleted
        self.assertEqual(s._set_objects().count(), 0)

    def test_purge(self):
        s = RecordSet()
        s.save()

        s.update([Record(pk=i) for i in xrange(3)])
        s.replace([Record(pk=i) for i in xrange(2, 6)])

        # The `removed` records still exist
        self.assertEqual(s._set_objects().count(), 6)

        s.purge()

        # The `removed` records have been deleted
        self.assertEqual(s._set_objects().count(), 4)
