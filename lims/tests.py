
from random import randint
from django.test import TestCase
from django.utils import timezone
from django.db import transaction

from .models import Sample, Location, SampleTag, LocationTag


def populate_test_data(n_locations=150, n_sub_locations=150, n_samples=700, max_tags=3, clear=True):

    with transaction.atomic():

        if clear:
            print("Clearing previous test data...")
            clear_models(
                models=(Sample, ),
                queryset=lambda model: model.objects.filter(slug__contains="_test-sample")
            )
            clear_models(
                models=(Location, ),
                queryset=lambda model: model.objects.filter(slug__startswith="test-")
            )

        print("Generating locations...")
        for loc_num in range(n_locations):
            print("\r%d/%d" % (loc_num + 1, n_locations), end='')

            loc = Location(
                name="Test Location %d" % (loc_num + 1),
                slug="test-location-%d" % (loc_num + 1),
                geometry="POINT (%d %d)" % (randint(-179, 180), randint(-85, 86))
            )
            loc.save()

            n_tags = randint(0, max_tags)
            for tag_num in range(n_tags):
                tag = LocationTag(
                    object=loc,
                    key="key%d" % (tag_num + 1),
                    value="value%d" % (tag_num + 1)
                )
                tag.save()

        print("\nGenerating sub-locations...")
        for loc_num in range(n_sub_locations):
            print("\r%d/%d" % (loc_num + 1, n_sub_locations), end='')

            n_locs = Location.objects.all().count()
            parent_loc = Location.objects.all()[randint(0, n_locs - 1)]
            loc = Location(
                name="Test Sub Location %d" % (loc_num + 1),
                slug="test-sub-location-%d" % (loc_num + 1),
                parent=parent_loc
            )
            loc.save()

            n_tags = randint(0, max_tags)
            for tag_num in range(n_tags):
                tag = LocationTag(
                    object=loc,
                    key="key%d" % (tag_num + 1),
                    value="value%d" % (tag_num + 1)
                )
                tag.save()

        print("\nGenerating samples...")
        for sample_num in range(n_samples):
            print("\r%d/%d" % (sample_num + 1, n_samples), end='')

            n_locs = Location.objects.all().count()
            loc_index = randint(0, int(n_locs * 1.5))
            if loc_index < n_locs:
                parent_loc = Location.objects.all()[loc_index]
            else:
                parent_loc = None

            sample = Sample(
                name="Test Sample %s" % (sample_num + 1),
                location=parent_loc
            )
            sample.collected = timezone.now()
            sample.save()

            n_tags = randint(0, max_tags)
            for tag_num in range(n_tags):
                tag = SampleTag(
                    object=sample,
                    key="key%d" % (tag_num + 1),
                    value="value%d" % (tag_num + 1)
                )
                tag.save()

        print("\nComplete!")


def clear_models(models=(Sample, Location), queryset=lambda model: model.objects.all()):
    print("Clearing models...")
    for recursive_depth in range(10):
        print("Recursive depth: %d" % recursive_depth)
        deleted = 0
        for model in models:
            print("Model %s" % model)
            qs = queryset(model)
            qs_len = qs.count()
            for obj in qs:
                try:
                    obj.delete()
                    deleted += 1
                    print("\r%d/%d" % (deleted, qs_len), end='')
                except Exception:
                    pass
            print("")
        model_counts = [queryset(model).count() for model in models]
        if not any(model_counts):
            print("Clearing complete.")
            return

    raise Exception("Could not delete all models")
