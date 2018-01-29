
import json

from django.views import generic
from django.urls import reverse_lazy
from django.forms import modelformset_factory, ModelForm, CharField, Textarea, ValidationError, TextInput

from .. import models
from .accounts import LimsLoginMixin


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


class BaseObjectModelForm(ModelForm):
    TagClass = None
    location_field = None

    location_slug = CharField(validators=[validate_location_slug, ], required=False)
    tag_json = CharField(
        validators=[validate_json_tags_dict, ],
        required=False,
        widget=Textarea(attrs={'rows': 2, 'cols': 40})
    )

    def clean(self):
        if not hasattr(self, 'user') or not self.user.pk:
            raise ValidationError('Unknown user attempting to make changes')

        # check that user can add/edit this sample
        if not self.instance.pk and not self.instance.user_can(self.user, 'add'):
            raise ValidationError('User is not allowed to add this sample')
        if self.instance.pk and not self.instance.user_can(self.user, 'edit'):
            raise ValidationError('User is not allowed to edit this sample')

        # set the user
        self.instance.user = self.user

        # clean the form
        super().clean()

        # check values of tags
        # tags need the instance to exist in the DB before creating them...
        if self.cleaned_data['tag_json']:
            tags_dict = json.loads(self.cleaned_data['tag_json'])
        else:
            tags_dict = {}

        tag_value_errors = []
        for key, value in tags_dict.items():
            try:
                term = models.Term.get_or_create(key)
                errors_for_key = term.get_validation_errors(value)
                for error in errors_for_key:
                    tag_value_errors.append('Error for key "%s": %s' % (key, error))

            except models.Term.DoesNotExist:
                # if there is no term, there is no invalid value
                pass

        if tag_value_errors:
            raise ValidationError({'tag_json': tag_value_errors})

        # set location object
        if not self.has_error('location_slug'):
            try:
                setattr(self.instance, self.location_field, models.Location.objects.get(
                    slug=self.cleaned_data['location_slug']
                ))
            except models.Location.DoesNotExist:
                pass

    def save(self, *args, **kwargs):
        return_val = super().save(*args, **kwargs)

        # tags need the instance to exist in the DB before creating them...
        if self.cleaned_data['tag_json']:
            tags_dict = json.loads(self.cleaned_data['tag_json'])
        else:
            tags_dict = {}

        self.instance.set_tags(**tags_dict)

        return return_val


class SampleForm(BaseObjectModelForm):
    TagClass = models.SampleTag
    location_field = 'location'

    class Meta:
        model = models.Sample
        fields = ['collected', 'name', 'description', 'location_slug', 'tag_json']


class SampleBulkAddForm(SampleForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget = TextInput()


class LocationForm(BaseObjectModelForm):
    TagClass = models.LocationTag
    location_field = 'parent'

    class Meta:
        model = models.Location
        fields = ['name', 'slug', 'description', 'location_slug', 'geometry', 'tag_json']


class BaseObjectAddView(generic.CreateView):

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.user = self.request.user
        return form


class BaseObjectChangeView(generic.UpdateView):

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        form.user = self.request.user

        loc = getattr(self.object, form.location_field)

        if loc:
            form.initial['location_slug'] = loc.slug

        tag_dict = self.object.get_tags()
        if tag_dict:
            form.initial['tag_json'] = json.dumps(tag_dict)

        return form


class SampleAddView(LimsLoginMixin, BaseObjectAddView):
    template_name = 'lims/sample_form.html'
    form_class = SampleForm


class SampleChangeView(LimsLoginMixin, BaseObjectChangeView):
    model = models.Sample
    template_name = 'lims/sample_change.html'
    form_class = SampleForm


class LocationAddView(LimsLoginMixin, BaseObjectAddView):
    template_name = 'lims/location_form.html'
    form_class = LocationForm


class LocationChangeView(LimsLoginMixin, BaseObjectChangeView):
    model = models.Location
    template_name = 'lims/location_change.html'
    form_class = LocationForm


class SampleBulkAddView(LimsLoginMixin, generic.FormView):
    success_url = reverse_lazy('lims:sample_list')
    template_name = 'lims/sample_bulk_form.html'

    def get_form_class(self):
        n_samples = self.request.GET.get('n_samples', 5)
        try:
            n_samples = int(n_samples)
        except ValueError:
            n_samples = 5

        return modelformset_factory(
            models.Sample,
            form=SampleBulkAddForm,
            extra=n_samples
        )

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        formset = form_class(**self.get_form_kwargs())

        for form in formset:
            form.user = self.request.user
        return formset

    def get_form_kwargs(self):
        kwargs = super(SampleBulkAddView, self).get_form_kwargs()
        kwargs["queryset"] = models.Sample.objects.none()
        return kwargs

    def form_valid(self, form):
        form.save()
        return super(SampleBulkAddView, self).form_valid(form)
