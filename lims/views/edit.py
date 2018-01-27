
import json

from django.views import generic
from django.urls import reverse_lazy
from django.forms import modelformset_factory, ModelForm, CharField, Textarea, ValidationError

from .. import models
from .accounts import LimsLoginMixin


class UserAwareForm(ModelForm):

    def clean(self):
        # check that user can add/edit this sample
        if not self.instance.pk and not self.instance.user_can(self.user, 'add'):
            raise ValidationError('User is not allowed to add this sample')
        if self.instance.pk and not self.instance.user_can(self.user, 'edit'):
            raise ValidationError('User is not allowed to edit this sample')

        self.instance.user = self.user
        super().clean()


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


class SampleAddForm(UserAwareForm):
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
    template_name = 'lims/sample_form.html'
    form_class = SampleAddForm

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.user = self.request.user
        return form


class SampleChangeView(LimsLoginMixin, generic.UpdateView):
    model = models.Sample
    template_name = 'lims/sample_change.html'
    form_class = SampleAddForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        form.user = self.request.user

        if self.object.location:
            form.initial['location_slug'] = self.object.location.slug

        tag_dict = {tag.key: tag.value for tag in self.object.tags.all()}
        if tag_dict:
            form.initial['tag_json'] = json.dumps(tag_dict)

        return form


class LocationForm(UserAwareForm):

    class Meta:
        model = models.Location
        fields = ['name', 'slug', 'description', 'parent', 'geometry']


class LocationAddView(LimsLoginMixin, generic.CreateView):
    model = models.Location
    form_class = LocationForm

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.user = self.request.user
        return form


class LocationChangeView(LimsLoginMixin, generic.UpdateView):
    model = models.Location
    template_name = 'lims/location_change.html'
    fields = ['name', 'slug', 'description', 'parent', 'geometry']
