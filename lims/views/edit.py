
import json

from django.views import generic
from django.urls import reverse_lazy
from django.forms import modelformset_factory, ModelForm, CharField, ValidationError, TextInput
import reversion

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
    location_field = None
    location_slug = CharField(validators=[validate_location_slug, ], required=False)

    def __init__(self, *args, user=None, tag_field_names=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # add additional tag names that may exist from the current instance
        current_tag_keys = self.instance.get_tags().keys()
        tag_field_names = list(tag_field_names)
        for key in current_tag_keys:
            tag_field_names.append(key)

        # add additional tag names that come from the form data
        if 'data' in kwargs:
            for key, value in kwargs['data'].items():
                if key.startswith('tag_form_field_'):
                    tag_field_names.append(key.replace('tag_form_field_', ''))

        # set the tag names from tag_field_names
        self.tag_field_names = {}
        for field_name in tag_field_names:
            term = models.Term.get_term(field_name)
            # don't duplicate tag fields
            if term.slug in self.tag_field_names:
                continue
            field_id = 'tag_form_field_' + term.slug
            self.tag_field_names[term.slug] = field_id
            self.fields[field_id] = CharField(required=False, label='Tag: ' + term.name)
            initial_val = self.instance.get_tag(term)
            if initial_val:
                self.initial[field_id] = initial_val

        # initial values must be set for location_slug
        initial_loc = getattr(self.instance, self.location_field)
        if initial_loc:
            self.initial['location_slug'] = initial_loc.slug

    def clean(self):
        if not hasattr(self, 'user') or not self.user.pk:
            raise ValidationError('Unknown user attempting to make changes')

        # check that user can add/edit this sample
        if not self.instance.pk and not self.instance.user_can(self.user, 'add'):
            raise ValidationError('User is not allowed to add this sample')
        if self.instance.pk and not self.instance.user_can(self.user, 'edit'):
            raise ValidationError('User is not allowed to edit this sample')

        # set the user, if there isn't one already
        if not self.instance.user:
            self.instance.user = self.user

        # clean the form
        super().clean()

        # check values of tags
        tag_value_errors = {}
        for term_name, field_name in self.tag_field_names.items():
            value = self.cleaned_data[field_name]
            if not value:
                continue

            # term will always exist, because it gets created before the value can be validated
            term = models.Term.get_term(term_name, create=True)
            errors_for_key = term.get_validation_errors(value)
            if errors_for_key:
                if field_name not in tag_value_errors:
                    tag_value_errors[field_name] = []
                for error in errors_for_key:
                    tag_value_errors[field_name].append(error)

        if tag_value_errors:
            raise ValidationError(tag_value_errors)

        # set location object
        if not self.has_error('location_slug'):
            try:
                setattr(self.instance, self.location_field, models.Location.objects.get(
                    slug=self.cleaned_data['location_slug']
                ))
            except models.Location.DoesNotExist:
                pass

    def save(self, *args, **kwargs):
        # save the instance
        return_val = super().save(*args, **kwargs)

        # tags need the instance to exist in the DB before creating them...
        tags_dict = {term: self.cleaned_data[field] for term, field in self.tag_field_names.items()}

        # remove empty values from the dict (these keys get removed)
        for key in list(tags_dict.keys()):
            if tags_dict[key] == '':
                del tags_dict[key]

        # update the tag information
        self.instance.set_tags(**tags_dict)

        # return whatever the super() returned
        return return_val


class SampleForm(BaseObjectModelForm):
    location_field = 'location'

    class Meta:
        model = models.Sample
        fields = ['collected', 'name', 'description', 'location_slug']


class SampleBulkAddForm(SampleForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget = TextInput()


class LocationForm(BaseObjectModelForm):
    location_field = 'parent'

    class Meta:
        model = models.Location
        fields = ['name', 'slug', 'description', 'location_slug', 'geometry']


class BaseObjectAddView(generic.CreateView):

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['tag_field_names'] = self.request.GET.getlist('_use_tag_field', default=[])
        return kwargs

    def form_valid(self, form):
        # wrap the saving of the object in a revision block
        with reversion.create_revision():
            # do the saving
            return_value = super().form_valid(form)

            # add information about from whence it came
            reversion.set_user(self.request.user)
            reversion.set_comment('object change from BaseObjectAddView')

            # return the response
            return return_value


class BaseObjectChangeView(generic.UpdateView):

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['tag_field_names'] = self.request.GET.getlist('_use_tag_field', [])
        return kwargs

    def form_valid(self, form):
        # wrap the saving of the object in a revision block
        with reversion.create_revision():
            # do the saving
            return_value = super().form_valid(form)

            # add information about from whence it came
            reversion.set_user(self.request.user)
            reversion.set_comment('object change from BaseObjectChangeView')

            # return the response
            return return_value


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
        with reversion.create_revision():
            form.save()

            # add information about from whence it came
            reversion.set_user(self.request.user)
            reversion.set_comment('bulk object creation from SampleBulkAddView')

        return super(SampleBulkAddView, self).form_valid(form)
