import re
import json

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.forms import CharField
from django.core.validators import RegexValidator
from django.utils.functional import cached_property

from .utils.geometry import validate_wkt, wkt_bounds
from .utils.barcode import qrcode_html


class ObjectPermissionError(PermissionError):

    def __init(self, *args):
        super().__init__(*args)

    def get_object(self):
        return self.args[0]


class BaseObjectModel(models.Model):
    name = models.CharField(max_length=55)
    slug = models.SlugField(max_length=55, unique=True, blank=True)
    description = models.TextField(blank=True)

    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    created = models.DateTimeField("created", auto_now_add=True)
    modified = models.DateTimeField("modified", auto_now=True)

    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='children')
    recursive_depth = models.IntegerField(default=0)

    geometry = models.TextField(blank=True, validators=[validate_wkt, ])
    minx = models.FloatField(editable=False, blank=True, null=True, default=None)
    maxx = models.FloatField(editable=False, blank=True, null=True, default=None)
    miny = models.FloatField(editable=False, blank=True, null=True, default=None)
    maxy = models.FloatField(editable=False, blank=True, null=True, default=None)

    def calculate_recursive_depth(self):
        if self.parent:
            return self.parent.calculate_recursive_depth() + 1
        else:
            return 0

    class Meta:
        abstract = True

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        if exclude is None or 'slug' not in exclude:
            if not self.slug and self.pk:
                raise ValidationError({'slug': ['slug cannot be changed to ""']})

    def save(self, *args, **kwargs):
        # cache the recursive depth (for future tree view)
        self.recursive_depth = self.calculate_recursive_depth()

        # set the slug if it is a new object
        if not self.pk and not self.slug:
            self.slug = self.calculate_slug()

        # cache location info
        bounds = wkt_bounds(self.geometry)
        self.minx = bounds['minx']
        self.maxx = bounds['maxx']
        self.miny = bounds['miny']
        self.maxy = bounds['maxy']
        super().save(*args, **kwargs)

    def auto_slug_use(self):
        return [slugify(self.name), ]

    def calculate_slug(self):
        slug_parts = self.auto_slug_use()
        ObjectType = type(self)

        # this is constructed such that it should always finish in 2 iterations
        suffix_index = 0
        for iterations in range(20):

            suffix = '_%d' % suffix_index if suffix_index else ''

            # construct the sample slug
            id_str_prefix = "_".join(item for item in slug_parts if item)
            id_str_prefix = id_str_prefix[:(55 - len(suffix))]
            id_str = id_str_prefix + suffix

            # make sure the id_str is unique
            other_object_with_slug = ObjectType.objects.filter(slug=id_str)

            if other_object_with_slug.count() == 0:
                # no object with this slug, use it!
                return id_str
            else:
                # an object exists with this slug, find objects that could
                # possibly collide with the slug

                possible_collisions = ObjectType.objects.filter(
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
        raise ValueError("Cannot create unique slug for object")

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

    def set_tags(self, _values=None, **kwargs):
        self.tags.all().delete()
        return self.add_tags(_values, **kwargs)

    def add_tags(self, _values=None, **kwargs):
        if _values is not None:
            kwargs.update(_values)

        # make sure all names are defined terms
        for key, value in kwargs.items():
            term = Term.get_term(key, create=True)
            self.tags.create(key=term, value=value)

    def update_tags(self, _values=None, **kwargs):
        if _values is not None:
            kwargs.update(_values)

        # make sure all names are defined terms
        for key, value in kwargs.items():
            term = Term.get_term(key, create=True)
            try:
                tag = self.tags.get(key=term)
                tag.value = value
                tag.save()
            except ObjectDoesNotExist:
                self.tags.create(key=term, value=value)

    def get_tag(self, key):
        term = Term.get_term(key, create=False)
        if term is None:
            return None
        try:
            return self.tags.get(key=term).value
        except ObjectDoesNotExist:
            return None

    def get_tags(self):
        return {tag.key.slug: tag.value for tag in self.tags.all()}

    def __str__(self):
        return self.name


def validate_is_a_regex(value):
    try:
        re.compile(value)
    except Exception as e:
        raise ValidationError('Value is not a valid Python regex: %s' % e)


class BaseValidator(models.Model):
    name = models.CharField(max_length=55)
    description = models.TextField(blank=True)
    regex = models.TextField(validators=[validate_is_a_regex, ])
    error_message = models.TextField()

    def __str__(self):
        return self.name


def validate_json_tags_dict(value):
    if not value:
        return
    try:
        obj = json.loads(value)
        if not isinstance(obj, dict):
            raise ValidationError("Value is not a valid JSON object")

    except ValueError:
        raise ValidationError("Value is not valid JSON")


class Term(models.Model):
    name = models.CharField(max_length=55)
    slug = models.SlugField(max_length=55, unique=True)
    description = models.TextField(blank=True)
    meta = models.TextField(blank=True, validators=[validate_json_tags_dict, ])

    def get_absolute_url(self):
        return reverse_lazy('lims:term_detail', self.pk)

    def get_link(self):
        return format_html('<a href="{}">{}</a>', self.get_absolute_url(), self)

    def get_validators(self):
        validators = []
        for validator in self.validators.all():
            validators.append(RegexValidator(validator.validator.regex, message=validator.validator.error_message))
        return validators

    @cached_property
    def form_field(self):
        return CharField(label='Tag %s' % self, validators=self.get_validators(), required=False)

    @staticmethod
    def get_term(string_key, create=True):
        # if it's already a term, return it
        if isinstance(string_key, Term):
            return string_key

        # if it is '' or None return None
        if not string_key:
            return None

        # take whitespace off of string_key
        string_key = string_key.strip()

        # try to get by name and slug
        try:
            return Term.objects.get(slug=slugify(string_key))
        except Term.DoesNotExist:
            try:
                return Term.objects.get(name=string_key)
            except Term.DoesNotExist:
                if create:
                    return Term.objects.create(name=string_key, slug=slugify(string_key))
                else:
                    return None

    def __str__(self):
        return self.name


class TermValidator(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='validators')
    validator = models.ForeignKey(BaseValidator, on_delete=models.PROTECT)

    def __str__(self):
        return '"%s" validator for term "%s"' % (self.term, self.validator)


class Tag(models.Model):
    object = models.ForeignKey(BaseObjectModel, on_delete=models.CASCADE, related_name='tags', db_index=True)
    key = models.ForeignKey(Term, on_delete=models.PROTECT, db_index=True)
    value = models.TextField(blank=True)

    created = models.DateTimeField("created", auto_now_add=True)
    modified = models.DateTimeField("modified", auto_now=True)

    class Meta:
        abstract = True

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)

        if exclude is None or 'value' not in exclude:
            field = self.key.form_field
            try:
                field.clean(self.value)
            except ValidationError as e:
                raise ValidationError({'value': e.error_list})

    def save(self, *args, **kwargs):
        # update parent object modified tag
        self.object.modified = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return '%s="%s"' % (self.key, self.value)


class Location(BaseObjectModel):

    def get_absolute_url(self):
        return reverse_lazy('lims:location_detail', kwargs={'pk': self.pk})

    @staticmethod
    def get_all_terms(queryset):
        return Term.objects.filter(locationtag__object__in=queryset).distinct()


class LocationTag(Tag):
    object = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="tags")


class Sample(BaseObjectModel):
    collected = models.DateTimeField("collected")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, null=True, blank=True)
    published = models.BooleanField(default=False)

    def auto_slug_use(self):
        # get parts of the calculated sample slug
        dt_str = str(self.collected.astimezone(timezone.get_default_timezone()).date())
        location_slug = slugify(self.location.slug[:10]) if self.location else ""
        user = self.user.username[:15] if self.user else ""
        hint = slugify(self.name)

        return [user, dt_str, location_slug, hint]

    def get_absolute_url(self):
        return reverse_lazy('lims:sample_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.slug

    @staticmethod
    def get_all_terms(queryset):
        return Term.objects.filter(sampletag__object__in=queryset).distinct()


class SampleTag(Tag):
    object = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name="tags")
