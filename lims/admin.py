from django.contrib import admin
from django.db.models import TextField
from django.forms import Textarea
from reversion.admin import VersionAdmin

from . import models

# This text override gets used in all models to keep the size down
text_overrides = {
    TextField: {'widget': Textarea(attrs={'rows': 2, 'cols': 40})},
}


# define base class that all models inherit
class LimsAdmin(VersionAdmin):
    formfield_overrides = text_overrides

    def save_model(self, request, obj, form, change):
        if hasattr(obj, 'user'):
            # save created user from admin login
            if obj.user is None and not obj.pk:
                obj.user = request.user
        return super().save_model(request, obj, form, change)


class TermValidatorInline(admin.TabularInline):
    model = models.TermValidator
    formfield_overrides = text_overrides
    extra = 1


@admin.register(models.BaseValidator)
class BaseValidatorAdmin(LimsAdmin):
    pass


@admin.register(models.Term)
class TermAdmin(LimsAdmin):
    inlines = [TermValidatorInline, ]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ['name', 'slug']
    autocomplete_fields = ['parent', 'project']


class SampleTagInline(admin.TabularInline):
    model = models.SampleTag
    formfield_overrides = text_overrides
    extra = 1
    autocomplete_fields = ['key', ]


class ProjectTagInline(admin.TabularInline):
    model = models.ProjectTag
    formfield_overrides = text_overrides
    extra = 1
    autocomplete_fields = ['key', ]


class ProjectPermissionInline(admin.TabularInline):
    model = models.ProjectPermission
    formfield_overrides = text_overrides
    extra = 1


class SampleEntryTemplateFieldInline(admin.TabularInline):
    model = models.EntryTemplateField
    formfield_overrides = text_overrides
    extra = 1
    ordering = ('order', )


class AttachmentTagInline(admin.TabularInline):
    model = models.AttachmentTag
    formfield_overrides = text_overrides
    extra = 1
    autocomplete_fields = ['key', ]


@admin.register(models.Attachment)
class AttachmentAdmin(LimsAdmin):
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ['project', 'samples', 'sample_tags']
    search_fields = ['name', 'slug', 'description', 'file_hash']
    inlines = [AttachmentTagInline, ]


@admin.register(models.Project)
class ProjectAdmin(LimsAdmin):
    inlines = [ProjectTagInline, ProjectPermissionInline]
    list_display = ('name', 'slug', 'user', 'modified')
    autocomplete_fields = ['parent', 'user']
    search_fields = ['name', 'slug']
    ordering = ['-modified', ]


@admin.register(models.Sample)
class SampleAdmin(LimsAdmin):
    inlines = [SampleTagInline, ]
    list_display = ('slug', 'user', 'modified', 'collected')
    date_hierarchy = "collected"
    autocomplete_fields = ['project', 'user', 'parent']
    search_fields = ['slug', ]
    ordering = ['-modified', ]


@admin.register(models.EntryTemplate)
class SampleEntryTemplateAdmin(LimsAdmin):
    inlines = [SampleEntryTemplateFieldInline, ]


@admin.register(models.SampleTag)
class SampleTagAdmin(admin.ModelAdmin):
    autocomplete_fields = ['key', 'object']
    search_fields = ['key__name', 'key__slug', 'object__slug']
    ordering = ['-modified', ]


@admin.register(models.AttachmentTag)
class AttachmentTagAdmin(admin.ModelAdmin):
    autocomplete_fields = ['key', 'object']
    search_fields = ['key__name', 'key__slug', 'object__slug']
    ordering = ['-modified', ]
