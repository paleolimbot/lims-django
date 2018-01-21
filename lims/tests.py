
import re

from random import randint
from django.test import TestCase
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User

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
