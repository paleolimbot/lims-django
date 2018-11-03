
from collections import OrderedDict

from django.views import generic
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.contrib.auth.models import User

from .. import models
from .accounts import LimsLoginMixin
from .actions import SAMPLE_ACTIONS
from lims.data_view import SampleDataViewWidget, \
    TermDataViewWidget, AttachmentDataViewWidget, TagDataViewWidget, TermField, get_widget_class


class DetailViewWithTablesBase(generic.DetailView):

    def get_project(self):
        if 'project_id' in self.kwargs:
            return get_object_or_404(models.Project, pk=self.kwargs['project_id'])
        else:
            return None

    def get_sample_queryset(self):
        return self.object.samples.all()

    def get_term_queryset(self):
        return models.Term.objects.none()

    def get_tag_queryset(self):
        return self.object.tags.filter(key__taxonomy=self.model.__name__)

    def get_attachment_queryset(self):
        return self.object.attachments.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # add project
        view_project = self.get_project()
        if 'project' not in context and view_project is not None:
            context['project'] = view_project
        elif 'project' in context:
            view_project = context['project']

        sample_queryset = self.get_sample_queryset()
        if sample_queryset is not None:
            context['sample_dv'] = SampleDataViewWidget(
                name='samples',
                actions=SAMPLE_ACTIONS
            ).bind(sample_queryset, self.request, project=view_project)

        term_queryset = self.get_term_queryset()
        if term_queryset is not None:
            context['term_dv'] = TermDataViewWidget(
                name='terms',
                actions=()  # no term actions yet
            ).bind(term_queryset, self.request, project=view_project)

        attachment_queryset = self.get_attachment_queryset()
        if attachment_queryset is not None:
            context['attachment_dv'] = AttachmentDataViewWidget(
                name='attachments',
                actions=()  # no attachment actions yet
            ).bind(attachment_queryset, self.request, project=view_project)

        tags_queryset = self.get_tag_queryset()
        if tags_queryset is not None:
            tag_dv = TagDataViewWidget(
                name='tags',
                actions=()  # no tag actions yet
            )

            # remove the 'object' field, because we're already on the detail page
            for i, field in enumerate(list(tag_dv.fields)):
                if field.slug == 'object':
                    tag_dv.fields.pop(i)

            context['tags_dv'] = tag_dv.bind(tags_queryset, self.request, project=view_project)

        return context


class ProjectDetailView(LimsLoginMixin, DetailViewWithTablesBase):
    template_name = "lims/detail/project_detail.html"
    model = models.Project

    def get_project(self):
        return self.object


class SampleDetailView(LimsLoginMixin, DetailViewWithTablesBase):
    template_name = 'lims/detail/sample_detail.html'
    model = models.Sample

    def get_project(self):
        return self.object.project

    def get_sample_queryset(self):
        return self.object.children.all()


class UserDetailView(LimsLoginMixin, DetailViewWithTablesBase):
    template_name = 'lims/detail/user_detail.html'
    model = User

    def get_sample_queryset(self):
        return self.object.lims_samples.all()

    def get_attachment_queryset(self):
        return self.object.lims_attachments.all()

    def get_tag_queryset(self):
        return None


class TermDetailView(LimsLoginMixin, DetailViewWithTablesBase):
    template_name = 'lims/detail/term_detail.html'
    model = models.Term

    def get_project(self):
        return self.object.project

    def get_sample_queryset(self):
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        view_project = context['project'] if 'project' in context else None

        value_data_views = OrderedDict()
        for model in (models.Project, models.Sample, models.SampleTag, models.Attachment):
            widget_class = get_widget_class(model)

            value_data_views[model.__name__] = widget_class(
                TermField(self.object),
                name='tags_' + model.__name__.lower()
            ).bind(model.objects.filter(tags__key=self.object).distinct(), self.request, project=view_project)

        context['value_dvs'] = value_data_views
        return context


class AttachmentDetailView(LimsLoginMixin, DetailViewWithTablesBase):
    template_name = 'lims/detail/attachment_detail.html'
    model = models.Attachment

    def get_project(self):
        return self.object.project

    def get_sample_queryset(self):
        return self.object.samples.all()


class AttachmentDownloadView(LimsLoginMixin, generic.View):

    def dispatch(self, request, *args, **kwargs):
        obj = get_object_or_404(models.Attachment, pk=kwargs['pk'])
        return FileResponse(obj.file.open('rb'), filename=obj.file.name, as_attachment=True)
