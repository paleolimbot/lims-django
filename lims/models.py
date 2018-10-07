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


def validate_is_a_regex(value):
    try:
        re.compile(value)
    except Exception as e:
        raise ValidationError('Value is not a valid Python regex: %s' % e)


def validate_json_tags_dict(value):
    if not value:
        return
    try:
        obj = json.loads(value)
        if not isinstance(obj, dict):
            raise ValidationError('Value is not a valid JSON object')

    except ValueError:
        raise ValidationError('Value is not valid JSON')


class SlugIdField(models.CharField):

    def __init__(self, **kwargs):
        defaults = {
            'max_length': 55,
            'unique': True,
            'blank': True,
            'validators': [RegexValidator('[A-Za-z0-9._-]*')]
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
                ('AttachmentTag', 'Attachment Tag')
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
        elif model == 'Attachment':
            return Attachment
        elif model == 'AttachmentTag':
            return AttachmentTag
        else:
            raise ValueError('No such model: %s' % model)


def object_queryset_for_user(model, user, permission):
    if user.is_staff:
        return model.objects.all()

    model_name = model.__name__
    return model.objects.filter(
        models.Q(project__permissions__user=user) &
        models.Q(project__permissions__permission=permission) &
        models.Q(project__permissions__model=model_name)
    )


def tag_queryset_for_user(model, user, permission):
    if user.is_staff:
        return model.objects.all()

    model_name = re.sub(r'Tag$', '', model.__name__)
    return model.objects.filter(
        models.Q(object__project__permissions__user=user) &
        models.Q(object__project__permissions__permission=permission) &
        models.Q(object__project__permissions__model=model_name)
    )


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


class BaseObjectModel(models.Model):
    name = models.CharField(max_length=55)
    slug = SlugIdField()
    description = models.TextField(blank=True)
    project = None

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

    def _should_update_slug(self):
        return not self.pk and not self.slug

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
        return [SlugIdField.idify(self.name), ]

    def calculate_slug(self):
        slug_parts = self.auto_slug_use()
        model = type(self)

        # this is constructed such that it should always finish in 2 iterations
        suffix_index = 0
        for iterations in range(20):

            suffix = '_%d' % suffix_index if suffix_index else ''

            # construct the sample slug
            id_str_prefix = '_'.join(item for item in slug_parts if item)
            id_str_prefix = id_str_prefix[:(55 - len(suffix))]
            id_str = id_str_prefix + suffix

            # make sure the id_str is unique
            other_object_with_slug = model.objects.filter(slug=id_str)

            if other_object_with_slug.count() == 0:
                # no object with this slug, use it!
                return id_str
            else:
                # an object exists with this slug, find objects that could
                # possibly collide with the slug

                possible_collisions = model.objects.filter(
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
        raise ValueError('Cannot create unique slug for object')

    def get_absolute_url(self):
        raise NotImplementedError()

    def get_project(self):
        raise NotImplementedError()

    def get_link(self):
        return format_html('<a href="{}">{}</a>', self.get_absolute_url(), self)

    def get_checkbox(self):
        return format_html('<input title="Select {}" type="checkbox" name="object-{}-selected"/>',
                           self, self.pk)

    def get_qrcode_html(self):
        return mark_safe(qrcode_html(self))

    def user_can(self, user, permission):
        return object_user_can(self, user=user, permission=permission)

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

        # make sure all names are defined terms
        for key, value in kwargs.items():
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

    def __str__(self):
        return self.name


class BaseValidator(models.Model):
    name = models.CharField(max_length=55)
    description = models.TextField(blank=True)
    regex = models.TextField(validators=[validate_is_a_regex, ])
    error_message = models.TextField()

    def __str__(self):
        return self.name


class Term(models.Model):
    project = models.ForeignKey('Project', on_delete=models.PROTECT, null=True, blank=True, related_name='terms')
    taxonomy = models.CharField(max_length=55)
    name = models.CharField(max_length=55)
    slug = models.SlugField(max_length=55)
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_terms')
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.PROTECT, blank=True, null=True, related_name='children')

    measured = models.BooleanField(default=False)
    meta = models.TextField(blank=True, validators=[validate_json_tags_dict, ])

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)

        if exclude is None or 'parent' not in exclude:
            if self.parent and self.parent.project != self.project:
                raise ValidationError({'parent': ['Term project must match parent term project']})

    class Meta:
        unique_together = ['project', 'taxonomy', 'slug']

    def user_can(self, user, permission):
        return object_user_can(self, user=user, permission=permission)

    def get_absolute_url(self):
        return reverse_lazy('lims:term_detail', kwargs={'pk': self.pk})

    def get_link(self):
        return format_html('<a href="{}">{}</a>', self.get_absolute_url(), self)

    def get_validators(self):
        validators = []
        for validator in self.validators.all():
            validators.append(RegexValidator(validator.validator.regex, message=validator.validator.error_message))
        return validators

    @cached_property
    def form_field(self):
        return CharField(
            label='%s' % self,
            validators=self.get_validators(),
            required=False,
            help_text=self.description
        )

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
            return Term.objects.get(project=project, taxonomy=taxonomy, slug=slugify(string_key))
        except Term.DoesNotExist:
            try:
                return Term.objects.get(project=project, taxonomy=taxonomy, name=string_key)
            except Term.DoesNotExist:
                if create:
                    return Term.objects.create(
                        project=project,
                        taxonomy=taxonomy,
                        slug=slugify(string_key),
                        name=string_key
                    )
                else:
                    return None

    def __str__(self):
        return '%s/%s' % (self.taxonomy, self.name)

    @staticmethod
    def queryset_for_user(user, permission='view'):
        return object_queryset_for_user(Term, user=user, permission=permission)


class TermValidator(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='validators')
    validator = models.ForeignKey(BaseValidator, on_delete=models.PROTECT)

    def __str__(self):
        return '"%s" validator for term "%s"' % (self.term, self.validator)


class Tag(models.Model):
    object = models.ForeignKey(BaseObjectModel, on_delete=models.CASCADE, related_name='tags', db_index=True)
    key = models.ForeignKey(Term, on_delete=models.PROTECT, db_index=True)
    value = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    meta = models.TextField(blank=True, validators=[validate_json_tags_dict, ])

    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    created = models.DateTimeField('created', auto_now_add=True)
    modified = models.DateTimeField('modified', auto_now=True)

    class Meta:
        abstract = True

    def default_taxonomy(self):
        return 'default'

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)

        if exclude is None or 'value' not in exclude:
            field = self.key.form_field
            try:
                field.clean(self.value)
            except ValidationError as e:
                raise ValidationError({'value': e.error_list})

        if exclude is None or ('object' not in exclude and 'key' not in exclude):
            if self.key.project != self.object.project:
                raise ValidationError({'object': ['Object project must match term project']})

    def save(self, *args, **kwargs):
        # update parent object modified tag
        self.object.modified = timezone.now()
        self.object.save()
        super().save(*args, **kwargs)

    def user_can(self, user, permission):
        return tag_user_can(self, user=user, permission=permission)

    def set_tags(self, _values=None, _save=True, **kwargs):
        if _values is not None:
            kwargs.update(_values)

        # make sure all names are defined terms
        string_tags = {}
        for key, value in kwargs.items():
            if value:
                term = Term.get_term(key, self.object.project, self.default_taxonomy(), create=True)
                string_tags[term.slug] = value

        if kwargs:
            self.meta = json.dumps(string_tags)
        else:
            self.meta = ''

        if _save:
            self.save()

    def add_tags(self, _values=None, **kwargs):
        self.update_tags(_value=_values, **kwargs)

    def update_tags(self, _values=None, **kwargs):
        if _values is not None:
            kwargs.update(_values)
        tags = self.get_tags()
        tags.update(kwargs)
        self.set_tags(_values=tags)

    def get_tag(self, key):
        tags = self.get_tags()
        return tags[key] if key in tags else None

    def get_tags(self, taxonomy=None):
        if taxonomy is not None:
            raise NotImplementedError('taxonomy must be None for meta fields')
        tags = json.loads(self.meta) if self.meta else {}
        return tags

    @staticmethod
    def get_all_terms(queryset):
        all_terms = set()
        for tag in queryset:
            all_terms.update(tag.gettags().keys())
        return list(all_terms)

    def __str__(self):
        return '%s/%s="%s"' % (self.object, self.key, self.value)


class Project(BaseObjectModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_projects')

    def get_absolute_url(self):
        return reverse_lazy('lims:project_detail', kwargs={'pk': self.pk})

    def get_project(self):
        return self

    def user_can(self, user, permission):
        return object_user_can(self, user=user, permission=permission, project=self)

    @staticmethod
    def get_all_terms(queryset):
        return Term.objects.filter(projecttag__object__in=queryset).distinct()

    @staticmethod
    def queryset_for_user(user, permission='view'):
        if user.is_staff:
            return Project.objects.all()

        return Project.objects.filter(
            models.Q(permissions__user=user) &
            models.Q(permissions__permission=permission) &
            models.Q(permissions__model='Project')
        )


class ProjectTag(Tag):
    object = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tags')
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_project_tags')
    key = models.ForeignKey(Term, on_delete=models.PROTECT, db_index=True, related_name='project_tags')

    def user_can(self, user, action):
        return self.object.user_can(user, action)

    @staticmethod
    def queryset_for_user(user, permission='view'):
        if user.is_staff:
            return ProjectTag.objects.all()
        return ProjectTag.objects.filter(
            models.Q(object__project__permissions__user=user) &
            models.Q(object__project__permissions__permission=permission) &
            models.Q(object__project__permissions__model='Project')
        )


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


class Sample(BaseObjectModel):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='samples')
    name = models.CharField(max_length=55, default='sample')
    collected = models.DateTimeField('collected', default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_samples')
    status = models.CharField(
        max_length=55,
        choices=(
            ('auto-draft', 'Auto Draft'),
            ('draft', 'Draft'),
            ('published', 'Published')
        ),
        default='draft'
    )

    def _should_update_slug(self):
        return super()._should_update_slug() or (self.status != 'published')

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


class SampleTag(Tag):
    object = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='tags')
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_sample_tags')
    key = models.ForeignKey(Term, on_delete=models.PROTECT, db_index=True, related_name='sample_tags')
    numeric_value = models.FloatField(default=None, editable=False, blank=True, null=True)
    numeric_value_autoset = models.BooleanField(default=True, editable=False)

    def save(self, *args, **kwargs):
        if self.numeric_value_autoset:
            try:
                self.numeric_value = float(self.value)
            except ValueError:
                self.numeric_value = None
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # clear relations so they don't delete attachments
        self.attachments.clear()
        return super().delete(*args, **kwargs)

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)

        if exclude is None or ('key' not in exclude and 'object' not in exclude):
            if self.key.project != self.object.project:
                raise ValidationError({'key': ['Key project must match object project']})

    @staticmethod
    def queryset_for_user(user, permission='view'):
        return tag_queryset_for_user(SampleTag, user=user, permission=permission)


class Attachment(BaseObjectModel):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='attachments')
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_attachments')
    file = models.FileField(upload_to='attachments')
    file_hash = models.CharField(max_length=128, blank=True)
    mime_type = models.CharField(max_length=256, blank=True)

    samples = models.ManyToManyField(Sample, related_name='attachments', blank=True)
    sample_tags = models.ManyToManyField(SampleTag, related_name='attachments', blank=True)

    def delete(self, *args, **kwargs):
        # clear relations so they don't get deleted with attachments
        self.samples.clear()
        self.sample_tags.clear()
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        for sample in self.samples.all():
            if sample.project != self.project:
                raise ValidationError({'samples': ['At least one related sample is of a different project']})

        for sample_tag in self.sample_tags.all():
            if sample_tag.object.project != self.project:
                raise ValidationError({'sample_tags': ['At least one related sample tag is of a different project']})

    def get_absolute_url(self):
        return reverse_lazy('lims:attachment_detail', kwargs={'pk': self.pk})

    def get_project(self):
        return self.project

    @staticmethod
    def get_all_terms(queryset):
        return Term.objects.filter(attachment_tags__object__in=queryset).distinct()

    @staticmethod
    def queryset_for_user(user, permission='view'):
        return object_queryset_for_user(Attachment, user=user, permission=permission)


class AttachmentTag(Tag):
    object = models.ForeignKey(Attachment, on_delete=models.CASCADE, related_name='tags')
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='lims_attachment_tags')
    key = models.ForeignKey(Term, on_delete=models.PROTECT, db_index=True, related_name='attachment_tags')

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)

        if exclude is None or ('key' not in exclude and 'object' not in exclude):
            if self.key.project != self.object.project:
                raise ValidationError({'key': ['Key project must match object project']})

    @staticmethod
    def queryset_for_user(user, permission='view'):
        return tag_queryset_for_user(AttachmentTag, user=user, permission=permission)


class EntryTemplate(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='templates')
    user = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True)
    name = models.CharField(max_length=55, unique=True)
    model = LimsModelField()
    last_used = models.DateTimeField('last_used', auto_now=True)

    def get_model(self):
        LimsModelField.get_model(self.model)

    def get_model_fields(self):
        if self.model == 'Sample':
            return ['collected', 'name', 'description', 'parent', 'geometry']
        elif self.model == 'SampleTag' or self.model == 'AttachmentTag':
            return ['object', 'key', 'value', 'comment', 'meta']
        elif self.model == 'Attachment':
            return ['name', 'slug', 'description', 'parent', 'geometry']
        else:
            raise ValueError('No such model: %s' % self.model)

    def get_fields_queryset(self):
        return self.fields.order_by('order')

    def get_absolute_url(self):
        return reverse_lazy('lims:template_form', kwargs={'template_pk': self.pk})

    def get_project(self):
        return self.project

    def __str__(self):
        return self.name

    @staticmethod
    def queryset_for_user(user, permission='view'):
        return object_queryset_for_user(EntryTemplate, user=user, permission=permission)


class EntryTemplateField(models.Model):
    template = models.ForeignKey(EntryTemplate, on_delete=models.CASCADE, related_name='fields')
    taxonomy = models.CharField(max_length=55, default='', blank=True)
    target = models.CharField(max_length=55)
    initial_value = models.TextField(blank=True)
    order = models.IntegerField(default=1)

    def clean_fields(self, exclude=None):
        if exclude is None or 'target' not in exclude:
            # target should be a field of self.template.model or a Term
            if self.target not in self.template.get_model_fields() and self.term is None:
                raise ValidationError(
                    {'target': 'Target is not a field of %s and is not a defined term slug' % self.template.model}
                )

    def get_project(self):
        return self.template.get_project()

    def default_taxonomy(self):
        return self.template.get_model().__name__

    @cached_property
    def term(self):
        if self.target in self.template.get_model_fields():
            return None
        try:
            return Term.objects.get(
                slug=self.target,
                project=self.get_project(),
                taxonomy=self.taxonomy if self.taxonomy else self.default_taxonomy()
            )
        except Term.DoesNotExist:
            return None

    def __str__(self):
        term = self.term
        if term is None:
            return self.target.replace('_', ' ').title()
        else:
            return str(term)
