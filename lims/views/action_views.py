from django.shortcuts import redirect
from django.views import generic
from django.urls import reverse_lazy
from django.http import Http404
from django.db import IntegrityError
from django.utils.safestring import mark_safe
from django.utils.html import format_html
import reversion

from .. import models
from .accounts import LimsLoginMixin


class ActionListView(generic.ListView):
    success_url = reverse_lazy('lims:index')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.errors = []

    def add_error(self, obj):
        self.errors.append(obj)

    def get_success_url(self):
        return self.request.GET.get('from', self.success_url)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['errors'] = self.errors
        return context

    def get_queryset(self):
        id_in = self.request.GET.getlist('id__in')
        queryset = self.model.objects.all().filter(id__in=id_in)
        if not queryset:
            raise Http404('Could not find any objects')
        if len(id_in) != queryset.count():
            raise Http404('Could not find all requested objects')
        return queryset

    def post(self, request):
        try:
            self.do_action(request, self.get_queryset())
            if self.errors:
                return self.get(request)
            else:
                return redirect(self.get_success_url())
        except Http404:
            return redirect(self.get_success_url())

    def do_action(self, request, queryset):
        raise NotImplementedError()


class MultiDeleteView(ActionListView):
    model = None

    def do_action(self, request, queryset):
        current_user = request.user

        try:
            with reversion.create_revision():
                for obj in queryset:
                    if obj.user_can(current_user, 'delete'):
                        obj.delete()
                    else:
                        raise models.ObjectPermissionError(obj)

                # set meta information
                reversion.set_user(self.request.user)
                reversion.set_comment('deleted from MultiDeleteView')

        except IntegrityError as e:
            if hasattr(e, 'protected_objects') and e.protected_objects:
                items_str = ', '.join(obj.get_link() for obj in e.protected_objects[:10])
                if len(e.protected_objects) > 10:
                    items_str += '...plus %d more objects' % (len(e.protected_objects) - 10)
                self.add_error(mark_safe('Some items could not be deleted due to relationships with other objects. '
                                         'These objects may include the following: ' + items_str))
            else:
                self.add_error('Some items could not be deleted: %s' % e)

        except models.ObjectPermissionError as e:
            self.add_error(
                format_html('You are not allowed to delete sample <a href="{}">{}</a>.',
                            e.get_object().get_absolute_url(), e.get_object())
            )


class SampleDeleteView(LimsLoginMixin, MultiDeleteView):
    model = models.Sample
    template_name = 'lims/action_views/sample_delete.html'
    success_url = reverse_lazy('lims:sample_list')


class LocationDeleteView(LimsLoginMixin, MultiDeleteView):
    model = models.Location
    template_name = 'lims/action_views/location_delete.html'
    success_url = reverse_lazy('lims:location_list')


class SamplePrintBarcodeView(LimsLoginMixin, ActionListView):
    model = models.Sample
    template_name = 'lims/action_views/sample_print_barcode.html'

    def do_action(self, request, queryset):
        self.add_error("Barcode printing isn't implemented yet...")
