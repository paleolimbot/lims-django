
import re

from django.views import generic
from django.http import QueryDict
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .. import models
from .accounts import LimsLoginMixin
from .actions import SAMPLE_ACTIONS


class LimsListView(generic.ListView):

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        project = self.get_project()
        if project is not None:
            context['project'] = project
        return context

    def get_project(self):
        if 'project_id' in self.kwargs:
            return get_object_or_404(models.Project, pk=self.kwargs['project_id'])
        else:
            return None


class ProjectListView(LimsLoginMixin, LimsListView):
    template_name = "lims/lists/project_list.html"
    paginate_by = 100
    page_kwarg = 'project_page'

    def get_queryset(self):
        return models.Project.objects.order_by('-modified')


class SampleListView(LimsLoginMixin, LimsListView):
    template_name = 'lims/lists/sample_list.html'
    paginate_by = 100
    page_kwarg = 'sample_page'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['actions'] = SAMPLE_ACTIONS
        return context

    def get_queryset(self):
        project = self.get_project()
        queryset = models.Sample.objects.all()
        if project is not None:
            queryset = queryset.filter(project=project)

        return query_string_filter(
            default_published_filter(queryset, self.request.user),
            self.request.GET,
            use=(),
            search=('name', 'slug', 'description'),
            prefix='sample_'
        ).order_by("-modified")


class MySampleListView(SampleListView):
    template_name = 'lims/lists/sample_list_my.html'

    def get_queryset(self):
        project = self.get_project()
        queryset = models.Sample.objects.filter(user=self.request.user)
        if project is not None:
            queryset = queryset.filter(project=project)

        return query_string_filter(
            queryset,
            self.request.GET,
            use=(),
            search=('name', 'slug', 'description'),
            prefix='sample_',
        ).order_by("-modified")


def default_published_filter(queryset, user):
    # in list views, published samples show up in everyone's view, but draft samples
    # show up in only the user's view. auto-draft samples never show up in a list view
    # but should show up in the admin view
    return queryset.filter(Q(status='published') | (Q(user=user) & Q(status='draft')))


def query_string_filter(queryset, query_dict, use=(), search=(), search_func="icontains", prefix=''):

    q = QueryDict(mutable=True)
    if prefix:
        prefix_re = re.compile('^' + prefix)
        for key in query_dict:
            if prefix_re.match(key):
                q.setlist(prefix_re.sub('', key), query_dict.getlist(key))
    else:
        q = query_dict.copy()

    # ignore empty query
    query = q.get('q', '')
    if query and search:
        search_queries = [{field + "__" + search_func: query} for field in search]
        final_q = None
        for search_query in search_queries:
            if final_q is None:
                final_q = Q(**search_query)
            else:
                final_q = Q(**search_query) | final_q
        queryset = queryset.filter(final_q)

    for key in q:
        if key in use:
            # make sure to ignore empty items! they cause errors
            value = q.getlist(key)
            if len(value) == 1:
                filter_args = {key: value[0]}
            else:
                filter_args = {key: [v for v in value if v]}
            queryset = queryset.filter(**{k: v for k, v in filter_args.items() if v})
        else:
            # ignore unwanted query string items
            pass

    return queryset


class UseEverything:
    """
    This is useful for debugging query_string filter, since it allows
    anything to be passed from the query string to filter().
    """

    def __contains__(self, item):
        return item not in ('page', 'q')
