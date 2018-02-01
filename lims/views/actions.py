
import re
import csv

from django.shortcuts import redirect
from django.views import generic
from django.urls import reverse_lazy
from django.http import Http404, HttpResponse, QueryDict, HttpResponseBadRequest
from django.db import IntegrityError
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.utils import timezone
import reversion

from .. import models
from .accounts import LimsLoginMixin
from .edit import SampleBulkAddView, SampleForm


def find_action_view(model, action):
    if model == 'location':
        action_list = LOCATION_ACTIONS
    elif model == 'sample':
        action_list = SAMPLE_ACTIONS
    else:
        raise Http404('No such model')

    for action_item in action_list:
        if action == action_item['value']:
            return action_item['view']

    raise Http404('No such action')


def resolve_action_view(request, model):
    # resolve the action
    if 'action' not in request.POST:
        return HttpResponseBadRequest('No action provided')
    action = request.POST['action']

    # resolve the objects
    new_querydict = extract_selected_ids(request.POST)

    # keep the return URL
    if 'from' in request.GET:
        new_querydict['from'] = request.GET['from']

    # redirect to the correct url
    return redirect(reverse_lazy('lims:bulk_action', args=(model, action)) + '?' + new_querydict.urlencode())


def item_action_view(request, model, pk, action):
    # resolve the objects
    new_querydict = QueryDict(mutable=True)
    new_querydict['id__in'] = pk

    # keep the return url
    if 'from' in request.GET:
        new_querydict['from'] = request.GET['from']

    # redirect to the correct url
    return redirect(reverse_lazy('lims:bulk_action', args=(model, action)) + '?' + new_querydict.urlencode())


def base_action_view(request, model, action):
    # check login
    if not request.user.pk:
        return HttpResponseBadRequest('Permission denied')

    # resolve the view
    action_view = find_action_view(model, action)

    # render the view
    return action_view.as_view()(request)


def extract_selected_ids(data):
    regex = re.compile(r'object-([0-9]+)-selected')
    ids = []
    for key, value in data.items():
        if regex.match(key) and value:
            ids.append(int(regex.search(key).group(1)))
    ids_query = QueryDict(mutable=True)
    ids_query.setlist('id__in', ids)
    return ids_query


class ActionListView(generic.ListView):
    success_url = reverse_lazy('lims:index')
    action_name = None
    model = None
    template_name = 'lims/action_views/action_list.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.errors = []
        self.messages = []

    def add_message(self, obj):
        self.messages.append(obj)

    def add_error(self, obj):
        self.errors.append(obj)

    def get_success_url(self):
        return self.request.GET.get('from', self.success_url)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['errors'] = self.errors
        context['action_name'] = self.action_name
        context['item_text'] = self.model.__name__.lower()
        return context

    def get_queryset(self):
        id_in = self.request.GET.getlist('id__in')
        queryset = self.model.objects.all().filter(id__in=id_in)
        if not queryset:
            raise Http404('Could not find any objects')
        if len(id_in) != queryset.count():
            raise Http404('Could not find all requested objects')
        return queryset


class BulkActionView(ActionListView):

    def post(self, request):
        try:
            result = self.do_action(request, self.get_queryset())
            if self.errors:
                return self.get(request)
            elif result is not None:
                return result
            else:
                return redirect(self.get_success_url())
        except Http404:
            return redirect(self.get_success_url())

    def do_action(self, request, queryset):
        raise NotImplementedError()


class MultiDeleteView(BulkActionView):
    action_name = 'delete'

    def do_action(self, request, queryset):
        current_user = request.user
        deleted = 0

        try:
            with reversion.create_revision():
                for obj in queryset:
                    if obj.user_can(current_user, 'delete'):
                        obj.delete()
                        deleted += 1
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

        self.add_message('%d items were successfully deleted' % deleted)


class SampleDeleteView(LimsLoginMixin, MultiDeleteView):
    model = models.Sample
    success_url = reverse_lazy('lims:sample_list')


class LocationDeleteView(LimsLoginMixin, MultiDeleteView):
    model = models.Location
    success_url = reverse_lazy('lims:location_list')


class SamplePrintBarcodeView(LimsLoginMixin, BulkActionView):
    model = models.Sample
    template_name = 'lims/action_views/sample_print_barcode.html'
    action_name = 'print barcodes'

    def do_action(self, request, queryset):
        self.add_error("Barcode printing isn't implemented yet...")


def export_response(queryset, fields, terms):

    target_tz = timezone.get_default_timezone()

    def header_iter():
        for field in fields:
            yield field
        for term in terms:
            yield term.slug

    def field_iter(instance):
        for field in fields:
            item = getattr(instance, field)
            if hasattr(item, 'strftime'):
                yield item.astimezone(target_tz).strftime('%Y-%m-%dT%H:%M%z')
            else:
                yield str(item)
        for term in terms:
            item = instance.get_tag(term)
            if item is None:
                yield 'NA'
            else:
                yield str(item)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename = "LIMS_export.csv"'
    writer = csv.writer(response)
    writer.writerow(header_iter())
    for obj in queryset:
        writer.writerow(field_iter(obj))
    return response


class SampleExportView(LimsLoginMixin, BulkActionView):
    model = models.Sample
    action_name = 'export'

    def do_action(self, request, queryset):
        return export_response(
            queryset,
            fields=['id', 'slug', 'user', 'name', 'description', 'collected', 'location'],
            terms=self.model.get_all_terms(queryset)
        )


class LocationExportView(LimsLoginMixin, BulkActionView):
    model = models.Location
    action_name = 'export'

    def do_action(self, request, queryset):
        return export_response(
            queryset,
            fields=['id', 'slug', 'user', 'name', 'description', 'parent', 'geometry'],
            terms=self.model.get_all_terms(queryset)
        )


class SamplePublishView(LimsLoginMixin, BulkActionView):
    model = models.Sample
    action_name = 'publish'

    def new_status(self):
        return True

    def do_action(self, request, queryset):
        current_user = request.user
        try:
            with reversion.create_revision():
                for obj in queryset:
                    if obj.user_can(current_user, 'edit'):
                        obj.published = self.new_status()
                        obj.save()
                    else:
                        raise models.ObjectPermissionError(obj)

        except models.ObjectPermissionError as e:
            self.add_error(
                format_html('You are not allowed to change the published status for sample <a href="{}">{}</a>.',
                            e.get_object().get_absolute_url(), e.get_object())
            )

        self.add_message('%s items were successfully %sed' % (queryset.count(), self.action_name))


class SampleUnPublishView(SamplePublishView):
    model = models.Sample
    action_name = 'unpublish'

    def new_status(self):
        return False


class SampleBulkEditForm(SampleForm):

    class Meta:
        fields = ['collected', 'name', 'description', 'location', 'parent', 'geometry']


class SampleBulkEditView(SampleBulkAddView, ActionListView):
    model = models.Sample
    template_name = 'lims/sample_bulk_change.html'

    def get_model_form_class(self):
        return SampleBulkEditForm

    def get_object_queryset(self):
        return self.get_queryset()

    def get_extra_forms(self):
        return 0


SAMPLE_ACTIONS = [
    {'value': 'delete', 'label': 'Delete samples', 'view': SampleDeleteView},
    {'value': 'print', 'label': 'Print barcodes', 'view': SamplePrintBarcodeView},
    {'value': 'export', 'label': 'Export selected samples', 'view': SampleExportView},
    {'value': 'publish', 'label': 'Publish selected samples', 'view': SamplePublishView},
    {'value': 'unpublish', 'label': 'Unpublish selected samples', 'view': SampleUnPublishView},
    {'value': 'bulkedit', 'label': 'Bulk Edit selected samples', 'view': SampleBulkEditView}
]

LOCATION_ACTIONS = [
    {'value': 'delete', 'label': 'Delete selected locations', 'view': LocationDeleteView},
    {'value': 'export', 'label': 'Export selected locations', 'view': LocationExportView}
]
