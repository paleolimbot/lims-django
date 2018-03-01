
from django.views import generic

from .. import models
from .accounts import LimsLoginMixin
from .forms import BaseObjectModelForm, ObjectFormView, BulkEditViewBase,\
    LocationSelect2Widget, SampleSelect2Widget, DateTimePicker, TermSelect2Widget


HELP_TEXTS = {
    'Sample': {
        'collected': 'The date at which the sample was collected or subsampled from the parent sample.',
        'name': 'The user sample identifier, without duplicating the location identifier.',
        'description': 'Extra information about the sample that is not expressed in other fields.',
        'location': 'Choose a previously added location at which this sample was collected.',
        'parent': 'Choose a parent sample from which this sample was subsampled.',
        'geometry': 'Well-known-text (e.g. POINT (lon lat) that describes where this sample was collected.',
        'published': 'Publish a sample to make it visible to others, unpublish it to fix a sample ID.'
    },
    'SampleTag': {
        'object': 'The sample to which this tag should be assigned',
        'key': 'The term for which these values should be assigned',
        'value': 'The primary value associated with this tag',
        'meta': 'A JSON-encoded dictionary of key/value pairs, with keys as valid Term slugs'
    },
    'Location': {
        'name': 'The display name for this location.',
        'slug': 'A short, unique, concise identifier for this location.',
        'description': 'Extra information that is not captured in other fields.',
        'parent': 'The parent location for this location.',
        'geometry': 'Well-known-text (e.g. POINT (lon lat) that describes this location.',
    },
    'LocationTag': {
        'object': 'The location to which this tag should be assigned',
        'key': 'The term for which these values should be assigned',
        'value': 'The primary value associated with this tag',
        'meta': 'A JSON-encoded dictionary of key/value pairs, with keys as valid Term slugs'
    }
}

WIDGETS = {
    'Sample': {
        'collected': DateTimePicker,
        'location': LocationSelect2Widget,
        'parent': SampleSelect2Widget
    },
    'SampleTag': {
        'object': SampleSelect2Widget,
        'key': TermSelect2Widget
    },
    'Location': {
        'parent': LocationSelect2Widget
    },
    'LocationTag': {
        'object': LocationSelect2Widget,
        'key': TermSelect2Widget
    }
}


class SampleForm(BaseObjectModelForm):

    class Meta:
        model = models.Sample
        fields = ['collected', 'name', 'description', 'location', 'parent', 'geometry', 'published']
        widgets = WIDGETS['Sample']
        help_texts = HELP_TEXTS['Sample']


class LocationForm(BaseObjectModelForm):

    class Meta:
        model = models.Location
        fields = ['name', 'slug', 'description', 'parent', 'geometry']
        widgets = WIDGETS['Location']
        help_texts = HELP_TEXTS['Location']


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
        widgets = WIDGETS['Sample']


class SampleBulkAddView(LimsLoginMixin, BulkEditViewBase):
    model = models.Sample

    def get_model_form_class(self):
        return SampleBulkAddForm
