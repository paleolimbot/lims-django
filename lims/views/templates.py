
from django.views import generic
from django.shortcuts import get_object_or_404

from .. import models
from .forms import BaseObjectModelForm, ObjectFormView, BulkEditViewBase
from .edit import HELP_TEXTS, WIDGETS
from .accounts import LimsLoginMixin


class TemplateListView(generic.ListView):
    model = models.EntryTemplate
    template_name = 'lims/lists/template_list.html'

    def get_project(self):
        if 'project_id' in self.kwargs:
            return get_object_or_404(models.Project, pk=self.kwargs['project_id'])
        else:
            return None

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['project'] = self.get_project()
        return context

    def get_queryset(self):
        return models.EntryTemplate.objects.order_by('name')


def template_form_class_factory(template):
    model_fields = []
    tag_fields = []
    initial_values = {}
    for field in template.get_fields_queryset():
        if field.target in template.get_model_fields():
            model_fields.append(field.target)
            initial_values[field.target] = field.initial_value
        else:
            tag_fields.append(field.target)
            initial_values['tag_form_field_' + field.target] = field.initial_value

    class ObjectBaseForm(BaseObjectModelForm):
        class Meta:
            model = template.get_model()
            fields = model_fields

            widgets = WIDGETS[template.model]
            help_texts = HELP_TEXTS[template.model]

        def __init__(self, *args, **kwargs):
            kwargs['tag_field_names'] = tag_fields
            kwargs['project'] = template.project
            super().__init__(*args, **kwargs)

            for form_field in self.fields:
                if form_field in initial_values:
                    self.fields[form_field].initial = initial_values[form_field]

    return ObjectBaseForm


class TemplateFormView(LimsLoginMixin, ObjectFormView, generic.CreateView):
    template_name = 'lims/forms/template_form.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = None

    def get_project(self):
        return self.template.project

    def dispatch(self, request, *args, **kwargs):
        self.template = get_object_or_404(models.EntryTemplate, pk=kwargs['template_pk'])
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
    model = None
    template_name = 'lims/forms/template_bulk.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = None

    def dispatch(self, request, *args, **kwargs):
        self.template = get_object_or_404(models.EntryTemplate, pk=kwargs['template_pk'])
        self.model = self.template.get_model()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs['template'] = self.template
        return kwargs

    def get_model_form_class(self):
        return template_form_class_factory(self.template)
