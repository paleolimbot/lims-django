
from django.views import generic
from django.core.paginator import Paginator
from django.contrib.auth.models import User

from .. import models
from .accounts import LimsLoginMixin
from .list import query_string_filter


class SampleDetailView(LimsLoginMixin, generic.DetailView):
    template_name = 'lims/sample_detail.html'
    model = models.Sample


class LocationDetailView(LimsLoginMixin, generic.DeleteView):
    template_name = 'lims/location_detail.html'
    model = models.Location

    def get_context_data(self, **kwargs):
        context = super(LocationDetailView, self).get_context_data(**kwargs)

        # setup the child samples list
        samples = query_string_filter(
            context['location'].sample_set.order_by('-modified'),
            self.request.GET,
            prefix='sample_'
        )
        sample_paginator = Paginator(samples, per_page=100)
        context['sample_page_obj'] = sample_paginator.page(self.request.GET.get('sample_page', 1))
        context['sample_page_kwarg'] = 'sample_page'

        # add some actions for the child samples
        context['sample_actions'] = [
            {'value': 'delete-samples', 'label': 'Delete samples'},
            {'value': 'print-barcodes', 'label': 'Print barcodes'}
        ]

        # setup the child locations list
        locations = query_string_filter(
            context['location'].children.order_by('-modified'),
            self.request.GET,
            prefix='location_'
        )
        location_paginator = Paginator(locations, per_page=10)
        context['location_page_obj'] = location_paginator.page(self.request.GET.get('location_page', 1))
        context['location_page_kwarg'] = 'location_page'

        # add some actions for the child locations
        context['location_actions'] = [
            {'value': 'delete-locations', 'label': 'Delete selected locations'}
        ]

        return context


class UserDetailView(LimsLoginMixin, generic.DeleteView):
    template_name = 'lims/user_detail.html'
    model = User

    def get_context_data(self, **kwargs):
        context = super(UserDetailView, self).get_context_data(**kwargs)

        # setup the child samples list
        samples = query_string_filter(
            context['user'].sample_set.order_by('-modified'),
            self.request.GET,
            prefix='sample_'
        )
        sample_paginator = Paginator(samples, per_page=100)
        context['sample_page_obj'] = sample_paginator.page(self.request.GET.get('sample_page', 1))
        context['sample_page_kwarg'] = 'sample_page'

        # add some actions for the child samples
        context['sample_actions'] = [
            {'value': 'delete-samples', 'label': 'Delete samples'},
            {'value': 'print-barcodes', 'label': 'Print barcodes'}
        ]

        # setup the child locations list
        locations = query_string_filter(
            context['user'].location_set.order_by('-modified'),
            self.request.GET,
            prefix='location_'
        )
        location_paginator = Paginator(locations, per_page=10)
        context['location_page_obj'] = location_paginator.page(self.request.GET.get('location_page', 1))
        context['location_page_kwarg'] = 'location_page'

        # add some actions for the child locations
        context['location_actions'] = [
            {'value': 'delete-locations', 'label': 'Delete selected locations'}
        ]

        return context
