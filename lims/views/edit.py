
from django.views import generic

from .. import models
from .accounts import LimsLoginMixin
from .forms import BaseObjectModelForm, ObjectSlugField, ObjectFormView, BulkEditViewBase


class SampleForm(BaseObjectModelForm):
    location = ObjectSlugField(models.Location, required=False)
    parent = ObjectSlugField(models.Sample, required=False)

    class Meta:
        model = models.Sample
        fields = ['collected', 'name', 'description', 'location', 'parent', 'geometry', 'published']


class LocationForm(BaseObjectModelForm):
    parent = ObjectSlugField(models.Location, required=False)

    class Meta:
        model = models.Location
        fields = ['name', 'slug', 'description', 'parent', 'geometry']


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


class SampleBulkAddView(LimsLoginMixin, BulkEditViewBase):
    model = models.Sample

    def get_model_form_class(self):
        return SampleForm
