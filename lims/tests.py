
import re

from random import randint
from django.test import TestCase
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Sample, Location, SampleTag, BaseValidator, Term, Project


def populate_test_data(n_locations=150, n_sub_locations=150, n_samples=700, max_tags=3, test_user=None,
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
                queryset=lambda model: model.objects.filter(slug__contains="_test-sample", user=test_user),
                quiet=quiet
            )
            clear_models(
                models=(Location, ),
                queryset=lambda model: model.objects.filter(slug__startswith="test-", user=test_user),
                quiet=quiet
            )
            clear_models(
                models=(Term,),
                queryset=lambda model: model.objects.filter(slug__startswith="key", project=test_proj),
                quiet=quiet
            )

        if not quiet:
            print("Generating locations...")
        for loc_num in range(n_locations):
            if not quiet:
                print("\r%d/%d" % (loc_num + 1, n_locations), end='')

            loc = Location.objects.create(
                project=proj,
                name="Test Location %d" % (loc_num + 1),
                slug="test-location-%d" % (loc_num + 1),
                geometry="POINT (%d %d)" % (randint(-179, 180), randint(-85, 86)),
                user=test_user
            )

            n_tags = randint(0, max_tags)
            for tag_num in range(n_tags):
                loc.add_tags(**{
                    "key%d" % (tag_num + 1): "value%d" % (tag_num + 1)
                })
        if not quiet:
            print("\nGenerating sub-locations...")
        for loc_num in range(n_sub_locations):
            if not quiet:
                print("\r%d/%d" % (loc_num + 1, n_sub_locations), end='')

            n_locs = Location.objects.all().count()
            parent_loc = Location.objects.all()[randint(0, n_locs - 1)]
            loc = Location.objects.create(
                project=proj,
                name="Test Sub Location %d" % (loc_num + 1),
                slug="test-sub-location-%d" % (loc_num + 1),
                geometry="POINT (%d %d)" % (randint(-179, 180), randint(-85, 86)),
                parent=parent_loc,
                user=test_user
            )

            n_tags = randint(0, max_tags)
            for tag_num in range(n_tags):
                loc.add_tags(**{
                    "key%d" % (tag_num + 1): "value%d" % (tag_num + 1)
                })

        if not quiet:
            print("\nGenerating samples...")
        for sample_num in range(n_samples):
            if not quiet:
                print("\r%d/%d" % (sample_num + 1, n_samples), end='')

            n_locs = Location.objects.filter(user=test_user, slug__contains="test-").count()
            loc_index = randint(0, int(n_locs * 1.5))
            if loc_index < n_locs:
                parent_loc = Location.objects.all()[loc_index]
            else:
                parent_loc = None

            sample = Sample.objects.create(
                project=proj,
                name="Test Sample %s" % (sample_num + 1),
                location=parent_loc,
                collected=timezone.now(),
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


def clear_models(models=(Sample, Location, Term, BaseValidator),
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


class LocationRecursionTestCase(TestCase):

    def test_recursive_locations(self):
        proj = Project.objects.create(name="Test Project", slug="test-proj")
        parent_loc = Location.objects.create(project=proj, name="Location1", slug="location-1")
        child_loc = Location.objects.create(project=proj, name="Sub Location 1", slug="sub-location-1",
                                            parent=parent_loc)
        child_loc_2 = Location.objects.create(project=proj, name="Sub Location 2", slug="sub-location-2",
                                              parent=parent_loc)
        child_child_loc = Location.objects.create(project=proj,
                                                  name="Sub Sub Location", slug="sub-sub-location", parent=child_loc)

        self.assertEqual(parent_loc.recursive_depth, 0)
        self.assertEqual(child_loc.recursive_depth, 1)
        self.assertEqual(child_loc_2.recursive_depth, 1)
        self.assertEqual(child_child_loc.recursive_depth, 2)

        self.assertEqual(
            list(parent_loc.children.all().order_by('pk')),
            list(Location.objects.all().filter(slug__startswith="sub-location").order_by('pk')),
        )


class LocationGeometryTestCase(TestCase):

    def test_location_geometry(self):
        proj = Project.objects.create(name="Test Project", slug="test-proj")
        location_no_geom = Location.objects.create(project=proj, name="location1", slug="location1")
        self.assertEqual(location_no_geom.geometry, '')
        self.assertIsNone(location_no_geom.xmin)
        self.assertIsNone(location_no_geom.xmax)
        self.assertIsNone(location_no_geom.ymin)
        self.assertIsNone(location_no_geom.ymax)

        location_point = Location.objects.create(
            project=proj, name='location2', slug='location2', geometry='POINT (30 10)'
        )
        self.assertEqual(location_point.geometry, 'POINT (30 10)')
        self.assertEqual(location_point.xmin, 30)
        self.assertEqual(location_point.xmax, 30)
        self.assertEqual(location_point.ymin, 10)
        self.assertEqual(location_point.ymax, 10)

        location_polygon = Location.objects.create(
            project=proj,
            name='location3', slug='location3',
            geometry='MULTIPOLYGON (((30 20, 45 40, 10 40, 30 20)), ((15 5, 40 10, 10 20, 5 10, 15 5)))'
        )
        self.assertEqual(location_polygon.xmin, 5)
        self.assertEqual(location_polygon.xmax, 45)
        self.assertEqual(location_polygon.ymin, 5)
        self.assertEqual(location_polygon.ymax, 40)


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
        self.test_location1 = Location.objects.create(
            project=self.proj,
            name='test location 1 with a long name',
            slug='test_location_1_with_a_long_name',
            user=self.test_user
        )
        self.test_location2 = Location.objects.create(
            project=self.proj,
            name='test location 2 with a long name',
            slug='test_location_2_with_a_long_name',
            user=self.test_user
        )

    def test_slug_calculation(self):
        """Test that unique slugs get generated for samples"""
        now = timezone.now()
        sample1 = Sample.objects.create(
            project=self.proj,
            collected=now,
            name='a quite long name',
            location=self.test_location1,
            user=self.test_user
        )
        self.assertTrue(len(sample1.slug), 55)

        sample2 = Sample.objects.create(
            project=self.proj,
            collected=now,
            name='a quite long name',
            location=self.test_location1,
            user=self.test_user
        )
        self.assertTrue(len(sample2.slug), 55)
        self.assertRegex(sample2.slug, '_1$')

    def test_slug_calculation_fail(self):
        """
        There is a 500-sample limit on unique sample creation to avoid a long-running loop in
        Sample.calculate_slug()...this test creates 501 samples and breaks it
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

    def test_str_output(self):
        """Tests that the string output should be the sample slug"""
        sample = Sample.objects.create(project=self.proj, collected=timezone.now(), user=self.test_user)
        self.assertEqual(sample.slug, str(sample))


class TestDataTestCase(TestCase):

    def setUp(self):
        self.test_user = User.objects.create(username='tuser')

    def test_sample_data_creation(self):
        """Test that the populate sample data method populates and re-populates properly"""

        # starting with an empty db, the app should populate the correct number of samples
        populate_test_data(n_locations=28, n_sub_locations=31, n_samples=109, test_user=self.test_user, quiet=True)
        self.assertEqual(Location.objects.filter(user=self.test_user).count(), 59)
        self.assertEqual(Sample.objects.filter(user=self.test_user).count(), 109)

        # starting with an full db of test data, the app should still populate the correct number of samples
        populate_test_data(n_locations=41, n_sub_locations=35, n_samples=27, test_user=self.test_user, clear=True,
                           quiet=True)
        self.assertEqual(Location.objects.filter(user=self.test_user).count(), 76)
        self.assertEqual(Sample.objects.filter(user=self.test_user).count(), 27)


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
        with self.assertRaisesRegex(ValidationError, "terms must not have projects"):
            self.proj1.set_tags(_values={t2: "fishval"})
        self.assertIsNone(self.proj1.get_tag(t2))

        with self.assertRaisesRegex(ValidationError, "terms must not have projects"):
            self.proj1.update_tags(_values={t2: "fishval"})
        self.assertIsNone(self.proj1.get_tag(t2))

    def test_object_projects(self):
        t1 = Term.objects.create(name="t1", slug="t1", project=None)
        t2 = Term.objects.create(name="t2", slug="t2", project=self.proj1)
        t3 = Term.objects.create(name="t3", slug="t3", project=self.proj2)

        s2 = Sample(project=self.proj1, name="sample", user=self.test_user, collected=timezone.now())
        s2.save()

        l2 = Location.objects.create(project=self.proj1, name="loc", slug="loc")
        l3 = Location.objects.create(project=self.proj2, name="loc", slug="loc2")

        # no project should not work
        with self.assertRaisesRegex(ValidationError, "Object project must match term project"):
            s2.set_tags(_values={t1: "stringval"})
        with self.assertRaisesRegex(ValidationError, "Object project must match term project"):
            l2.set_tags(_values={t1: "stringval"})

        # proj2 should not work
        with self.assertRaisesRegex(ValidationError, "Object project must match term project"):
            s2.set_tags(_values={t3: "stringval"})
        with self.assertRaisesRegex(ValidationError, "Object project must match term project"):
            l2.set_tags(_values={t3: "stringval"})

        # location with other proj should not work
        with self.assertRaisesRegex(ValidationError, "Location project must match sample project"):
            news = Sample(project=self.proj1, name="loc", location=l3, collected=timezone.now())
            news.full_clean()

        # parent sample with other proj should not work
        with self.assertRaisesRegex(ValidationError, "Parent must belong to same project as child"):
            news = Sample(project=self.proj2, name="loc", parent=s2, collected=timezone.now())
            news.full_clean()

        # parent location with other proj should not work
        with self.assertRaisesRegex(ValidationError, "Parent must belong to same project as child"):
            newl = Location(project=self.proj2, name="loc", parent=l2)
            newl.full_clean()
