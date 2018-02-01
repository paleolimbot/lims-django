
from django.views import generic
from django.core.paginator import Paginator
from django.contrib.auth.models import User

from .. import models
from .accounts import LimsLoginMixin
from .list import query_string_filter, default_published_filter
from .actions import SAMPLE_ACTIONS, LOCATION_ACTIONS


class DetailViewWithTablesBase(generic.DetailView):

    def get_location_queryset(self):
        return self.object.location_set

    def get_sample_queryset(self):
        return self.object.sample_set

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sample_queryset = self.get_sample_queryset()

        if sample_queryset is not None:
            # setup the child samples list
            samples = query_string_filter(
                default_published_filter(self.get_sample_queryset().order_by('-modified'), self.request.user),
                self.request.GET,
                prefix='sample_'
            )
            sample_paginator = Paginator(samples, per_page=100)
            context['sample_page_obj'] = sample_paginator.page(self.request.GET.get('sample_page', 1))
            context['sample_page_kwarg'] = 'sample_page'

            # add some actions for the child samples
            context['sample_actions'] = SAMPLE_ACTIONS

        location_queryset = self.get_location_queryset()

        if location_queryset is not None:
            # setup the child locations list
            locations = query_string_filter(
                self.get_location_queryset().order_by('-modified'),
                self.request.GET,
                prefix='location_'
            )
            location_paginator = Paginator(locations, per_page=100)
            context['location_page_obj'] = location_paginator.page(self.request.GET.get('location_page', 1))
            context['location_page_kwarg'] = 'location_page'

            # add some actions for the child locations
            context['location_actions'] = LOCATION_ACTIONS

        return context


class SampleDetailView(LimsLoginMixin, DetailViewWithTablesBase):
    template_name = 'lims/sample_detail.html'
    model = models.Sample

    def get_sample_queryset(self):
        return self.object.children.all()

    def get_location_queryset(self):
        return None


class LocationDetailView(LimsLoginMixin, DetailViewWithTablesBase):
    template_name = 'lims/location_detail.html'
    model = models.Location

    def get_location_queryset(self):
        return self.object.children


class UserDetailView(LimsLoginMixin, DetailViewWithTablesBase):
    template_name = 'lims/user_detail.html'
    model = User


class TermDetailView(LimsLoginMixin, DetailViewWithTablesBase):
    template_name = 'lims/term_detail.html'
    model = models.Term

    def get_location_queryset(self):
        return models.Location.objects.filter(tags__key=self.object)

    def get_sample_queryset(self):
        return models.Sample.objects.filter(tags__key=self.object)
