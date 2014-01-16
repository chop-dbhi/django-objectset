import json
from django.test import TestCase
from django.db import IntegrityError
from django.db.models.query import QuerySet, EmptyQuerySet
from django.contrib.auth.models import User
from objectset.models import ObjectSetError
from objectset.forms import objectset_form_factory
from .models import Record, RecordSet, RecordSetObject, SimpleRecordSet, \
    ProtectedRecordSet


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

    def test_init_ids(self):
        objs = range(1, 5)
        s = SimpleRecordSet(objs)
        self.assertTrue(isinstance(s._pending, QuerySet))
        s.save()
        self.assertTrue(isinstance(s._pending, EmptyQuerySet))
        self.assertEqual(s.count, 4)
        self.assertEqual(s.pk, 1)

    def test_init_objects(self):
        objs = [Record(pk=i) for i in xrange(1, 5)]
        s = SimpleRecordSet(objects=objs)
        self.assertTrue(isinstance(s._pending, QuerySet))
        s.save()
        self.assertTrue(isinstance(s._pending, EmptyQuerySet))
        self.assertEqual(s.count, 4)
        self.assertEqual(s.pk, 1)

    def teset_init_object_ids(self):
        objs = range(1, 5)
        s = SimpleRecordSet(objects=objs)
        self.assertTrue(isinstance(s._pending, QuerySet))
        s.save()
        self.assertTrue(isinstance(s._pending, EmptyQuerySet))
        self.assertEqual(s.count, 4)
        self.assertEqual(s.pk, 1)

    def test_repr(self):
        objs = [Record(pk=i) for i in xrange(1, 5)]
        self.assertEqual(repr(SimpleRecordSet(objs)),
                         'SimpleRecordSet([<Record: 1>, <Record: 2>, '
                         '<Record: 3>, <Record: 4>])')

    def test_and(self):
        s1 = SimpleRecordSet([Record(pk=i) for i in xrange(1, 5)], save=True)
        s2 = SimpleRecordSet([Record(pk=i) for i in xrange(3, 7)], save=True)
        s3 = s1 & s2
        s3.save()

        self.assertEqual(sorted([o.pk for o in s3]), [3, 4])

    def test_iand(self):
        s1 = SimpleRecordSet([Record(pk=i) for i in xrange(1, 5)], save=True)
        s2 = SimpleRecordSet([Record(pk=i) for i in xrange(3, 7)], save=True)
        s2 &= s1
        s2.save()

        self.assertEqual(sorted([o.pk for o in s2]), [3, 4])

    def test_or(self):
        s1 = SimpleRecordSet([Record(pk=i) for i in xrange(1, 5)], save=True)
        s2 = SimpleRecordSet([Record(pk=i) for i in xrange(3, 7)], save=True)
        s3 = s1 | s2
        s3.save()

        self.assertEqual(sorted([o.pk for o in s3]), range(1, 7))

    def test_ior(self):
        s1 = SimpleRecordSet([Record(pk=i) for i in xrange(1, 5)], save=True)
        s2 = SimpleRecordSet([Record(pk=i) for i in xrange(3, 7)], save=True)
        s2 |= s1
        s2.save()

        self.assertEqual(sorted([o.pk for o in s2]), range(1, 7))

    def test_xor(self):
        s1 = SimpleRecordSet([Record(pk=i) for i in xrange(1, 5)], save=True)
        s2 = SimpleRecordSet([Record(pk=i) for i in xrange(3, 7)], save=True)
        s3 = s1 ^ s2
        s3.save()

        self.assertEqual(sorted([o.pk for o in s3]), [1, 2, 5, 6])

    def test_ixor(self):
        s1 = SimpleRecordSet([Record(pk=i) for i in xrange(1, 5)], save=True)
        s2 = SimpleRecordSet([Record(pk=i) for i in xrange(3, 7)], save=True)
        s2 ^= s1
        s2.save()

        self.assertEqual(sorted([o.pk for o in s2]), [1, 2, 5, 6])

    def test_sub(self):
        s1 = SimpleRecordSet([Record(pk=i) for i in xrange(1, 5)], save=True)
        s2 = SimpleRecordSet([Record(pk=i) for i in xrange(3, 7)], save=True)
        s3 = s1 - s2
        s3.save()

        self.assertEqual(sorted([o.pk for o in s3]), [1, 2])

    def test_isub(self):
        s1 = SimpleRecordSet([Record(pk=i) for i in xrange(1, 5)], save=True)
        s2 = SimpleRecordSet([Record(pk=i) for i in xrange(3, 7)], save=True)
        s2 -= s1
        s2.save()

        self.assertEqual(sorted([o.pk for o in s2]), [5, 6])

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
        self.assertEqual(s.replace([Record(pk=i) for i in xrange(2, 6)],
                                   delete=True), 4)
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


class SetFormTest(TestCase):
    def test(self):
        RecordSetForm = objectset_form_factory(RecordSet)
        form = RecordSetForm(data={'objects': range(1, 5)})
        self.assertTrue(form.is_valid())
        s = form.save()
        self.assertEqual(s.count, 4)
        self.assertEqual(s.pk, 1)

    def test_subclass(self):
        from django import forms

        RecordSetForm = objectset_form_factory(RecordSet)

        class CustomRecordSetForm(RecordSetForm):
            name = forms.CharField()

        form = CustomRecordSetForm(data={'objects': range(1, 5)})
        self.assertFalse(form.is_valid())

        form = CustomRecordSetForm(data={
            'objects': range(1, 5),
            'name': 'Foo',
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['name'], 'Foo')

    def test_instance(self):
        s = SimpleRecordSet(range(1, 5), save=True)

        SimpleRecordSetForm = objectset_form_factory(SimpleRecordSet)
        form = SimpleRecordSetForm(data={'objects': range(6, 9)}, instance=s)

        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(s.count, 3)
        self.assertEqual(sorted(list([x.pk for x in s])), [6, 7, 8])


class ResourcesTest(TestCase):
    def test_get_sets(self):
        response = self.client.get('/', HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 0)

        RecordSet([1, 2, 3], save=True)
        response = self.client.get('/', HTTP_ACCEPT='application/json')
        data = json.loads(response.content)

        self.assertEqual(len(data), 1)
        self.assertFalse('objects' in data[0])

        response = self.client.get('/?embed=1', HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual(len(data[0]['objects']), 3)

    def test_post_sets(self):
        response = self.client.post('/?embed=1',
                                    json.dumps({'objects': [1, 2, 3]}),
                                    content_type='application/json',
                                    HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual([o['id'] for o in data['objects']], [1, 2, 3])

        s2 = RecordSet([4, 5, 6], save=True)
        response = self.client.post('/?embed=1',
                                    json.dumps({
                                        'objects': [1, 2, 3],
                                        'operations': [
                                            {'set': s2.pk, 'operator': 'or'}
                                        ],
                                    }),
                                    content_type='application/json',
                                    HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual([o['id'] for o in data['objects']],
                         [1, 2, 3, 4, 5, 6])

        s2 = RecordSet([4, 5, 6], save=True)
        response = self.client.post('/?embed=1',
                                    json.dumps({
                                        'operations': [
                                            {'set': s2.pk, 'operator': 'or'}
                                        ],
                                    }),
                                    content_type='application/json',
                                    HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual([o['id'] for o in data['objects']],
                         [4, 5, 6])

    def test_get_set(self):
        RecordSet([1, 2, 3], save=True)
        response = self.client.get('/1/?embed=1',
                                   HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual(len(data['objects']), 3)

    def test_put_set(self):
        s = RecordSet([1, 2, 3], save=True)
        s2 = RecordSet([4, 5, 6], save=True)

        ops = [
            {'set': s2.pk, 'operator': 'or'},
            {'set': [2, 4, 6], 'operator': 'sub'},
        ]

        self.client.put('/1/', json.dumps({
                        'objects': [4, 5, 6],
                        'operations': ops,
                        }),
                        content_type='application/json',
                        HTTP_ACCEPT='application/json')

        self.assertEqual([o.pk for o in s], [1, 3, 5])

    def test_delete_set(self):
        RecordSet([1, 2, 3], save=True)
        self.client.delete('/1/', HTTP_ACCEPT='application/json')
        self.assertEqual(RecordSet.objects.count(), 0)

    def test_get_set_objects(self):
        RecordSet([1, 2, 3], save=True)
        response = self.client.get('/1/objects/',
                                   HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual([o['id'] for o in data], [1, 2, 3])


class ProtectedResourcesTest(TestCase):
    def test_user(self):
        user = User.objects.create_user(username='test', password='test')
        ProtectedRecordSet([1, 2, 3], user=user, save=True)

        # Unauthenticated
        response = self.client.get('/protected/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 0)

        # Authenticate
        self.client.login(username='test', password='test')

        response = self.client.get('/protected/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)

    def test_session(self):
        # This session mumbo-jumbo is from:
        #       https://code.djangoproject.com/ticket/10899
        from django.conf import settings
        from django.utils.importlib import import_module

        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store.save()  # we need to make load() work, or the cookie is worthless
        session_key = store.session_key

        ProtectedRecordSet([1, 2, 3], session_key=session_key, save=True)

        # Unauthenticated
        response = self.client.get('/protected/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 0)

        # Authenticate
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session_key

        response = self.client.get('/protected/',
                                   HTTP_ACCEPT='application/json')
        self.assertEqual(len(json.loads(response.content)), 1)
