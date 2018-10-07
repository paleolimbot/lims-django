
from django.views import generic
from django.urls import reverse_lazy

from .. import models
from .accounts import LimsLoginMixin
from .forms import BaseObjectModelForm, ObjectFormView, BulkEditViewBase,\
    SampleSelect2Widget, DateTimePicker, TermSelect2Widget


HELP_TEXTS = {
    'Sample': {
        'collected': 'The date at which the sample was collected or subsampled from the parent sample.',
        'name': 'The user sample identifier',
        'description': 'Extra information about the sample that is not expressed in other fields.',
        'parent': 'Choose a parent sample from which this sample was subsampled.',
        'geometry': 'Well-known-text (e.g. POINT (lon lat) that describes where this sample was collected.'
    },
    'SampleTag': {
        'object': 'The sample to which this tag should be assigned',
        'key': 'The term for which these values should be assigned',
        'value': 'The primary value associated with this tag',
        'meta': 'A JSON-encoded dictionary of key/value pairs, with keys as valid Term slugs'
    }
}

WIDGETS = {
    'Sample': {
        'collected': DateTimePicker,
        'parent': SampleSelect2Widget
    },
    'SampleTag': {
        'object': SampleSelect2Widget,
        'key': TermSelect2Widget
    }
}


class SampleForm(BaseObjectModelForm):

    class Meta:
        model = models.Sample
        fields = ['collected', 'name', 'description', 'parent', 'geometry']
        widgets = WIDGETS['Sample']
        help_texts = HELP_TEXTS['Sample']


class SampleAddView(LimsLoginMixin, ObjectFormView, generic.CreateView):
    template_name = 'lims/forms/sample_form.html'
    form_class = SampleForm

    def get_success_url(self):
        project = self.get_project()
        if project:
            return reverse_lazy('lims:project_my_sample_list', kwargs={"project_id": self.get_project().pk})
        else:
            return reverse_lazy('lims:my_sample_list')


class SampleChangeView(LimsLoginMixin, ObjectFormView, generic.UpdateView):
    model = models.Sample
    template_name = 'lims/forms/sample_change.html'
    form_class = SampleForm

    def get_project(self):
        return self.object.project

    def get_success_url(self):
        return reverse_lazy('lims:sample_detail', kwargs={'pk': self.kwargs['pk']})


class SampleBulkAddForm(SampleForm):

    class Meta:
        fields = ['collected', 'name', 'description', 'parent']
        widgets = WIDGETS['Sample']


class SampleBulkAddView(LimsLoginMixin, BulkEditViewBase):
    model = models.Sample

    def get_model_form_class(self):
        return SampleBulkAddForm

    def get_success_url(self):
        project = self.get_project()
        if project:
            return reverse_lazy('lims:project_my_sample_list', kwargs={"project_id": self.get_project().pk})
        else:
            return reverse_lazy('lims:my_sample_list')
