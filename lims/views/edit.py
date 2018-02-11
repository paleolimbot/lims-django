
from django.views import generic

from .. import models
from .accounts import LimsLoginMixin
from .forms import BaseObjectModelForm, ObjectFormView, BulkEditViewBase, LocationSelect2Widget, SampleSelect2Widget


class SampleForm(BaseObjectModelForm):

    class Meta:
        model = models.Sample
        fields = ['collected', 'name', 'description', 'location', 'parent', 'geometry', 'published']
        widgets = {
            'location': LocationSelect2Widget,
            'parent': SampleSelect2Widget
        }


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
            'location': LocationSelect2Widget,
            'parent': SampleSelect2Widget
        }


class SampleBulkAddView(LimsLoginMixin, BulkEditViewBase):
    model = models.Sample

    def get_model_form_class(self):
        return SampleBulkAddForm
