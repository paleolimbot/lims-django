import re

from django.shortcuts import redirect, render
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.core.paginator import Paginator

from . import models


class LimsLoginMixin(LoginRequiredMixin):
    login_url = '/admin/login/'


def index(request):
    # return render(request, 'lims/base.html', context={"view": {"request": request}})
    return redirect(reverse_lazy('lims:sample_list'))


class SampleListView(LimsLoginMixin, generic.ListView):
    template_name = 'lims/sample_list.html'
    paginate_by = 100

    def get_queryset(self):
        return query_string_filter(
            models.Sample.objects.all(),
            self.request.GET,
            use=("location__slug", "slug__contains")
        ).order_by("-modified")


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
        return query_string_filter(
            models.Location.objects.all(),
            self.request.GET,
            # use=("slug__contains", )
            use=UseEverything()
        ).order_by("-modified")


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


def query_string_filter(queryset, q, use=()):

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
