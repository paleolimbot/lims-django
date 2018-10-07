
import re

from random import randint
from django.test import TestCase
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Sample, SampleTag, BaseValidator, Term, Project, ProjectPermission, Attachment


def populate_test_data(n_samples=700, n_sub_samples=150, max_tags=3, test_user=None,
                       test_proj=None, clear=True, quiet=False):

    with transaction.atomic():

        if test_user is None:
            try:
                test_user = User.objects.get(username='tuser31848')
            except User.DoesNotExist:
                test_user = User.objects.create(username='tuser31848')

        if test_proj is None:
            try:
                proj = Project.objects.get(slug='test-project-1')
            except Project.DoesNotExist:
                proj = Project.objects.create(name="Test Project 1", slug='test-project-1', user=test_user)
        else:
            proj = test_proj

        if clear:
            if not quiet:
                print("Clearing previous test data...")
            clear_models(
                models=(Sample, ),
                queryset=lambda model: model.objects.filter(
                    slug__contains="_test-sub-sample", user=test_user
                ),
                quiet=quiet
            )
            clear_models(
                models=(Sample,),
                queryset=lambda model: model.objects.filter(slug__contains="_test-sample", user=test_user),
                quiet=quiet
            )
            clear_models(
                models=(Term,),
                queryset=lambda model: model.objects.filter(slug__startswith="key", user=test_user),
                quiet=quiet
            )

        if not quiet:
            print("\nGenerating samples...")

        parent_samples = []
        for sample_num in range(n_samples):
            if not quiet:
                print("\r%d/%d" % (sample_num + 1, n_samples), end='')

            sample = Sample.objects.create(
                project=proj,
                name="Test Sample %s" % (sample_num + 1),
                user=test_user,
                status='published'
            )

            n_tags = randint(0, max_tags)
            for tag_num in range(n_tags):
                sample.add_tags(**{
                    "key%d" % (tag_num + 1): "value%d" % (tag_num + 1)
                })

            parent_samples.append(sample)

        if not quiet:
            print("\nGenerating sub samples...")

        for sample_num in range(n_sub_samples):
            if not quiet:
                print("\r%d/%d" % (sample_num + 1, n_samples), end='')

            parent_sample_index = randint(0, len(parent_samples) - 1)

            sample = Sample.objects.create(
                project=proj,
                name="Test Sub Sample %s" % (sample_num + 1),
                parent=parent_samples[parent_sample_index],
                user=test_user,
                status='published'
            )

            n_tags = randint(0, max_tags)
            for tag_num in range(n_tags):
                sample.add_tags(**{
                    "key%d" % (tag_num + 1): "value%d" % (tag_num + 1)
                })

        if not quiet:
            print("\nComplete!")


def clear_models(models=(Sample, Attachment, Term, Project, BaseValidator),
                 queryset=lambda model: model.objects.all(), quiet=False):
    if not quiet:
        print("Clearing models...")
    last_exception = "Unknown error"

    for recursive_depth in range(10):
        if not quiet:
            print("Recursive depth: %d" % recursive_depth)
        deleted = 0
        for model in models:
            if not quiet:
                print("Model %s" % model)
            qs = queryset(model)
            qs_len = qs.count()
            for obj in qs:
                try:
                    obj.delete()
                    deleted += 1
                    if not quiet:
                        print("\r%d/%d" % (deleted, qs_len), end='')
                except Exception as e:
                    last_exception = str(e)
            if not quiet:
                print("")
        model_counts = [queryset(model).count() for model in models]
        if not any(model_counts):
            if not quiet:
                print("Clearing complete.")
            return

    raise Exception("Could not delete all models: %s" % last_exception)


class GeometryTestCase(TestCase):

    def test_wkt_bounds(self):
        """Test the wkt_bounds function"""
        from .utils.geometry import wkt_bounds
        self.assertEqual(
            wkt_bounds("(1 1)"),
            {'xmin': 1.0, 'xmax': 1.0, 'ymin': 1.0, 'ymax': 1.0}
        )
        self.assertEqual(
            wkt_bounds("(-1.45 -2.45) (1.75 2.75)"),
            {'xmin': -1.45, 'xmax': 1.75, 'ymin': -2.45, 'ymax': 2.75}
        )

        self.assertEqual(
            wkt_bounds("(-1.45 -2.45) (1.75 2.75) (0, 0)"),
            {'xmin': -1.45, 'xmax': 1.75, 'ymin': -2.45, 'ymax': 2.75}
        )

        self.assertEqual(
            wkt_bounds(''),
            {'xmin': None, 'xmax': None, 'ymin': None, 'ymax': None}
        )
        self.assertEqual(
            wkt_bounds(None),
            {'xmin': None, 'xmax': None, 'ymin':  None, 'ymax': None}
        )

    def test_wkt_regex(self):
        from .utils.geometry import POINT, POLYGON, LINESTRING, MULTIPOINT, MULTIPOLYGON, MULTILINESTRING

        # general tests
        self.assertRegex('POINT (30 10)', POINT)
        self.assertRegex('LINESTRING (30 10, 10 30, 40 40)', LINESTRING)
        self.assertRegex('POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))', POLYGON)
        self.assertRegex(
            'POLYGON ((35 10, 45 45, 15 40, 10 20, 35 10), (20 30, 35 35, 30 20, 20 30))',
            POLYGON
        )
        self.assertRegex(
            'MULTIPOINT ((10 40), (40 30), (20 20), (30 10))',
            MULTIPOINT
        )
        self.assertRegex(
            'MULTIPOINT (10 40, 40 30, 20 20, 30 10)',
            MULTIPOINT
        )
        self.assertRegex(
            'MULTILINESTRING ((10 10, 20 20, 10 40), (40 40, 30 30, 40 20, 30 10))',
            MULTILINESTRING
        )
        self.assertRegex(
            'MULTIPOLYGON (((40 40, 20 45, 45 30, 40 40)), ((20 35, 10 30, 10 10, 30 5, 45 20, 20 35), '
            '(30 20, 20 15, 20 25, 30 20)))',
            MULTIPOLYGON
        )
        self.assertRegex(
            'MULTIPOLYGON (((30 20, 45 40, 10 40, 30 20)), ((15 5, 40 10, 10 20, 5 10, 15 5)))',
            MULTIPOLYGON
        )

        # point tests
        self.assertRegex('POINT (-30.6  10.1e7)', POINT)
        self.assertRegex('POINT (30       10)', POINT)
        self.assertRegex('POINT (  30  10 )', POINT)

        # linestring tests
        self.assertRegex('LINESTRING (30 10,10 30,40 40   )', LINESTRING)
        self.assertRegex('LINESTRING (-30.0 10.8, .10 30E09, 40 0.40)', LINESTRING)

        # polygon tests
        self.assertRegex('POLYGON (    ( 30 10   , 40 40,20 40 , 10   20, 30 10))', POLYGON)
        self.assertRegex(
            'POLYGON ((35 10, 45 45, 15 40, 10 20, 35 10),(20 30, 35 35, 30 20, 20 30)  ,   (15 40,10 20,35 10))',
            POLYGON
        )

    def test_geometry_id(self):

        from .utils.geometry import identify_geometry

        self.assertEqual(identify_geometry('POINT (30 10)'), 'POINT')
        self.assertEqual(identify_geometry('LINESTRING (30 10, 10 30, 40 40)'), 'LINESTRING')
        self.assertEqual(identify_geometry('POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))'), 'POLYGON')
        self.assertEqual(identify_geometry('MULTIPOINT ((10 40), (40 30), (20 20), (30 10))'), 'MULTIPOINT')
        self.assertEqual(
            identify_geometry('MULTILINESTRING ((10 10, 20 20, 10 40), (40 40, 30 30, 40 20, 30 10))'),
            'MULTILINESTRING'
        )
        self.assertEqual(
            identify_geometry('MULTIPOLYGON (((30 20, 45 40, 10 40, 30 20)), ((15 5, 40 10, 10 20, 5 10, 15 5)))'),
            'MULTIPOLYGON'
        )
        self.assertIsNone(identify_geometry('MULTIPOLYGON with invalid geometry'))

    def test_geometry_validator(self):

        from .utils.geometry import validate_wkt

        self.assertIsNone(validate_wkt('POINT (30 10)'))
        self.assertIsNone(validate_wkt(''))
        self.assertIsNone(validate_wkt(None))
        with self.assertRaisesRegex(ValidationError, "The value is not valid"):
            validate_wkt('not valid wkt')


class SampleRecursionTestCase(TestCase):

    def test_recursive_samples(self):
        proj = Project.objects.create(name="Test Project", slug="test-proj")
        parent = Sample.objects.create(project=proj)
        child1 = Sample.objects.create(project=proj, parent=parent)
        child2 = Sample.objects.create(project=proj, parent=parent)
        child_child = Sample.objects.create(project=proj, parent=child1)

        self.assertEqual(parent.recursive_depth, 0)
        self.assertEqual(child1.recursive_depth, 1)
        self.assertEqual(child2.recursive_depth, 1)
        self.assertEqual(child_child.recursive_depth, 2)

        self.assertTrue(child1 in parent.children.all())
        self.assertTrue(child2 in parent.children.all())
        self.assertTrue(child_child in child1.children.all())


class SampleGeometryTestCase(TestCase):

    def test_sample_geometry(self):
        proj = Project.objects.create(name="Test Project", slug="test-proj")
        sample_no_geom = Sample.objects.create(project=proj)
        self.assertEqual(sample_no_geom.geometry, '')
        self.assertIsNone(sample_no_geom.geo_xmin)
        self.assertIsNone(sample_no_geom.geo_xmax)
        self.assertIsNone(sample_no_geom.geo_ymin)
        self.assertIsNone(sample_no_geom.geo_ymax)

        sample_point = Sample.objects.create(
            project=proj, geometry='POINT (30 10)'
        )
        self.assertEqual(sample_point.geometry, 'POINT (30 10)')
        self.assertEqual(sample_point.geo_xmin, 30)
        self.assertEqual(sample_point.geo_xmax, 30)
        self.assertEqual(sample_point.geo_ymin, 10)
        self.assertEqual(sample_point.geo_ymax, 10)

        sample_polygon = Sample.objects.create(
            project=proj,
            geometry='MULTIPOLYGON (((30 20, 45 40, 10 40, 30 20)), ((15 5, 40 10, 10 20, 5 10, 15 5)))'
        )
        self.assertEqual(sample_polygon.geo_xmin, 5)
        self.assertEqual(sample_polygon.geo_xmax, 45)
        self.assertEqual(sample_polygon.geo_ymin, 5)
        self.assertEqual(sample_polygon.geo_ymax, 40)


class TagsTestCase(TestCase):

    def setUp(self):
        proj = Project.objects.create(name="Test Project", slug="test-proj")
        self.sample = Sample.objects.create(project=proj, collected=timezone.now(), name='a sample')

        self.number_validator = BaseValidator.objects.create(
            name='Number', regex='^[0-9]+$', error_message='Value is not a number'
        )

        self.generic_term = Term.objects.create(project=proj, name='A generic tag', slug='generic-tag')
        self.number_term = Term.objects.create(project=proj, name='A Number Tag', slug='number-tag')
        self.number_term.validators.create(validator=self.number_validator)

    def test_object_tags(self):
        sample_tag_generic = SampleTag(object=self.sample, key=self.generic_term, value='literally anything')
        sample_tag_generic.full_clean()
        sample_tag_generic.save()
        sample_tag_numeric = SampleTag(object=self.sample, key=self.number_term, value='123487')
        sample_tag_numeric.full_clean()
        sample_tag_numeric.save()

        with self.assertRaisesRegex(ValidationError, 'Value is not a number'):
            sample_tag_numeric_bad = SampleTag(object=self.sample, key=self.number_term, value='AAA')
            sample_tag_numeric_bad.full_clean()


class SampleTestCase(TestCase):

    def setUp(self):
        self.proj = Project.objects.create(name="Test Project", slug="test-proj")
        self.test_user = User.objects.create(username="test_user_with_a_long_name")

    def test_slug_calculation(self):
        """Test that unique slugs get generated for samples"""
        now = timezone.now()
        sample1 = Sample.objects.create(
            project=self.proj,
            collected=now,
            name='a quite long name that will probably overflow the slug',
            user=self.test_user
        )
        self.assertTrue(len(sample1.slug), 55)

        sample2 = Sample.objects.create(
            project=self.proj,
            collected=now,
            name='a quite long name that will probably overflow the slug',
            user=self.test_user
        )
        self.assertTrue(len(sample2.slug), 55)
        self.assertRegex(sample2.slug, '_1$')

    def test_slug_calculation_large(self):
        """
        This creates a lot of samples with the same name to make sure that repeat calculation is robust
        """
        now = timezone.now()
        with transaction.atomic():
            for i in range(500):
                Sample.objects.create(project=self.proj, collected=now, user=self.test_user, name='sample_repeat')

        # test that the slugs go from 1 to 499
        sample_slugs = Sample.objects.filter(user=self.test_user, name='sample_repeat').values_list('slug', flat=True)
        self.assertEqual(len(sample_slugs), 500)

        suffix_re = re.compile('_([0-9]+)$')
        suffix_numbers = []
        zero_suffix = []
        for slug in sample_slugs:
            if suffix_re.search(slug):
                suffix_numbers.append(int(suffix_re.search(slug).group(1)))
            else:
                zero_suffix.append(slug)

        self.assertEqual(len(zero_suffix), 1)
        self.assertEqual(len(suffix_numbers), 499)

        for n1, n2 in zip(sorted(suffix_numbers), range(1, 500)):
            self.assertEqual(n1, n2)


class TestDataTestCase(TestCase):

    def setUp(self):
        self.test_user = User.objects.create(username='tuser')

    def test_sample_data_creation(self):
        """Test that the populate sample data method populates and re-populates properly"""

        # starting with an empty db, the app should populate the correct number of samples
        populate_test_data(n_samples=109, n_sub_samples=29, test_user=self.test_user, quiet=True)
        self.assertEqual(Sample.objects.filter(user=self.test_user, recursive_depth=0).count(), 109)
        self.assertEqual(Sample.objects.filter(user=self.test_user, recursive_depth__gt=0).count(), 29)

        # starting with an empty db, the app should populate the correct number of samples
        populate_test_data(n_samples=72, n_sub_samples=79, test_user=self.test_user, quiet=True, clear=True)
        self.assertEqual(Sample.objects.filter(user=self.test_user, recursive_depth=0).count(), 72)
        self.assertEqual(Sample.objects.filter(user=self.test_user, recursive_depth__gt=0).count(), 79)


class ProjectLayerTestCase(TestCase):

    def setUp(self):
        self.test_user = User.objects.create(username='tuser')
        self.proj1 = Project.objects.create(name="Project 1", slug="project-1")
        self.proj2 = Project.objects.create(name="Project 2", slug="project-2")

    def test_project_tags(self):
        """Project tags can only have terms with no project attribute"""
        t1 = Term.objects.create(name="t1", slug="t1", project=None)
        t2 = Term.objects.create(name="t2", slug="t2", project=self.proj1)

        self.proj1.set_tags(_values={t1: "fishval"})
        self.assertEqual(self.proj1.get_tag(t1), "fishval")
        with self.assertRaisesRegex(ValidationError, "Object project must match term project"):
            self.proj1.set_tags(_values={t2: "fishval"})
        self.assertIsNone(self.proj1.get_tag(t2))

        with self.assertRaisesRegex(ValidationError, "Object project must match term project"):
            self.proj1.update_tags(_values={t2: "fishval"})
        self.assertIsNone(self.proj1.get_tag(t2))

    def test_object_projects(self):
        t0 = Term.objects.create(name="t1", slug="t1", project=None)
        t1 = Term.objects.create(name="t2", slug="t2", project=self.proj1)
        t2 = Term.objects.create(name="t3", slug="t3", project=self.proj2)

        s1 = Sample.objects.create(project=self.proj1, user=self.test_user)

        # same project should work
        st1 = SampleTag.objects.create(object=s1, key=t1, value='value')
        self.assertEqual(st1.object, s1)
        self.assertEqual(st1.key, t1)
        s1.set_tags(_values={t1: 'stringval'})
        self.assertEqual(s1.get_tag(t1), 'stringval')

        # no project should not work
        with self.assertRaisesRegex(ValidationError, "Object project must match term project"):
            s1.set_tags(_values={t0: "stringval"})

        # proj2 should not work
        with self.assertRaisesRegex(ValidationError, "Object project must match term project"):
            s1.set_tags(_values={t2: "stringval"})

        # parent sample with other proj should not work
        with self.assertRaisesRegex(ValidationError, "Parent must belong to same project as child"):
            news = Sample(project=self.proj2, parent=s1)
            news.full_clean()


class PermissionTestCase(TestCase):

    def setUp(self):
        self.test_user1 = User.objects.create(username='tuser1')
        self.test_user2 = User.objects.create(username='tuser2')
        self.staff_user = User.objects.create(username='staff_user', is_staff=True)

        self.proj1 = Project.objects.create(name="Project 1", slug="project-1")
        self.proj1.set_tags(atag='avalue1')
        self.ptag1 = self.proj1.tags.all()[0]
        self.sample1 = Sample.objects.create(collected=timezone.now(), project=self.proj1, name="user1's sample")
        self.sample1.set_tags(atag='avalue1')
        self.stag1 = self.sample1.tags.all()[0]
        self.sterm1 = self.stag1.key

        self.proj2 = Project.objects.create(name="Project 2", slug="project-2")
        self.proj2.set_tags(atag='avalue2')
        self.ptag2 = self.proj2.tags.all()[0]
        self.sample2 = Sample.objects.create(collected=timezone.now(), project=self.proj2, name="user2's sample")
        self.sample2.set_tags(atag='avalue2')
        self.stag2 = self.sample2.tags.all()[0]
        self.sterm2 = self.stag2.key

        self.pterm = self.ptag1.key

        # a realistic set of permissions, users generally cannot edit projects or terms
        ProjectPermission.objects.create(user=self.test_user1, project=self.proj1, permission='view', model='Project')
        ProjectPermission.objects.create(user=self.test_user1, project=self.proj1, permission='view', model='Term')
        ProjectPermission.objects.create(user=self.test_user1, project=self.proj1, permission='view', model='Sample')
        ProjectPermission.objects.create(user=self.test_user1, project=self.proj1, permission='edit', model='Sample')

        ProjectPermission.objects.create(user=self.test_user2, project=self.proj2, permission='view', model='Project')
        ProjectPermission.objects.create(user=self.test_user2, project=self.proj2, permission='view', model='Term')
        ProjectPermission.objects.create(user=self.test_user2, project=self.proj2, permission='view', model='Sample')
        ProjectPermission.objects.create(user=self.test_user2, project=self.proj2, permission='edit', model='Sample')

    def test_project_permissions(self):

        # view permission allows viewing of project in a list
        self.assertTrue(self.proj1.user_can(self.test_user1, 'view'))
        self.assertTrue(self.ptag1.user_can(self.test_user1, 'view'))
        self.assertFalse(self.proj1.user_can(self.test_user2, 'view'))
        self.assertFalse(self.ptag1.user_can(self.test_user2, 'view'))

        # only staff can do anything else to actual project objects
        self.assertFalse(self.proj1.user_can(self.test_user1, 'edit'))
        self.assertTrue(self.proj1.user_can(self.staff_user, 'edit'))
        self.assertFalse(self.ptag1.user_can(self.test_user1, 'edit'))
        self.assertTrue(self.ptag1.user_can(self.staff_user, 'edit'))

        # nobody can view project terms, nobody can edit them except staff
        self.assertFalse(self.pterm.user_can(self.test_user1, 'view'))
        self.assertFalse(self.pterm.user_can(self.test_user1, 'edit'))
        self.assertTrue(self.pterm.user_can(self.staff_user, 'view'))
        self.assertTrue(self.pterm.user_can(self.staff_user, 'edit'))

        # user querysets
        self.assertTrue(self.proj1 in Project.queryset_for_user(self.test_user1, 'view'))
        self.assertTrue(self.proj1 in Project.queryset_for_user(self.staff_user, 'view'))
        self.assertFalse(self.proj1 in Project.queryset_for_user(self.test_user2, 'view'))

        self.assertTrue(self.proj2 in Project.queryset_for_user(self.test_user2, 'view'))
        self.assertTrue(self.proj2 in Project.queryset_for_user(self.staff_user, 'view'))
        self.assertFalse(self.proj2 in Project.queryset_for_user(self.test_user1, 'view'))

    def test_sample_permissions(self):

        # samples follow project permissions for Sample
        self.assertTrue(self.sample1.user_can(self.test_user1, 'view'))
        self.assertFalse(self.sample1.user_can(self.test_user2, 'view'))
        self.assertTrue(self.sample1.user_can(self.staff_user, 'view'))
        self.assertTrue(self.sample1.user_can(self.staff_user, 'edit'))

        self.assertTrue(self.sample2.user_can(self.test_user2, 'view'))
        self.assertFalse(self.sample2.user_can(self.test_user1, 'view'))
        self.assertTrue(self.sample2.user_can(self.staff_user, 'view'))
        self.assertTrue(self.sample2.user_can(self.staff_user, 'edit'))

        # user querysets
        self.assertTrue(self.sample1 in Sample.queryset_for_user(self.test_user1, 'view'))
        self.assertTrue(self.sample1 in Sample.queryset_for_user(self.staff_user, 'view'))
        self.assertFalse(self.sample1 in Sample.queryset_for_user(self.test_user2, 'view'))

        self.assertTrue(self.sample2 in Sample.queryset_for_user(self.test_user2, 'view'))
        self.assertTrue(self.sample2 in Sample.queryset_for_user(self.staff_user, 'view'))
        self.assertFalse(self.sample2 in Sample.queryset_for_user(self.test_user1, 'view'))

    def test_sample_tag_permissions(self):

        # sample tags follow samples
        self.assertTrue(self.stag1.user_can(self.test_user1, 'view'))
        self.assertFalse(self.stag1.user_can(self.test_user2, 'view'))
        self.assertTrue(self.stag1.user_can(self.staff_user, 'view'))
        self.assertTrue(self.stag1.user_can(self.staff_user, 'edit'))

        self.assertTrue(self.stag2.user_can(self.test_user2, 'view'))
        self.assertFalse(self.stag2.user_can(self.test_user1, 'view'))
        self.assertTrue(self.stag2.user_can(self.staff_user, 'view'))
        self.assertTrue(self.stag2.user_can(self.staff_user, 'edit'))

        # user querysets
        self.assertTrue(self.stag1 in SampleTag.queryset_for_user(self.test_user1, 'view'))
        self.assertTrue(self.stag1 in SampleTag.queryset_for_user(self.staff_user, 'view'))
        self.assertFalse(self.stag1 in SampleTag.queryset_for_user(self.test_user2, 'view'))

        self.assertTrue(self.stag2 in SampleTag.queryset_for_user(self.test_user2, 'view'))
        self.assertTrue(self.stag2 in SampleTag.queryset_for_user(self.staff_user, 'view'))
        self.assertFalse(self.stag2 in SampleTag.queryset_for_user(self.test_user1, 'view'))

    def test_term_permissions(self):

        # samples follow project permissions for Term
        self.assertTrue(self.sterm1.user_can(self.test_user1, 'view'))
        self.assertFalse(self.sterm1.user_can(self.test_user2, 'view'))
        self.assertTrue(self.sterm1.user_can(self.staff_user, 'view'))
        self.assertTrue(self.sterm1.user_can(self.staff_user, 'edit'))

        self.assertTrue(self.sterm2.user_can(self.test_user2, 'view'))
        self.assertFalse(self.sterm2.user_can(self.test_user1, 'view'))
        self.assertTrue(self.sterm2.user_can(self.staff_user, 'view'))
        self.assertTrue(self.sterm2.user_can(self.staff_user, 'edit'))

        # user querysets
        self.assertTrue(self.sterm1 in Term.queryset_for_user(self.test_user1, 'view'))
        self.assertFalse(self.sterm1 in Term.queryset_for_user(self.test_user1, 'edit'))
        self.assertTrue(self.sterm1 in Term.queryset_for_user(self.staff_user, 'view'))
        self.assertFalse(self.sterm1 in Term.queryset_for_user(self.test_user2, 'view'))

        self.assertTrue(self.sterm2 in Term.queryset_for_user(self.test_user2, 'view'))
        self.assertFalse(self.sterm2 in Term.queryset_for_user(self.test_user2, 'edit'))
        self.assertTrue(self.sterm2 in Term.queryset_for_user(self.staff_user, 'view'))
        self.assertFalse(self.sterm2 in Term.queryset_for_user(self.test_user1, 'view'))


class DefaultObjectTestCase(TestCase):

    def test_default_project(self):
        new_user = User.objects.create(username="anewuser")

        from . import default_objects
        # test assumes there is no default project before
        default_p = default_objects.get_or_create_default_project()

        # should be a project
        self.assertTrue(isinstance(default_p, Project))

        # all existing users should be able to do the things in the default project
        default_p_sample = Sample.objects.create(project=default_p, name="ds", collected=timezone.now())
        self.assertTrue(default_p_sample.user_can(new_user, 'view'))
        self.assertTrue(default_p_sample.user_can(new_user, 'edit'))

        # subsequent calls should return the same project
        self.assertEqual(
            default_objects.get_or_create_default_project(),
            default_p
        )

    def test_user_projects(self):
        user = User.objects.create(username="anewuser")
        other_user = User.objects.create(username="other")
        staff_user = User.objects.create(username="staffer", is_staff=True)

        from . import default_objects
        user_proj = default_objects.get_or_create_user_project(user)

        # should be a project
        self.assertTrue(isinstance(user_proj, Project))

        # only the user and the staffer should be able to do anything
        default_p_sample = Sample.objects.create(project=user_proj, name="ds", collected=timezone.now())
        self.assertTrue(default_p_sample.user_can(user, 'view'))
        self.assertTrue(default_p_sample.user_can(user, 'edit'))

        self.assertTrue(default_p_sample.user_can(staff_user, 'view'))
        self.assertTrue(default_p_sample.user_can(staff_user, 'edit'))

        self.assertFalse(default_p_sample.user_can(other_user, 'view'))
        self.assertFalse(default_p_sample.user_can(other_user, 'edit'))

        # subsequent calls should return the same project
        self.assertEqual(
            default_objects.get_or_create_user_project(user),
            user_proj
        )
