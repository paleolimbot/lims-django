
import re

from random import randint
from django.test import TestCase
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Sample, Location, SampleTag, LocationTag


def populate_test_data(n_locations=150, n_sub_locations=150, n_samples=700, max_tags=3, test_user=None,
                       clear=True, quiet=False):

    with transaction.atomic():

        if test_user is None:
            try:
                test_user = User.objects.get(username='tuser31848')
            except User.DoesNotExist:
                test_user = User.objects.create(username='tuser31848')

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

        if not quiet:
            print("Generating locations...")
        for loc_num in range(n_locations):
            if not quiet:
                print("\r%d/%d" % (loc_num + 1, n_locations), end='')

            loc = Location.objects.create(
                name="Test Location %d" % (loc_num + 1),
                slug="test-location-%d" % (loc_num + 1),
                geometry="POINT (%d %d)" % (randint(-179, 180), randint(-85, 86)),
                user=test_user
            )

            n_tags = randint(0, max_tags)
            for tag_num in range(n_tags):
                LocationTag.objects.create(
                    object=loc,
                    key="key%d" % (tag_num + 1),
                    value="value%d" % (tag_num + 1)
                )
        if not quiet:
            print("\nGenerating sub-locations...")
        for loc_num in range(n_sub_locations):
            if not quiet:
                print("\r%d/%d" % (loc_num + 1, n_sub_locations), end='')

            n_locs = Location.objects.all().count()
            parent_loc = Location.objects.all()[randint(0, n_locs - 1)]
            loc = Location.objects.create(
                name="Test Sub Location %d" % (loc_num + 1),
                slug="test-sub-location-%d" % (loc_num + 1),
                parent=parent_loc,
                user=test_user
            )

            n_tags = randint(0, max_tags)
            for tag_num in range(n_tags):
                tag = LocationTag(
                    object=loc,
                    key="key%d" % (tag_num + 1),
                    value="value%d" % (tag_num + 1)
                )
                tag.save()

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
                name="Test Sample %s" % (sample_num + 1),
                location=parent_loc,
                collected=timezone.now(),
                user=test_user
            )

            n_tags = randint(0, max_tags)
            for tag_num in range(n_tags):
                tag = SampleTag.objects.create(
                    object=sample,
                    key="key%d" % (tag_num + 1),
                    value="value%d" % (tag_num + 1)
                )

        if not quiet:
            print("\nComplete!")


def clear_models(models=(Sample, Location), queryset=lambda model: model.objects.all(), quiet=False):
    if not quiet:
        print("Clearing models...")
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
                except Exception:
                    pass
            if not quiet:
                print("")
        model_counts = [queryset(model).count() for model in models]
        if not any(model_counts):
            if not quiet:
                print("Clearing complete.")
            return

    raise Exception("Could not delete all models")


class GeometryTestCase(TestCase):

    def test_wkt_bounds(self):
        """Test the wkt_bounds function"""
        from .geometry import wkt_bounds
        self.assertEqual(
            wkt_bounds("(1 1)"),
            {'minx': 1.0, 'maxx': 1.0, 'miny': 1.0, 'maxy': 1.0}
        )
        self.assertEqual(
            wkt_bounds("(-1.45 -2.45) (1.75 2.75)"),
            {'minx': -1.45, 'maxx': 1.75, 'miny': -2.45, 'maxy': 2.75}
        )

        self.assertEqual(
            wkt_bounds("(-1.45 -2.45) (1.75 2.75) (0, 0)"),
            {'minx': -1.45, 'maxx': 1.75, 'miny': -2.45, 'maxy': 2.75}
        )

        self.assertEqual(
            wkt_bounds(''),
            {'minx': None, 'maxx': None, 'miny': None, 'maxy': None}
        )
        self.assertEqual(
            wkt_bounds(None),
            {'minx': None, 'maxx': None, 'miny':  None, 'maxy': None}
        )

    def test_wkt_regex(self):
        from .geometry import POINT, POLYGON, LINESTRING, MULTIPOINT, MULTIPOLYGON, MULTILINESTRING

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

        from .geometry import identify_geometry

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

        from .geometry import validate_wkt

        self.assertIsNone(validate_wkt('POINT (30 10)'))
        self.assertIsNone(validate_wkt(''))
        self.assertIsNone(validate_wkt(None))
        with self.assertRaisesRegex(ValidationError, "The value is not valid"):
            validate_wkt('not valid wkt')


class LocationRecursionTestCase(TestCase):

    def test_recursive_locations(self):

        parent_loc = Location.objects.create(name="Location1", slug="location-1")
        child_loc = Location.objects.create(name="Sub Location 1", slug="sub-location-1", parent=parent_loc)
        child_loc_2 = Location.objects.create(name="Sub Location 2", slug="sub-location-2", parent=parent_loc)
        child_child_loc = Location.objects.create(name="Sub Sub Location", slug="sub-sub-location", parent=child_loc)

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

        location_no_geom = Location.objects.create(name="location1", slug="location1")
        self.assertEqual(location_no_geom.geometry, '')
        self.assertIsNone(location_no_geom.minx)
        self.assertIsNone(location_no_geom.maxx)
        self.assertIsNone(location_no_geom.miny)
        self.assertIsNone(location_no_geom.maxy)

        location_point = Location.objects.create(
            name='location2', slug='location2', geometry='POINT (30 10)'
        )
        self.assertEqual(location_point.geometry, 'POINT (30 10)')
        self.assertEqual(location_point.minx, 30)
        self.assertEqual(location_point.maxx, 30)
        self.assertEqual(location_point.miny, 10)
        self.assertEqual(location_point.maxy, 10)

        location_polygon = Location.objects.create(
            name='location3', slug='location3',
            geometry='MULTIPOLYGON (((30 20, 45 40, 10 40, 30 20)), ((15 5, 40 10, 10 20, 5 10, 15 5)))'
        )
        self.assertEqual(location_polygon.minx, 5)
        self.assertEqual(location_polygon.maxx, 45)
        self.assertEqual(location_polygon.miny, 5)
        self.assertEqual(location_polygon.maxy, 40)


class SampleTestCase(TestCase):

    def setUp(self):
        self.test_user = User.objects.create(username="test_user_with_a_long_name")
        self.test_location1 = Location.objects.create(
            name='test location 1 with a long name',
            slug='test_location_1_with_a_long_name',
            user=self.test_user
        )
        self.test_location2 = Location.objects.create(
            name='test location 2 with a long name',
            slug='test_location_2_with_a_long_name',
            user=self.test_user
        )

    def test_slug_calculation(self):
        """Test that unique slugs get generated for samples"""

        now = timezone.now()
        sample1 = Sample.objects.create(
            collected=now,
            name='a quite long name',
            location=self.test_location1,
            user=self.test_user
        )
        self.assertTrue(len(sample1.slug), 55)

        sample2 = Sample.objects.create(
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
                Sample.objects.create(collected=now, user=self.test_user, name='sample_repeat')

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
        sample = Sample.objects.create(collected=timezone.now(), user=self.test_user)
        self.assertEqual(sample.slug, str(sample))

    def tearDown(self):
        for sample in Sample.objects.filter(user=self.test_user):
            sample.delete()
        self.test_location1.delete()
        self.test_location2.delete()
        self.test_user.delete()


class TestDataTestCase(TestCase):

    def setUp(self):
        self.test_user = User.objects.create(username='tuser')

    def test_sample_data_creation(self):
        """Test that the populate sample data method populates and re-populates properly"""

        # starting with an empty db, the app should populate the correct number of samples
        populate_test_data(n_locations=28, n_sub_locations=31, n_samples=109, test_user=self.test_user,
                           quiet=True)
        self.assertEqual(Location.objects.filter(user=self.test_user).count(), 59)
        self.assertEqual(Sample.objects.filter(user=self.test_user).count(), 109)

        # starting with an full db of test data, the app should still populate the correct number of samples
        populate_test_data(n_locations=41, n_sub_locations=35, n_samples=27, test_user=self.test_user, clear=True,
                           quiet=True)
        self.assertEqual(Location.objects.filter(user=self.test_user).count(), 76)
        self.assertEqual(Sample.objects.filter(user=self.test_user).count(), 27)

    def tearDown(self):
        clear_models(queryset=lambda model: model.objects.filter(user=self.test_user), quiet=True)
        self.test_user.delete()
