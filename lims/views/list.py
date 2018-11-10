from django.views import generic
from django.shortcuts import get_object_or_404

from .. import models
from .accounts import LimsLoginMixin
from .actions import SAMPLE_ACTIONS
from ..widgets.data_widget import SampleDataWidget, ProjectDataWidget, AttachmentDataWidget, TermDataWidget


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
        return ProjectDataWidget()

    def get_queryset(self):
        return models.Project.objects.all()


class SampleListView(LimsLoginMixin, LimsListView):
    template_name = 'lims/lists/sample_list.html'

    def get_data_view(self):
        return SampleDataWidget(actions=SAMPLE_ACTIONS)

    def get_queryset(self):
        return models.Sample.objects.all()


class AttachmentListView(LimsLoginMixin, LimsListView):
    template_name = 'lims/lists/attachment_list.html'

    def get_data_view(self):
        return AttachmentDataWidget()

    def get_queryset(self):
        return models.Attachment.objects.all()


class TermListView(LimsLoginMixin, LimsListView):
    template_name = 'lims/lists/term_list.html'

    def get_data_view(self):
        return TermDataWidget()

    def get_queryset(self):
        return models.Term.objects.all()
