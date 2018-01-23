
import re
import json

from django.shortcuts import redirect
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q
from django.forms import modelformset_factory, widgets, ModelForm, CharField
from django.core.exceptions import ValidationError
from django.http.request import QueryDict
from django.core.paginator import Paginator
from django.contrib.auth.models import User

from . import models


class LimsLoginMixin(LoginRequiredMixin):
    login_url = '/admin/login/'


def index(request):
    return redirect(reverse_lazy('lims:sample_list'))


class SampleListView(LimsLoginMixin, generic.ListView):
    template_name = 'lims/sample_list.html'
    paginate_by = 100
    page_kwarg = 'sample_page'

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
    tag_json = CharField(validators=[validate_json_tags_dict, ], required=False)

    class Meta:
        model = models.Sample
        fields = ['collected', 'name', 'location_slug']
        widgets = {'location': widgets.TextInput()}

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
                str_value = value if isinstance(value, str) else json.dumps(value)
                tag = models.SampleTag(key=key, value=str_value, object=self.instance)
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


class LocationListView(LimsLoginMixin, generic.ListView):
    template_name = 'lims/location_list.html'
    context_object_name = 'location_list'
    paginate_by = 100
    page_kwarg = 'location_page'

    def get_queryset(self):
        return query_string_filter(
            models.Location.objects.all(),
            self.request.GET,
            use=(),
            search=('name', 'slug'),
            prefix='location_'
        ).order_by("-modified")


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

        # setup the child locations list
        locations = query_string_filter(
            context['location'].children.order_by('-modified'),
            self.request.GET,
            prefix='location_'
        )
        location_paginator = Paginator(locations, per_page=10)
        context['location_page_obj'] = location_paginator.page(self.request.GET.get('location_page', 1))
        context['location_page_kwarg'] = 'location_page'

        return context


class LocationAddView(LimsLoginMixin, generic.CreateView):
    model = models.Location
    fields = ['name', 'slug', 'parent', 'geometry']
    success_url = reverse_lazy('lims:location_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(LocationAddView, self).form_valid(form)


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

        # setup the child locations list
        locations = query_string_filter(
            context['user'].location_set.order_by('-modified'),
            self.request.GET,
            prefix='location_'
        )
        location_paginator = Paginator(locations, per_page=10)
        context['location_page_obj'] = location_paginator.page(self.request.GET.get('location_page', 1))
        context['location_page_kwarg'] = 'location_page'

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
