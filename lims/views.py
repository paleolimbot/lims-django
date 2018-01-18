import re

from django.shortcuts import redirect
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.core.paginator import Paginator

from . import models


class LimsLoginMixin(LoginRequiredMixin):
    login_url = '/admin/login/'


def index(request):
    return redirect(reverse_lazy('lims:sample_list'))


class SampleListView(LimsLoginMixin, generic.ListView):
    template_name = 'lims/sample_list.html'
    context_object_name = 'sample_list'

    def get_queryset(self):
        return models.Sample.objects.all()

    def get_context_data(self, **kwargs):
        context = super(SampleListView, self).get_context_data(**kwargs)
        query_params = self.request.GET

        # apply sample list filtering, ordering, and pagination based on query string params
        sample_list_context = filter_sample_table(context['sample_list'], query_params)

        context.update(sample_list_context)
        return context


class SampleDetailView(LimsLoginMixin, generic.DetailView):
    template_name = 'lims/sample_detail.html'
    model = models.Sample


class SampleAddView(LimsLoginMixin, generic.CreateView):
    model = models.Sample
    fields = ['name', 'collected', 'location']
    success_url = reverse_lazy('lims:sample_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(SampleAddView, self).form_valid(form)


class LocationListView(LimsLoginMixin, generic.ListView):
    template_name = 'lims/location_list.html'
    context_object_name = 'location_list'
    paginate_by = 100

    def get_queryset(self):
        return models.Location.objects.all()

    def get_context_data(self, *args, **kwargs):
        context = super(LocationListView, self).get_context_data(*args, **kwargs)
        return context


class LocationDetailView(LimsLoginMixin, generic.DeleteView):
    template_name = 'lims/location_detail.html'
    model = models.Location


class LocationAddView(LimsLoginMixin, generic.CreateView):
    model = models.Location
    fields = ['name', 'slug', 'parent', 'geometry']
    success_url = reverse_lazy('lims:location_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(LocationAddView, self).form_valid(form)


TAG_QUERY_KEY = re.compile(r"^tag_(.*)$")


def filter_sample_table(queryset, q):
    """
    Consistent filtering, ordering of sample tables based on query params:

    Date/times:
    created_start = The first allowed creation date/time, YYYY-MM-DDThh:mm:ssZ
    created_end = The last allowed creation date/time, YYYY-MM-DDThh:mm:ssZ
    collected_start = The first allowed collection date/time, YYYY-MM-DDThh:mm:ssZ
    collected_end = The last allowed collection date/time, YYYY-MM-DDThh:mm:ssZ
    modified_start = The first allowed modified date/time, YYYY-MM-DDThh:mm:ssZ
    modified_end = The last allowed modified date/time, YYYY-MM-DDThh:mm:ssZ

    Locations:
    location = value (matches location)
    location_regex = value (regex matches location ID)

    Tags:
    tag_* = "" (tag * not defined), = "__exists__" (tag * is defined), = value (tag = value)

    Pagination and ordering
    n_samples = number of results to show on a page (>1)
    paged = number of pages in (>1)
    order_by = values passed to QuerySet.order_by()


    :param queryset: The queryset of samples to filter
    :param q The QueryDict (e.g. request.GET)
    :return: A dictionary with additional context variables for the sample_table.html template
    """

    # Date/times:
    if q.get("created_start"):
        queryset = queryset.filter(created__gte=q["created_start"])

    if q.get("collected_start"):
        queryset = queryset.filter(collected__gte=q["collected_start"])

    if q.get("modified_start"):
        queryset = queryset.filter(modified__gte=q["modified_start"])

    if q.get("created_end"):
        queryset = queryset.filter(created__lte=q["created_end"])

    if q.get("collected_end"):
        queryset = queryset.filter(collected__lte=q["collected_end"])

    if q.get("modified_end"):
        queryset = queryset.filter(modified__lte=q["modified_end"])

    # Locations (can pass multiple IDs/slugs
    locations = q.getlist("location")
    if locations:
        queryset = queryset.filter(location__in=locations)

    location_regex = q.get("location_regex")
    if location_regex:
        queryset = queryset.filter(location__regex=location_regex)

    # tags (can pass query param as anything like tag_*)
    tag_keys = [key for key in q if TAG_QUERY_KEY.match(key)]
    for tag_key in tag_keys:
        tag = TAG_QUERY_KEY.match(tag_key).group(1)
        values = q.getlist(tag_key)
        # if any value is '__exists__', just filter anything that has that tag
        if any(value == "__exists__" for value in values):
            queryset = queryset.filter(sampletag__key=tag)
        elif any(value == "" for value in values):
            queryset = queryset.exclude(sampletag__key=tag)
        else:
            queryset = queryset.filter(sampletag__key=tag, sampletag__value__in=values)

    # Ordering
    order_by = q.getlist("order_by", ['-modified'])
    if order_by:
        queryset = queryset.order_by(*order_by)

    # apply pagination (100 samples per page)
    paged = q.get('paged', 1)
    more_context = {}

    try:
        paged = int(paged)
    except ValueError:
        more_context['sample_list'] = []
        more_context['pagination_error'] = 'Invalid page: "%s"' % paged
        return more_context

    paginator = Paginator(queryset, 100)

    if 1 <= paged <= paginator.num_pages:
        queryset = paginator.page(paged)
    else:
        queryset = []
        more_context['pagination_error'] = 'Page out of range: %d' % paged

    # provide next/previous page links
    if (paged + 1) <= paginator.num_pages:
        qs = q.copy()
        qs['paged'] = paged + 1
        more_context['next_link'] = qs.urlencode()

    if (paged - 1) > 0:
        qs = q.copy()
        qs['paged'] = paged - 1
        more_context['prev_link'] = qs.urlencode()

    more_context['paginator'] = paginator
    more_context['sample_list'] = queryset

    return more_context
