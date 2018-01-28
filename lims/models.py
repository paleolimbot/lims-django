import re

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .utils.geometry import validate_wkt, wkt_bounds
from .utils.barcode import qrcode_html


class ObjectPermissionError(PermissionError):

    def __init(self, obj, *args):
        super().__init__(*args)

    def get_object(self):
        return self.args[0]


class BaseObjectModel(models.Model):
    name = models.CharField(max_length=55)
    slug = models.SlugField(max_length=55, unique=True)
    description = models.TextField(blank=True)

    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    created = models.DateTimeField("created", auto_now_add=True)
    modified = models.DateTimeField("modified", auto_now=True)

    class Meta:
        abstract = True

    def get_absolute_url(self):
        raise NotImplementedError()

    def get_link(self):
        return format_html('<a href="{}">{}</a>', self.get_absolute_url(), self)

    def get_checkbox(self):
        return format_html('<input title="Select {}" type="checkbox" name="object-{}-selected"/>',
                           self, self.pk)

    def get_qrcode_html(self):
        return mark_safe(qrcode_html(self))

    def user_can(self, user, action):
        # non-existent users can't do anything
        if not user.pk:
            return False

        if user.is_staff or user == self.user:
            # owners and staff can do anything
            return True
        elif action == 'add':
            # any logged in user can add samples
            return True
        elif action == 'view':
            # any logged in user can view
            return True
        else:
            return False

    def __str__(self):
        return self.name


class Tag(models.Model):
    object = models.ForeignKey(BaseObjectModel, on_delete=models.CASCADE, related_name='tags')
    key = models.CharField(max_length=55)
    value = models.TextField(blank=True)

    created = models.DateTimeField("created", auto_now_add=True)
    modified = models.DateTimeField("modified", auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # update parent object modified tag
        self.object.modified = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return '%s="%s"' % (self.key, self.value)


class Location(BaseObjectModel):
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='children')
    recursive_depth = models.IntegerField(default=0, editable=False)

    geometry = models.TextField(blank=True, validators=[validate_wkt, ])
    minx = models.FloatField(editable=False, blank=True, null=True, default=None)
    maxx = models.FloatField(editable=False, blank=True, null=True, default=None)
    miny = models.FloatField(editable=False, blank=True, null=True, default=None)
    maxy = models.FloatField(editable=False, blank=True, null=True, default=None)

    def get_absolute_url(self):
        return reverse_lazy('lims:location_detail', kwargs={'pk': self.pk})

    def calculate_recursive_depth(self):
        if self.parent:
            return self.parent.calculate_recursive_depth() + 1
        else:
            return 0

    def save(self, *args, **kwargs):
        # cache the recursive depth and bounds
        self.recursive_depth = self.calculate_recursive_depth()
        bounds = wkt_bounds(self.geometry)
        self.minx = bounds['minx']
        self.maxx = bounds['maxx']
        self.miny = bounds['miny']
        self.maxy = bounds['maxy']

        super(Location, self).save(*args, **kwargs)


class LocationTag(Tag):
    object = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="tags")


class Sample(BaseObjectModel):
    collected = models.DateTimeField("collected")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, null=True, blank=True)

    def get_absolute_url(self):
        return reverse_lazy('lims:sample_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if not self.pk and not self.slug:
            self.slug = self.calculate_slug()
        super(Sample, self).save(*args, **kwargs)

    def calculate_slug(self):

        # get parts of the calculated sample slug
        dt_str = str(self.collected.date())
        location_slug = slugify(self.location.slug[:10]) if self.location else ""
        user = self.user.username[:15] if self.user else ""
        hint = slugify(self.name)

        # this is constructed such that it should always finish in 2 iterations
        suffix_index = 0
        for iterations in range(20):

            suffix = '_%d' % suffix_index if suffix_index else ''

            # construct the sample slug
            id_str_prefix = "_".join(item for item in [user, dt_str, location_slug, hint] if item)
            id_str_prefix = id_str_prefix[:(55 - len(suffix))]
            id_str = id_str_prefix + suffix

            # make sure the id_str is unique
            other_object_with_slug = Sample.objects.filter(slug=id_str)

            if other_object_with_slug.count() == 0:
                # no object with this slug, use it!
                return id_str
            else:
                # an object exists with this slug, find objects that could
                # possibly collide with the slug

                possible_collisions = Sample.objects.filter(
                    slug__startswith=id_str_prefix
                ).values_list('slug', flat=True)

                # find the maximum _suffix number for the slug
                suffix_re = re.compile('_([0-9]+)$')
                possible_collision_suffixes = [
                    int(suffix_re.search(slug).group(1)) for slug in possible_collisions if suffix_re.search(slug)
                ]
                suffix_index = max(possible_collision_suffixes) + 1 if possible_collision_suffixes else suffix_index + 1

        # this could theoretically happen but would probably be very difficult
        # because the previous code should resolve a valid sample ID in 2 iterations
        raise ValueError("Cannot create unique sample ID for sample")

    def __str__(self):
        return self.slug


class SampleTag(Tag):
    object = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name="tags")
