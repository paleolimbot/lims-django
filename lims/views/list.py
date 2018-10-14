from django.views import generic
from django.shortcuts import get_object_or_404

from .. import models
from lims.data_view import query_string_filter
from .accounts import LimsLoginMixin
from .actions import SAMPLE_ACTIONS
from ..data_view import SampleDataViewWidget, ProjectDataViewWidget


class LimsListView(generic.TemplateView):

    def get_data_view(self):
        raise NotImplementedError()

    def get_queryset(self):
        raise NotImplementedError()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        if project is not None:
            context['project'] = project
        dv = self.get_data_view()
        if dv is not None:
            context['dv'] = dv.bind(
                self.get_queryset(),
                self.request,
                project=context['project'] if 'project' in context else None
            )
        return context

    def get_project(self):
        if 'project_id' in self.kwargs:
            return get_object_or_404(models.Project, pk=self.kwargs['project_id'])
        else:
            return None


class ProjectListView(LimsLoginMixin, LimsListView):
    template_name = "lims/lists/project_list.html"

    def get_data_view(self):
        return ProjectDataViewWidget()

    def get_queryset(self):
        return models.Project.objects.all()


class SampleListView(LimsLoginMixin, LimsListView):
    template_name = 'lims/lists/sample_list.html'

    def get_data_view(self):
        return SampleDataViewWidget(actions=SAMPLE_ACTIONS)

    def get_queryset(self):
        return models.Sample.objects.all()
