
import re

from django.views import generic
from django.http import QueryDict
from django.db.models import Q

from .. import models
from .accounts import LimsLoginMixin


class SampleListView(LimsLoginMixin, generic.ListView):
    template_name = 'lims/lists/sample_list.html'
    paginate_by = 50
    page_kwarg = 'sample_page'

    def get_context_data(self, *args, **kwargs):
        context = super(SampleListView, self).get_context_data(*args, **kwargs)
        context['actions'] = [
            {'value': 'delete-samples', 'label': 'Delete samples'},
            {'value': 'print-barcodes', 'label': 'Print barcodes'}
        ]
        return context

    def get_queryset(self):
        return query_string_filter(
            models.Sample.objects.all(),
            self.request.GET,
            use=(),
            search=('name', 'slug', 'description'),
            prefix='sample_'
        ).order_by("-modified")


class LocationListView(LimsLoginMixin, generic.ListView):
    template_name = 'lims/lists/location_list.html'
    context_object_name = 'location_list'
    paginate_by = 50
    page_kwarg = 'location_page'

    def get_queryset(self):
        return query_string_filter(
            models.Location.objects.all(),
            self.request.GET,
            use=(),
            search=('name', 'slug', 'description'),
            prefix='location_'
        ).order_by("-modified")

    def get_context_data(self, *args, **kwargs):
        context = super(LocationListView, self).get_context_data(*args, **kwargs)
        context['actions'] = [
            {'value': 'delete-locations', 'label': 'Delete selected locations'}
        ]
        return context


def query_string_filter(queryset, query_dict, use=(), search=(), search_func="icontains", prefix=''):

    q = QueryDict(mutable=True)
    if prefix:
        prefix_re = re.compile('^' + prefix)
        for key in query_dict:
            if prefix_re.match(key):
                q.setlist(prefix_re.sub('', key), query_dict.getlist(key))
    else:
        q = query_dict.copy()

    if 'q' in q and search:
        query = q['q']
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
            value = q.getlist(key)
            if len(value) == 1:
                filter_args = {key: value[0]}
            else:
                filter_args = {key: value}
            queryset = queryset.filter(**filter_args)
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
