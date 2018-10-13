import re
import json

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.forms import CharField
from django.core.validators import RegexValidator
from django.utils.functional import cached_property

import reversion

from .utils.geometry import validate_wkt, wkt_bounds
from .utils.barcode import qrcode_html
from .validators import JSONDictValidator, resolve_validator, ValidatorError
from .widgets import resolve_input_widget, resolve_output_widget, WidgetError


class ObjectPermissionError(PermissionError):

    def __init(self, *args):
        super().__init__(*args)

    def get_object(self):
        return self.args[0]


class SlugIdField(models.CharField):

    def __init__(self, **kwargs):
        defaults = {
            'max_length': 55,
            'blank': True,
            'validators': [RegexValidator('[A-Za-z0-9._-]*')],
            'db_index': True
        }
        defaults.update(**kwargs)
        super().__init__(**defaults)

    @staticmethod
    def idify(obj):
        txt = re.sub(r'[^A-Za-z0-9._-]+', '-', str(obj).lower())
        return re.sub(r'(^-)|(-$)', '', txt)


class LimsModelField(models.CharField):
    """
    This field type specifies a model defined in this module.
    """

    def __init__(self, **kwargs):
        defaults = {
            'max_length': 55,
            'choices': (
                ('Sample', 'Sample'),
                ('SampleTag', 'Sample Tag'),
                ('Attachment', 'Attachment'),
                ('AttachmentTag', 'Attachment Tag'),
                ('Term', 'Term'),
                ('TermTag', 'Term Tag')
            )
        }
        defaults.update(**kwargs)
        super().__init__(**defaults)

    @staticmethod
    def get_model(model):
        """
        Resolve a model class from a string.

        :param model: A value from  this field
        :return: A model class
        """
        if model == 'Sample':
            return Sample
        elif model == 'SampleTag':
            return SampleTag
        elif model == 'SampleTagTag':
            return SampleTagTag
        elif model == 'Attachment':
            return Attachment
        elif model == 'AttachmentTag':
            return AttachmentTag
        elif model == 'Term':
            return Term
        elif model == 'TermTag':
            return TermTag
        elif model == 'Project':
            return Project
        elif model == 'ProjectTag':
            return ProjectTag
        else:
            raise ValueError('No such model: %s' % model)


class LimsStatusField(models.CharField):

    def __init__(self, **kwargs):
        defaults = {
            'max_length': 55,
            'choices': (
                ('auto-draft', 'Auto Draft'),
                ('draft', 'Draft'),
                ('published', 'Published')
            ),
            'default': 'published'
        }
        defaults.update(**kwargs)
        super().__init__(**defaults)


def object_queryset_for_user(model, user, permission):
    if user.is_staff:
        return model.objects.all()

    model_name = model.__name__
    if model_name == 'Project':
        return Project.objects.filter(
            models.Q(permissions__user=user) &
            models.Q(permissions__permission=permission) &
            models.Q(permissions__model='Project')
        )
    else:
        return model.objects.filter(
            models.Q(project__permissions__user=user) &
            models.Q(project__permissions__permission=permission) &
            models.Q(project__permissions__model=model_name)
        )


def tag_queryset_for_user(model, user, permission):
    if user.is_staff:
        return model.objects.all()

    model_name = re.sub(r'Tag$', '', model.__name__)
    if model_name == 'Project':
        return ProjectTag.objects.filter(
            models.Q(object__permissions__user=user) &
            models.Q(object__permissions__permission=permission) &
            models.Q(object__permissions__model='Project')
        )
    elif model_name == 'SampleTag':
        return model.objects.filter(
            models.Q(object__object__project__permissions__user=user) &
            models.Q(object__object__project__permissions__permission=permission) &
            models.Q(object__object__project__permissions__model='Sample')
        )
    else:
        return model.objects.filter(
            models.Q(object__project__permissions__user=user) &
            models.Q(object__project__permissions__permission=permission) &
            models.Q(object__project__permissions__model=model_name)
        )


def queryset_for_user(model, user, permission):
    if model.__name__.endswith('Tag'):
        return tag_queryset_for_user(model, user, permission)
    else:
        return object_queryset_for_user(model, user, permission)


def object_user_can(obj, user, permission, project=None):
    if user.is_staff:
        return True
    if project is None:
        project = obj.project

    model_name = type(obj).__name__
    try:
        ProjectPermission.objects.get(project=project, user=user, model=model_name, permission=permission)
        return True
    except ProjectPermission.DoesNotExist:
        return False


def tag_user_can(obj, user, permission, project=None):
    if user.is_staff:
        return True
    if project is None:
        project = obj.object.project

    model_name = re.sub(r'Tag$', '', type(obj).__name__)
    try:
        ProjectPermission.objects.get(project=project, user=user, model=model_name, permission=permission)
        return True
    except ProjectPermission.DoesNotExist:
        return False


class TagsMixin:
    tags = None
    project = None

    def default_taxonomy(self):
        return type(self).__name__

    def set_tags(self, _values=None, taxonomy=None, **kwargs):
        taxonomy = self.default_taxonomy() if taxonomy is None else taxonomy
        self.tags.all().delete()
        return self.add_tags(_values, taxonomy=taxonomy, **kwargs)

    def add_tags(self, _values=None, taxonomy=None, **kwargs):
        taxonomy = self.default_taxonomy() if taxonomy is None else taxonomy
        if _values is not None:
            kwargs.update(_values)

        # make sure all names are defined terms, ignore empty strings and None values
        for key, value in kwargs.items():
            if not value:
                continue
            term = Term.get_term(key, self.project, taxonomy=taxonomy, create=True)
            tag = self.tags.create(key=term, value=value)
            try:
                tag.full_clean()
            except ValidationError as e:
                tag.delete()
                raise e

    def update_tags(self, _values=None, taxonomy=None, **kwargs):
        taxonomy = self.default_taxonomy() if taxonomy is None else taxonomy

        if _values is not None:
            kwargs.update(_values)

        # make sure all names are defined terms
        for key, value in kwargs.items():
            term = Term.get_term(key, self.project, taxonomy=taxonomy, create=True)
            try:
                tag = self.tags.get(key=term)
                if value:
                    tag.value = value
                    tag.full_clean()
                    tag.save()
                else:
                    tag.delete()
            except ObjectDoesNotExist:
                if value:
                    tag = self.tags.create(key=term, value=value)
                    try:
                        tag.full_clean()
                    except ValidationError as e:
                        tag.delete()
                        raise e

    def get_tag(self, key, taxonomy=None, as_list=False):
        taxonomy = self.default_taxonomy() if taxonomy is None else taxonomy

        term = Term.get_term(key, self.project, taxonomy=taxonomy, create=False)
        if term is None:
            return None
        try:
            tags = self.tags.all().filter(key=term)
            if as_list:
                return [tag.value for tag in tags]
            elif tags:
                # always return the *last* value
                return tags[tags.count()-1].value
            else:
                return None
        except ObjectDoesNotExist:
            return None

    def get_tags(self, taxonomy=None):
        taxonomy = self.default_taxonomy() if taxonomy is None else taxonomy
        return {tag.key.slug: tag.value for tag in self.tags.filter(key__taxonomy=taxonomy)}


class BaseObjectModel(TagsMixin, models.Model):
    name = models.CharField(max_length=256)
    slug = SlugIdField()
    description = models.TextField(blank=True)
    project = None
    status = LimsStatusField()

    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    created = models.DateTimeField('created', auto_now_add=True)
    modified = models.DateTimeField('modified', auto_now=True)

    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='children')
    recursive_depth = models.IntegerField(default=0, editable=False)

    geometry = models.TextField(blank=True, validators=[validate_wkt, ])
    geo_xmin = models.FloatField(editable=False, blank=True, null=True, default=None)
    geo_xmax = models.FloatField(editable=False, blank=True, null=True, default=None)
    geo_ymin = models.FloatField(editable=False, blank=True, null=True, default=None)
    geo_ymax = models.FloatField(editable=False, blank=True, null=True, default=None)

    class Meta:
        abstract = True
        unique_together = ['project', 'slug']

    def _should_update_slug(self):
        return (self.status != 'published') or (not self.pk and not self.slug)

    def calculate_recursive_depth(self):
        if self.parent:
            return self.parent.calculate_recursive_depth() + 1
        else:
            return 0

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        if exclude is None or 'slug' not in exclude:
            if not self.slug and self.pk:
                raise ValidationError({'slug': ['slug cannot be changed to ""']})

        if exclude is None or 'parent' not in exclude:
            if hasattr(self, 'project') and self.parent:
                if self.parent.project != self.project:
                    raise ValidationError({'parent': ['Parent must belong to same project as child']})

    def save(self, *args, **kwargs):
        # cache the recursive depth (for future tree view)
        self.recursive_depth = self.calculate_recursive_depth()

        # set the slug if it is a new object
        if self._should_update_slug():
            self.slug = self.calculate_slug()

        # cache location info
        bounds = wkt_bounds(self.geometry)
        self.geo_xmin = bounds['xmin']
        self.geo_xmax = bounds['xmax']
        self.geo_ymin = bounds['ymin']
        self.geo_ymax = bounds['ymax']
        super().save(*args, **kwargs)

    def auto_slug_use(self):
        return [SlugIdField.idify(self.name)]

    def _duplicate_slug_queryset(self, possible_slug):
        return type(self).objects.filter(project=self.project, slug=possible_slug)

    def _possible_duplicate_slug_queryset(self, slug_prefix):
        return type(self).objects.filter(project=self.project, slug__startswith=slug_prefix)

    def calculate_slug(self):
        slug_parts = self.auto_slug_use()

        # this is constructed such that it should always finish in 2 iterations
        suffix_index = 0
        for iterations in range(20):

            suffix = '__%d' % suffix_index if suffix_index else ''

            # construct the sample slug
            id_str_prefix = '_'.join(item for item in slug_parts if item)
            id_str_prefix = id_str_prefix[:(55 - len(suffix))]
            id_str = id_str_prefix + suffix

            # make sure the id_str is unique
            other_object_with_slug = self._duplicate_slug_queryset(id_str)
            if self.pk:
                other_object_with_slug = other_object_with_slug.exclude(pk=self.pk)

            if other_object_with_slug.count() == 0:
                # no object with this slug, use it!
                return id_str
            else:
                # an object exists with this slug, find objects that could
                # possibly collide with the slug

                possible_collisions = self._possible_duplicate_slug_queryset(id_str_prefix).\
                    values_list('slug', flat=True)

                # find the maximum _suffix number for the slug
                suffix_re = re.compile('__([0-9]+)$')
                possible_collision_suffixes = [
                    int(suffix_re.search(slug).group(1)) for slug in possible_collisions if suffix_re.search(slug)
                ]
                suffix_index = max(possible_collision_suffixes) + 1 if possible_collision_suffixes else suffix_index + 1

        # this could theoretically happen but would probably be very difficult
        # because the previous code should resolve a valid sample ID in 2 iterations
        raise ValueError('Cannot create unique slug for object')

    def get_absolute_url(self):
        raise NotImplementedError()

    # TODO: these three links should be implemented as filters, not object methods
    def get_link(self):
        return format_html('<a href="{}">{}</a>', self.get_absolute_url(), self)

    def get_checkbox(self):
        return format_html('<input title="Select {}" type="checkbox" name="object-{}-selected"/>',
                           self, self.pk)

    def get_qrcode_html(self):
        return mark_safe(qrcode_html(self))

    def user_can(self, user, permission):
        return object_user_can(self, user=user, permission=permission)

    def __str__(self):
        return self.name


@reversion.register(follow=('tags', 'term_validators'))
class Term(BaseObjectModel):
    project = models.ForeignKey('Project', on_delete=models.PROTECT, null=True, blank=True, related_name='terms')
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_terms')
    parent = models.ForeignKey('self', on_delete=models.PROTECT, blank=True, null=True, related_name='children')

    taxonomy = models.CharField(max_length=55)
    measured = models.BooleanField(default=False)

    input_widget_class = models.CharField(max_length=55, default='TextInput')
    input_widget_arguments = models.TextField(validators=[JSONDictValidator(), ], blank=True)
    output_widget_class = models.CharField(max_length=55, default='IdentityOutput')
    output_widget_arguments = models.TextField(validators=[JSONDictValidator(), ], blank=True)

    class Meta:
        unique_together = ['project', 'taxonomy', 'slug']

    def _duplicate_slug_queryset(self, possible_slug):
        return type(self).objects.filter(project=self.project, taxonomy=self.taxonomy, slug=possible_slug)

    def _possible_duplicate_slug_queryset(self, slug_prefix):
        return type(self).objects.filter(project=self.project, taxonomy=self.taxonomy, slug__startswith=slug_prefix)

    def user_can(self, user, permission):
        return object_user_can(self, user=user, permission=permission)

    def get_absolute_url(self):
        return reverse_lazy('lims:term_detail', kwargs={'pk': self.pk})

    @cached_property
    def validators(self):
        return self.resolve_validators(strict=False)

    def resolve_validators(self, strict=False):
        if strict:
            validators = [v.resolve_validator(strict=True) for v in self.term_validators.order_by('order')]
        else:
            validators = [v.validator for v in self.term_validators.order_by('order')]

        return [v for v in validators if v is not None]

    @cached_property
    def input_widget(self):
        return self.resolve_input_widget(strict=False)

    @cached_property
    def output_widget(self):
        return self.resolve_output_widget(strict=False)

    def resolve_input_widget(self, strict=False):
        try:
            kwargs = json.loads(self.input_widget_arguments) if self.input_widget_arguments else {}
            return resolve_input_widget(self.input_widget_class, **kwargs)
        except WidgetError as e:
            if strict:
                raise ValidationError({'input_widget_class': [str(e), ]})
            else:
                return resolve_input_widget('TextInput')

    def resolve_output_widget(self, strict=False):
        try:
            kwargs = json.loads(self.output_widget_arguments) if self.output_widget_arguments else {}
            return resolve_output_widget(self.output_widget_class, **kwargs)
        except WidgetError as e:
            if strict:
                raise ValidationError({'output_widget_class': [str(e), ]})
            else:
                return resolve_output_widget('IdentityOutput')

    @cached_property
    def field(self):
        return self.resolve_field()

    def resolve_field(self, klass=CharField, **kwargs):
        defaults = {
            'label': '%s' % self,
            'validators': self.validators,
            'required': False,
            'help_text': self.description,
            'widget': self.input_widget
        }
        defaults.update(**kwargs)
        return klass(**defaults)

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)

        if exclude is None or not all(x in exclude for x in ('input_widget_arguments', 'input_widget_class')):
            self.resolve_input_widget(strict=True)

        if exclude is None or not all(x in exclude for x in ('output_widget_arguments', 'output_widget_class')):
            self.resolve_output_widget(strict=True)

    @staticmethod
    def get_term(string_key, project, taxonomy, create=True):

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
            return Term.objects.get(project=project, taxonomy=taxonomy, slug=SlugIdField.idify(string_key))
        except Term.DoesNotExist:
            try:
                return Term.objects.get(project=project, taxonomy=taxonomy, name=string_key)
            except Term.DoesNotExist:
                if create:
                    return Term.objects.create(
                        project=project,
                        taxonomy=taxonomy,
                        slug=SlugIdField.idify(string_key),
                        name=string_key
                    )
                else:
                    return None

    @staticmethod
    def queryset_for_user(user, permission='view'):
        return object_queryset_for_user(Term, user=user, permission=permission)


class TermValidator(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='term_validators')
    order = models.IntegerField(default=0)
    validator_class = models.CharField(max_length=55)
    validator_arguments = models.TextField(validators=[JSONDictValidator(), ], blank=True)

    @cached_property
    def validator(self):
        return self.resolve_validator(strict=False)

    def resolve_validator(self, strict=False):
        try:
            kwargs = json.loads(self.validator_arguments) if self.validator_arguments else {}
            return resolve_validator(self.validator_class, **kwargs)
        except ValidatorError as e:
            if strict:
                raise ValidationError({'validator_class': [str(e), ]})
            else:
                return None

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        self.resolve_validator(strict=True)

    def __str__(self):
        return '"%s" validator for term "%s%s"' % (self.term, self.validator_class, self.validator_arguments)


class Tag(models.Model):
    object = models.ForeignKey(BaseObjectModel, on_delete=models.CASCADE, related_name='tags', db_index=True)
    key = models.ForeignKey(Term, on_delete=models.PROTECT, db_index=True)
    value = models.TextField(blank=True)
    comment = models.TextField(blank=True)

    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    created = models.DateTimeField('created', auto_now_add=True)
    modified = models.DateTimeField('modified', auto_now=True)

    numeric_value = models.FloatField(default=None, editable=False, blank=True, null=True)
    numeric_value_autoset = models.BooleanField(default=True, editable=False)

    class Meta:
        abstract = True

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)

        if exclude is None or 'value' not in exclude:
            field = self.key.field
            try:
                field.clean(self.value)
            except ValidationError as e:
                raise ValidationError({'value': e.error_list})

        if exclude is None or ('object' not in exclude and 'key' not in exclude):
            if (self.key.project is not None) and (self.key.project != self.object.project):
                raise ValidationError(
                    {'object': ['Object project must match term project, or the term project must be None']}
                )

    def save(self, *args, **kwargs):
        # update parent object modified tag
        self.object.modified = timezone.now()
        self.object.save()

        # cache numeric value
        if self.numeric_value_autoset:
            if self.value is None:
                self.numeric_value = None
            else:
                try:
                    self.numeric_value = float(self.value)
                except ValueError:
                    if self.value.lower() == 'true':
                        self.numeric_value = 1
                    elif self.value.lower() == 'false':
                        self.numeric_value = 0
                    else:
                        self.numeric_value = None

        super().save(*args, **kwargs)

    @cached_property
    def project(self):
        return self.object.project

    def user_can(self, user, permission):
        return tag_user_can(self, user=user, permission=permission)

    def __str__(self):
        return '%s/%s="%s"' % (self.object, self.key, self.value)


@reversion.register()
class TermTag(Tag):
    object = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='tags')
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_term_tags')
    key = models.ForeignKey(Term, on_delete=models.PROTECT, db_index=True, related_name='term_tags')

    @staticmethod
    def queryset_for_user(user, permission='view'):
        tag_queryset_for_user(TermTag, user=user, permission=permission)


@reversion.register(follow=('tags', 'permissions'))
class Project(BaseObjectModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_projects')

    class Meta:
        unique_together = ['slug']

    def _duplicate_slug_queryset(self, possible_slug):
        return type(self).objects.filter(slug=possible_slug)

    def _possible_duplicate_slug_queryset(self, slug_prefix):
        return type(self).objects.filter(slug__startswith=slug_prefix)

    def auto_slug_use(self):
        return [SlugIdField.idify(self.name), ]

    def get_absolute_url(self):
        return reverse_lazy('lims:project_detail', kwargs={'pk': self.pk})

    def user_can(self, user, permission):
        return object_user_can(self, user=user, permission=permission, project=self)

    @staticmethod
    def get_all_terms(queryset):
        return Term.objects.filter(project_tags__object__in=queryset).distinct()

    @staticmethod
    def queryset_for_user(user, permission='view'):
        if user.is_staff:
            return Project.objects.all()

        return Project.objects.filter(
            models.Q(permissions__user=user) &
            models.Q(permissions__permission=permission) &
            models.Q(permissions__model='Project')
        )


@reversion.register()
class ProjectTag(Tag):
    object = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tags')
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_project_tags')
    key = models.ForeignKey(Term, on_delete=models.PROTECT, db_index=True, related_name='project_tags')

    @cached_property
    def project(self):
        return None

    def user_can(self, user, action):
        return self.object.user_can(user, action)

    @staticmethod
    def queryset_for_user(user, permission='view'):
        if user.is_staff:
            return ProjectTag.objects.all()
        return ProjectTag.objects.filter(
            models.Q(object__permissions__user=user) &
            models.Q(object__permissions__permission=permission) &
            models.Q(object__permissions__model='Project')
        )


@reversion.register()
class ProjectPermission(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='permissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lims_project_permissions')
    model = LimsModelField()
    permission = models.CharField(max_length=55, choices=(
        ('edit', 'Edit objects'),
        ('view', 'View objects')
    ))

    class Meta:
        # also creates index on these fields
        unique_together = ('project', 'user', 'model', 'permission')

    def __str__(self):
        return '%s/%s/%s/%s' % (self.project.slug, self.user.username, self.model, self.permission)


@reversion.register(follow=('tags', ))
class Sample(BaseObjectModel):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='samples')
    name = models.CharField(max_length=256, default='sample')
    slug = SlugIdField(unique=True)
    collected = models.DateTimeField('collected', default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_samples')
    status = LimsStatusField(default='draft')

    def auto_slug_use(self):
        # get parts of the calculated sample slug
        dt_str = str(self.collected.astimezone(timezone.get_default_timezone()).date()) if self.collected else ''
        user = self.user.username[:15] if self.user else ''
        hint = SlugIdField.idify(self.name)

        return [user, dt_str, hint]

    def get_absolute_url(self):
        return reverse_lazy('lims:sample_detail', kwargs={'pk': self.pk})

    def get_project(self):
        return self.project

    def delete(self, *args, **kwargs):
        # clear relations so they don't delete attachments
        self.attachments.clear()
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.project.modified = timezone.now()
        self.project.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.slug

    @staticmethod
    def get_all_terms(queryset):
        return Term.objects.filter(sample_tags__object__in=queryset).distinct()

    @staticmethod
    def queryset_for_user(user, permission='view'):
        return object_queryset_for_user(Sample, user=user, permission=permission)


@reversion.register(follow=('tags', ))
class SampleTag(TagsMixin, Tag):
    object = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='tags')
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_sample_tags')
    key = models.ForeignKey(Term, on_delete=models.PROTECT, db_index=True, related_name='sample_tags')

    def delete(self, *args, **kwargs):
        # clear relations so they don't delete attachments
        self.attachments.clear()
        return super().delete(*args, **kwargs)

    @staticmethod
    def queryset_for_user(user, permission='view'):
        return tag_queryset_for_user(SampleTag, user=user, permission=permission)


@reversion.register()
class SampleTagTag(Tag):
    object = models.ForeignKey(SampleTag, on_delete=models.CASCADE, related_name='tags')
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_sample_tag_tags')
    key = models.ForeignKey(Term, on_delete=models.PROTECT, db_index=True, related_name='sample_tag_tags')

    @staticmethod
    def queryset_for_user(user, permission='view'):
        return tag_queryset_for_user(SampleTagTag, user=user, permission=permission)


@reversion.register(follow='tags')
class Attachment(BaseObjectModel):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='attachments')
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_attachments')
    file = models.FileField(upload_to='attachments')
    file_hash = models.CharField(max_length=128, blank=True)
    mime_type = models.CharField(max_length=256, blank=True)

    samples = models.ManyToManyField(Sample, related_name='attachments', blank=True)
    sample_tags = models.ManyToManyField(SampleTag, related_name='attachments', blank=True)
    terms = models.ManyToManyField(Term, related_name='attachments', blank=True)
    term_tags = models.ManyToManyField(TermTag, related_name='attachments', blank=True)

    def delete(self, *args, **kwargs):
        # clear relations so they don't get deleted with attachments
        self.samples.clear()
        self.sample_tags.clear()
        self.terms.clear()
        self.term_tags.clear()
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        for sample in self.samples.all():
            if sample.project != self.project:
                raise ValidationError({'samples': ['At least one related sample is of a different project']})

        for sample_tag in self.sample_tags.all():
            if sample_tag.object.project != self.project:
                raise ValidationError({'sample_tags': ['At least one related sample tag is of a different project']})

        for term in self.terms.all():
            if term.project != self.project:
                raise ValidationError({'samples': ['At least one related term is of a different project']})

        for sample_tag in self.term_tags.all():
            if sample_tag.object.project != self.project:
                raise ValidationError({'term_tags': ['At least one related term tag is of a different project']})

    def get_absolute_url(self):
        return reverse_lazy('lims:attachment_detail', kwargs={'pk': self.pk})

    @staticmethod
    def get_all_terms(queryset):
        return Term.objects.filter(attachment_tags__object__in=queryset).distinct()

    @staticmethod
    def queryset_for_user(user, permission='view'):
        return object_queryset_for_user(Attachment, user=user, permission=permission)


@reversion.register()
class AttachmentTag(Tag):
    object = models.ForeignKey(Attachment, on_delete=models.CASCADE, related_name='tags')
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_attachment_tags')
    key = models.ForeignKey(Term, on_delete=models.PROTECT, db_index=True, related_name='attachment_tags')

    @staticmethod
    def queryset_for_user(user, permission='view'):
        return tag_queryset_for_user(AttachmentTag, user=user, permission=permission)

