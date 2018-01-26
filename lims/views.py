
import re
import json

from django.shortcuts import redirect
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q
from django.db import transaction, IntegrityError
from django.forms import modelformset_factory, ModelForm, CharField, Textarea
from django.core.exceptions import ValidationError
from django.http.request import QueryDict
from django.http import Http404
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from django.utils.html import format_html

from . import models


class LimsLoginMixin(LoginRequiredMixin):
    login_url = '/admin/login/'


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
        queryset = self.get_queryset()
        errors = []

        try:
            with transaction.atomic():
                queryset.delete()
        except IntegrityError as e:
            if hasattr(e, 'protected_objects') and e.protected_objects:
                link_list = [format_html('<a href="{}">{}</a>', obj.get_absolute_url(), str(obj))
                             for obj in e.protected_objects[:10]]
                items_str = ', '.join(link_list)
                if len(e.protected_objects) > 10:
                    items_str += '...plus %d more objects' % (len(e.protected_objects) - 10)
                errors.append(mark_safe('Some items could not be deleted due to relationships with other objects. '
                                        'These objects may include the following: ' + items_str))
            else:
                errors.append('Some items could not be deleted: %s' % e)

        if errors:
            self.errors = errors
            return self.get(request)
        else:
            return redirect(self.get_success_url())


def index(request):
    return redirect(reverse_lazy('lims:sample_list'))


class SampleListView(LimsLoginMixin, generic.ListView):
    template_name = 'lims/sample_list.html'
    paginate_by = 50
    page_kwarg = 'sample_page'

    def get_context_data(self, *args, **kwargs):
        context = super(SampleListView, self).get_context_data(*args, **kwargs)
        context['actions'] = [
            {'value': 'delete-samples', 'label': 'Delete selected samples'}
        ]
        return context

    def get_queryset(self):
        return query_string_filter(
            models.Sample.objects.all(),
            self.request.GET,
            use=(),
            search=('name', 'slug'),
            prefix='sample_'
        ).order_by("-modified")


class SampleDetailView(LimsLoginMixin, generic.DetailView):
    template_name = 'lims/sample_detail.html'
    model = models.Sample


def validate_location_slug(value):
    if value:
        try:
            models.Location.objects.get(slug=value)
        except models.Location.DoesNotExist:
            raise ValidationError("Location with this ID does not exist")


def validate_json_tags_dict(value):
    if not value:
        return
    try:
        obj = json.loads(value)
        if not isinstance(obj, dict):
            raise ValidationError("Value is not a valid JSON object")

    except ValueError:
        raise ValidationError("Value is not valid JSON")


class SampleAddForm(ModelForm):
    location_slug = CharField(validators=[validate_location_slug, ], required=False)
    tag_json = CharField(
        validators=[validate_json_tags_dict, ],
        required=False,
        widget=Textarea(attrs={'rows': 2, 'cols': 40})
    )

    class Meta:
        model = models.Sample
        fields = ['collected', 'name', 'description', 'location_slug']

    def clean(self):
        super(SampleAddForm, self).clean()

        if not self.has_error('location_slug'):
            try:
                self.instance.location = models.Location.objects.get(
                    slug=self.cleaned_data['location_slug']
                )
            except models.Location.DoesNotExist:
                pass

    def save(self, *args, **kwargs):
        return_val = super(SampleAddForm, self).save(*args, **kwargs)

        # tags need the instance to exist in the DB before creating them...
        if self.cleaned_data['tag_json']:
            for key, value in json.loads(self.cleaned_data['tag_json']).items():
                object_tags_with_key = self.instance.tags.filter(key=key)
                if object_tags_with_key:
                    tag = object_tags_with_key[0]
                else:
                    tag = models.SampleTag(object=self.instance, key=key)
                tag.value = value if isinstance(value, str) else json.dumps(value)
                tag.save()

        return return_val


class SampleBulkAddView(LimsLoginMixin, generic.FormView):
    success_url = reverse_lazy('lims:sample_list')
    template_name = 'lims/sample_bulk_form.html'

    def get_form_class(self):
        n_samples = self.request.GET.get('n_samples', 10)
        try:
            n_samples = int(n_samples)
        except ValueError:
            n_samples = 10

        return modelformset_factory(
            models.Sample,
            form=SampleAddForm,
            extra=n_samples
        )

    def get_form_kwargs(self):
        kwargs = super(SampleBulkAddView, self).get_form_kwargs()
        kwargs["queryset"] = models.Sample.objects.none()
        return kwargs

    def form_valid(self, form):
        for sub_form in form:
            if sub_form.has_changed():
                sub_form.instance.user = self.request.user

        form.save()
        return super(SampleBulkAddView, self).form_valid(form)


class SampleAddView(LimsLoginMixin, generic.CreateView):
    success_url = reverse_lazy('lims:sample_list')
    template_name = 'lims/sample_form.html'
    form_class = SampleAddForm

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(SampleAddView, self).form_valid(form)


class SampleChangeView(LimsLoginMixin, generic.UpdateView):
    model = models.Sample
    template_name = 'lims/sample_change.html'
    form_class = SampleAddForm

    def get_form(self, form_class=None):
        form = super(SampleChangeView, self).get_form(form_class=form_class)
        if self.object.location:
            form.initial['location_slug'] = self.object.location.slug

        tag_dict = {tag.key: tag.value for tag in self.object.tags.all()}
        if tag_dict:
            form.initial['tag_json'] = json.dumps(tag_dict)

        return form


class SampleDeleteView(LimsLoginMixin, MultiDeleteView):
    model = models.Sample
    template_name = 'lims/sample_delete.html'
    success_url = reverse_lazy('lims:sample_list')


def sample_action(request, pk=None, action=None):

    if action and pk:
        ids_query = QueryDict('id__in=' + pk)
    else:
        post_vars = request.POST
        if not post_vars or 'action' not in post_vars:
            raise Http404('No action provided')

        ids_query = extract_selected_ids(post_vars, 'sample-([0-9]+)-selected')
        action = post_vars['action']

    if 'from' in request.GET:
        ids_query['from'] = request.GET['from']

    if action == 'delete-samples':
        return redirect(reverse_lazy('lims:sample_delete') + '?' + ids_query.urlencode())
    else:
        raise Http404('Unrecognized action: "%s"' % action)


class LocationListView(LimsLoginMixin, generic.ListView):
    template_name = 'lims/location_list.html'
    context_object_name = 'location_list'
    paginate_by = 50
    page_kwarg = 'location_page'

    def get_queryset(self):
        return query_string_filter(
            models.Location.objects.all(),
            self.request.GET,
            use=(),
            search=('name', 'slug'),
            prefix='location_'
        ).order_by("-modified")

    def get_context_data(self, *args, **kwargs):
        context = super(LocationListView, self).get_context_data(*args, **kwargs)
        context['actions'] = [
            {'value': 'delete-locations', 'label': 'Delete selected locations'}
        ]
        return context


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
            {'value': 'delete-samples', 'label': 'Delete selected samples'}
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


class LocationAddView(LimsLoginMixin, generic.CreateView):
    model = models.Location
    fields = ['name', 'slug', 'description', 'parent', 'geometry']
    success_url = reverse_lazy('lims:location_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(LocationAddView, self).form_valid(form)


class LocationChangeView(LimsLoginMixin, generic.UpdateView):
    model = models.Location
    template_name = 'lims/location_change.html'
    fields = ['name', 'slug', 'description', 'parent', 'geometry']


class LocationDeleteView(LimsLoginMixin, MultiDeleteView):
    model = models.Location
    template_name = 'lims/location_delete.html'
    success_url = reverse_lazy('lims:location_list')


def location_action(request, pk=None, action=None):

    if action and pk:
        ids_query = QueryDict('id__in=' + pk)
    else:
        post_vars = request.POST
        if not post_vars or 'action' not in post_vars:
            raise Http404('No action provided')

        ids_query = extract_selected_ids(post_vars, 'location-([0-9]+)-selected')
        action = post_vars['action']

    if 'from' in request.GET:
        ids_query['from'] = request.GET['from']

    if action == 'delete-locations':
        return redirect(reverse_lazy('lims:location_delete') + '?' + ids_query.urlencode())
    else:
        raise Http404('Unrecognized action: "%s"' % action)


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
            {'value': 'delete-samples', 'label': 'Delete selected samples'}
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


def extract_selected_ids(data, regex_str):
    regex = re.compile(regex_str)
    ids = []
    for key, value in data.items():
        if regex.match(key) and value:
            ids.append(int(regex.search(key)[1]))
    ids_query = QueryDict(mutable=True)
    ids_query.setlist('id__in', ids)
    return ids_query


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
