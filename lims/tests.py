
from random import randint
from django.test import TestCase
from django.utils import timezone

from .models import Sample, Location, SampleTag, LocationTag


def populate_test_data(n_locations=150, n_sub_locations=150, n_samples=700, max_tags=3, clear=True):

    if clear:
        clear_models(
            models=(Sample, ),
            queryset=lambda model: model.objects.filter(slug__contains="_test-sample")
        )
        clear_models(
            models=(Location, ),
            queryset=lambda model: model.objects.filter(slug__startswith="test-")
        )

    for loc_num in range(n_locations):
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
                key="key%d" % (tag_num +1),
                value="value%d" % (tag_num + 1)
            )
            tag.save()

    for loc_num in range(n_sub_locations):
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

    for sample_num in range(n_samples):
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


def clear_models(models=(Sample, Location), queryset=lambda model: model.objects.all()):
    for recursive_depth in range(10):
        for model in models:
            for obj in queryset(model):
                try:
                    obj.delete()
                except Exception:
                    pass
        model_counts = [queryset(model).count() for model in models]
        if not any(model_counts):
            return

    raise Exception("Could not delete all models")
