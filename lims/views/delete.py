from django.shortcuts import redirect
from django.views import generic
from django.urls import reverse_lazy
from django.http import Http404
from django.db import transaction, IntegrityError
from django.utils.safestring import mark_safe
from django.utils.html import format_html

from .. import models
from .accounts import LimsLoginMixin


class MultiDeleteView(generic.ListView):
    model = None
    success_url = reverse_lazy('lims:index')

    def get_success_url(self):
        return self.request.GET.get('from', self.success_url)

    def get_queryset(self):
        id_in = self.request.GET.getlist('id__in')
        queryset = self.model.objects.all().filter(id__in=id_in)
        if not queryset:
            raise Http404('Could not find any objects to delete')
        if len(id_in) != queryset.count():
            raise Http404('Could not find all requested objects to delete')
        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super(MultiDeleteView, self).get_context_data(*args, **kwargs)
        if hasattr(self, 'errors'):
            context['errors'] = self.errors
        return context

    def post(self, request):
        current_user = request.user
        queryset = self.get_queryset()
        errors = []

        try:
            with transaction.atomic():
                for obj in queryset:
                    if obj.user_can(current_user, 'delete'):
                        obj.delete()
                    else:
                        raise models.ObjectPermissionError(obj)

        except IntegrityError as e:
            if hasattr(e, 'protected_objects') and e.protected_objects:
                items_str = ', '.join(obj.get_link() for obj in e.protected_objects[:10])
                if len(e.protected_objects) > 10:
                    items_str += '...plus %d more objects' % (len(e.protected_objects) - 10)
                errors.append(mark_safe('Some items could not be deleted due to relationships with other objects. '
                                        'These objects may include the following: ' + items_str))
            else:
                errors.append('Some items could not be deleted: %s' % e)

        except models.ObjectPermissionError as e:
            errors.append(
                format_html('You are not allowed to delete sample <a href="{}">{}</a>.',
                            e.get_object().get_absolute_url(), e.get_object())
            )

        if errors:
            self.errors = errors
            return self.get(request)
        else:
            return redirect(self.get_success_url())


class SampleDeleteView(LimsLoginMixin, MultiDeleteView):
    model = models.Sample
    template_name = 'lims/sample_delete.html'
    success_url = reverse_lazy('lims:sample_list')


class LocationDeleteView(LimsLoginMixin, MultiDeleteView):
    model = models.Location
    template_name = 'lims/location_delete.html'
    success_url = reverse_lazy('lims:location_list')


