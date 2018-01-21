
from django.shortcuts import redirect
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q
from django.forms import modelformset_factory, widgets, ModelForm, CharField
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from . import models


class LimsLoginMixin(LoginRequiredMixin):
    login_url = '/admin/login/'


def index(request):
    return redirect(reverse_lazy('lims:sample_list'))


class SampleListView(LimsLoginMixin, generic.ListView):
    template_name = 'lims/sample_list.html'
    paginate_by = 100

    def get_queryset(self):
        return query_string_filter(
            models.Sample.objects.all(),
            self.request.GET,
            use=(),
            search=('name', 'slug')
        ).order_by("-modified")


class SampleDetailView(LimsLoginMixin, generic.DetailView):
    template_name = 'lims/sample_detail.html'
    model = models.Sample


def validate_location_slug(value):
    if value:
        try:
            models.Location.objects.get(slug=value)
        except models.Location.DoesNotExist:
            raise ValidationError("Location '%s' does not exist" % value)


class SampleAddForm(ModelForm):
    location_slug = CharField(validators=[validate_location_slug, ], required=False)

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


class SampleAddView(LimsLoginMixin, generic.FormView):
    success_url = reverse_lazy('lims:sample_list')
    template_name = 'lims/sample_form.html'

    def get_form_class(self):
        return modelformset_factory(
            models.Sample,
            form=SampleAddForm,
            extra=3
        )

    def get_form_kwargs(self):
        kwargs = super(SampleAddView, self).get_form_kwargs()
        kwargs["queryset"] = models.Sample.objects.none()
        return kwargs

    def form_valid(self, form):
        for sub_form in form:
            if sub_form.has_changed():
                sub_form.instance.user = self.request.user

        form.save()
        return super(SampleAddView, self).form_valid(form)


class LocationListView(LimsLoginMixin, generic.ListView):
    template_name = 'lims/location_list.html'
    context_object_name = 'location_list'
    paginate_by = 100

    def get_queryset(self):
        return query_string_filter(
            models.Location.objects.all(),
            self.request.GET,
            use=(),
            search=('name', 'slug')
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


def query_string_filter(queryset, q, use=(), search=(), search_func="icontains"):

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
