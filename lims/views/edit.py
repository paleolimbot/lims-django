
from django.views import generic

from .. import models
from .accounts import LimsLoginMixin
from .forms import BaseObjectModelForm, ObjectFormView, BulkEditViewBase,\
    LocationSelect2Widget, SampleSelect2Widget, DateTimePicker


SAMPLE_HELP_TEXTS = {
    'collected': 'The date at which the sample was collected or subsampled from the parent sample.',
    'name': 'The user sample identifier, without duplicating the location identifier.',
    'description': 'Extra information about the sample that is not expressed in other fields.',
    'location': 'Choose a previously added location at which this sample was collected.',
    'parent': 'Choose a parent sample from which this sample was subsampled.',
    'geometry': 'Well-known-text (e.g. POINT (lon lat) that describes where this sample was collected.',
    'published': 'Publish a sample to make it visible to others, unpublish it to fix a sample ID.'
}


class SampleForm(BaseObjectModelForm):

    class Meta:
        model = models.Sample
        fields = ['collected', 'name', 'description', 'location', 'parent', 'geometry', 'published']
        widgets = {
            'collected': DateTimePicker,
            'location': LocationSelect2Widget,
            'parent': SampleSelect2Widget
        }
        help_texts = SAMPLE_HELP_TEXTS


class LocationForm(BaseObjectModelForm):

    class Meta:
        model = models.Location
        fields = ['name', 'slug', 'description', 'parent', 'geometry']
        widgets = {
            'parent': LocationSelect2Widget
        }


class SampleAddView(LimsLoginMixin, ObjectFormView, generic.CreateView):
    template_name = 'lims/sample_form.html'
    form_class = SampleForm


class SampleChangeView(LimsLoginMixin, ObjectFormView, generic.UpdateView):
    model = models.Sample
    template_name = 'lims/sample_change.html'
    form_class = SampleForm


class LocationAddView(LimsLoginMixin, ObjectFormView, generic.CreateView):
    template_name = 'lims/location_form.html'
    form_class = LocationForm


class LocationChangeView(LimsLoginMixin, ObjectFormView, generic.UpdateView):
    model = models.Location
    template_name = 'lims/location_change.html'
    form_class = LocationForm


class SampleBulkAddForm(SampleForm):

    class Meta:
        fields = ['collected', 'name', 'description', 'location', 'parent']
        widgets = {
            'collected': DateTimePicker,
            'location': LocationSelect2Widget,
            'parent': SampleSelect2Widget
        }


class SampleBulkAddView(LimsLoginMixin, BulkEditViewBase):
    model = models.Sample

    def get_model_form_class(self):
        return SampleBulkAddForm
