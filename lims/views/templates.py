
from django.views import generic
from django.http import Http404

from .. import models
from .forms import BaseObjectModelForm, ObjectFormView, BulkEditViewBase, \
    LocationSelect2Widget, SampleSelect2Widget, DateTimePicker
from .accounts import LimsLoginMixin


class TemplateListView(generic.ListView):
    model = models.SampleEntryTemplate
    template_name = 'lims/lists/template_list.html'

    def get_queryset(self):
        return models.SampleEntryTemplate.objects.order_by('name')


def template_form_class_factory(template):
    model_fields = ['collected', 'name']
    tag_fields = []
    initial_values = {}
    for field in template.fields.all().order_by('order'):
        if field.target in ['collected', 'name']:
            initial_values[field.target] = field.initial_value
        elif field.target in ['description', 'location', 'parent', 'geometry', 'published']:
            model_fields.append(field.target)
            initial_values[field.target] = field.initial_value
        else:
            tag_fields.append(field.target)
            initial_values['tag_form_field_' + field.target] = field.initial_value

    class SampleBaseForm(BaseObjectModelForm):
        class Meta:
            model = models.Sample
            fields = model_fields

            widgets = {
                'collected': DateTimePicker,
                'location': LocationSelect2Widget,
                'parent': SampleSelect2Widget
            }

        def __init__(self, *args, **kwargs):
            kwargs['tag_field_names'] = tag_fields
            super().__init__(*args, **kwargs)

            for form_field in self.fields:
                if form_field in initial_values:
                    self.fields[form_field].initial = initial_values[form_field]

    return SampleBaseForm


class TemplateFormView(LimsLoginMixin, ObjectFormView, generic.CreateView):
    template_name = 'lims/template_form.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = None

    def dispatch(self, request, *args, **kwargs):
        try:
            self.template = models.SampleEntryTemplate.objects.get(pk=kwargs['template_pk'])
        except models.SampleEntryTemplate.DoesNotExist:
            raise Http404('Sample Entry Template not found.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs['template'] = self.template
        return kwargs

    def get_form_class(self):
        return template_form_class_factory(self.template)

    def get_success_url(self):
        return self.request.get_full_path()


class TemplateBulkView(LimsLoginMixin, BulkEditViewBase):
    model = models.Sample
    template_name = 'lims/template_bulk.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = None

    def dispatch(self, request, *args, **kwargs):
        try:
            self.template = models.SampleEntryTemplate.objects.get(pk=kwargs['template_pk'])
        except models.SampleEntryTemplate.DoesNotExist:
            raise Http404('Sample Entry Template not found.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs['template'] = self.template
        return kwargs

    def get_model_form_class(self):
        return template_form_class_factory(self.template)
