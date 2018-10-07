
from django.views import generic
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.core.paginator import Paginator
from django.contrib.auth.models import User

from .. import models
from .accounts import LimsLoginMixin
from .list import query_string_filter, default_published_filter
from .actions import SAMPLE_ACTIONS


class DetailViewWithTablesBase(generic.DetailView):

    def get_project(self):
        if 'project_id' in self.kwargs:
            return get_object_or_404(models.Project, pk=self.kwargs['project_id'])
        else:
            return None

    def get_sample_queryset(self):
        return self.object.sample_set

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
            if view_project is not None:
                sample_queryset = sample_queryset.filter(project=view_project)

            # setup the child samples list
            samples = query_string_filter(
                default_published_filter(
                    sample_queryset.order_by('-modified'),
                    self.request.user
                ),
                self.request.GET,
                prefix='sample_'
            )
            sample_paginator = Paginator(samples, per_page=100)
            context['sample_page_obj'] = sample_paginator.page(self.request.GET.get('sample_page', 1))
            context['sample_page_kwarg'] = 'sample_page'

            # add some actions for the child samples
            context['sample_actions'] = SAMPLE_ACTIONS

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


class TermDetailView(LimsLoginMixin, DetailViewWithTablesBase):
    template_name = 'lims/detail/term_detail.html'
    model = models.Term

    def get_project(self):
        return self.object.project

    def get_sample_queryset(self):
        return models.Sample.objects.filter(tags__key=self.object).distinct()


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
