from django.contrib import admin
from django.db.models import TextField
from django.forms import Textarea

from .models import Sample, SampleTag, Location, LocationTag

# This text override gets used in all models to keep the size down
text_overrides = {
    TextField: {'widget': Textarea(attrs={'rows': 2, 'cols': 40})},
}


# define base class that all models inherit
class LimsAdmin(admin.ModelAdmin):
    formfield_overrides = text_overrides

    def save_model(self, request, obj, form, change):
        # save created user from admin login
        if obj.user is None and not obj.pk:
            obj.user = request.user
        obj.save()


class LocationTagInline(admin.TabularInline):
    model = LocationTag
    formfield_overrides = text_overrides
    extra = 1


class SampleTagInline(admin.TabularInline):
    model = SampleTag
    formfield_overrides = text_overrides
    extra = 1


@admin.register(Sample)
class SampleAdmin(LimsAdmin):
    inlines = [SampleTagInline, ]
    list_display = ('slug', 'user', 'location', 'modified', 'collected')
    date_hierarchy = "collected"
    autocomplete_fields = ['location', 'user']
    search_fields = ['slug', ]


@admin.register(Location)
class LocationAdmin(LimsAdmin):
    inlines = [LocationTagInline, ]
    prepopulated_fields = {"slug": ("name", )}
    list_display = ('name', 'slug', 'parent', 'user', 'modified')
    autocomplete_fields = ['parent', 'user']
    search_fields = ['name', 'slug']
