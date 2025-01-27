
import re

from django.shortcuts import get_object_or_404
from django.forms import modelformset_factory,\
    ModelForm, ValidationError, TextInput, BaseModelFormSet, Textarea, HiddenInput, CharField
from django.views import generic
import reversion
from django_select2.forms import ModelSelect2Widget

from .. import models


class ProjectModelSelect2Widget(ModelSelect2Widget):
    search_fields = [
        'name__icontains',
        'slug__icontains'
    ]

    def filter_queryset(self, term, queryset=None, **dependent_fields):
        qs = super().filter_queryset(term, queryset, **dependent_fields)
        return qs


class SampleSelect2Widget(ProjectModelSelect2Widget):
    def get_queryset(self):
        return models.Sample.objects.order_by('-modified').filter(status='published')


class TermSelect2Widget(ProjectModelSelect2Widget):
    def get_queryset(self):
        return models.Term.objects.order_by('name')


class DateTimePicker(TextInput):

    class Media:
        css = {
            'all': ('lims/css/jquery.datetimepicker.min.css', )
        }
        js = ('lims/js/jquery.datetimepicker.full.min.js', 'lims/js/jquery.datetimepicker.widget.js')

    def __init__(self, *args, **kwargs):
        if 'attrs' not in kwargs:
            kwargs['attrs'] = {}
        if 'class' not in kwargs['attrs']:
            kwargs['attrs']['class'] = 'jquery-datetimepicker-widget'
        else:
            kwargs['attrs']['class'] = kwargs['attrs']['class'] + ' jquery-datetimepicker-widget'

        super().__init__(*args, **kwargs)


class ObjectFormView(generic.FormView):

    def get_project(self):
        if 'project_id' in self.kwargs:
            return get_object_or_404(models.Project, pk=self.kwargs['project_id'])
        else:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.get_project()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['project'] = self.get_project()

        # get tag fields from the add tag column item
        tag_field_names = list(self.request.POST.get('add-form-tag-column', default='').split(','))
        for name in self.request.GET.getlist('_use_tag_field', default=[]):
            tag_field_names.append(name)

        # don't pass on '' items
        kwargs['tag_field_names'] = [name for name in tag_field_names if name]

        return kwargs

    def form_valid(self, form):
        # if the user requested additional tag columns but all the models were valid,
        # the user should probably stay on this page
        if self.request.POST.get('add-form-tag-column', None):
            return self.form_invalid(form)

        # wrap the saving of the object in a revision block
        with reversion.create_revision():
            # do the saving
            return_value = super().form_valid(form)

            # add information about from whence it came
            reversion.set_user(self.request.user)
            reversion.set_comment('object change from ObjectFormView')

            # return the response
            return return_value


class BaseObjectModelForm(ModelForm):
    project_meta_field = CharField(widget=HiddenInput(), required=True)

    def __init__(self, *args, user=None, project=None, tag_field_names=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.project = project
        self.fields['project_meta_field'].initial = project.pk

        # add additional tag names that may exist from the current instance
        current_tag_keys = self.instance.get_tags().keys()
        tag_field_names = list(tag_field_names)
        for key in current_tag_keys:
            tag_field_names.append(key)

        # add additional terms that exist in the form data
        for key in self.data:
            if re.match('^tag_form_field_(.*)$', key):
                tag_field_names.append(re.search('^tag_form_field_(.*)$', key).group(1))

        # set the tag names from tag_field_names
        # currently only the model taxonomy can be used
        self.tag_field_names = {}
        for field_name in tag_field_names:
            # try to resolve term
            term = models.Term.get_term(
                field_name,
                create=True,
                project=self.project,
                taxonomy=self._meta.model.__name__
            )

            # if term can't be resolved, don't add it to the form
            # (most likely reason is that field_name is '')
            if term is None:
                continue

            # don't duplicate tag fields
            if term in self.tag_field_names:
                continue

            # add the field
            field_id = 'tag_form_field_' + term.slug
            self.tag_field_names[term] = field_id
            self.fields[field_id] = term.field
            initial_val = self.instance.get_tag(term)
            if initial_val:
                self.initial[field_id] = initial_val

        # make sure dependencies are added to the Select2Widget
        for field in self.fields.values():
            if isinstance(field.widget, ProjectModelSelect2Widget):
                field.widget.dependent_fields = {'project_meta_field': 'project'}

    def clean(self):
        if not hasattr(self, 'user') or not self.user.pk:
            raise ValidationError('Unknown user attempting to make changes')

        # set the project, user if there isn't one already
        if not hasattr(self.instance, "project"):
            self.instance.project = self.project
        elif not self.instance.project:
            self.instance.project = self.project

        if not hasattr(self.instance, "user"):
            self.instance.user = self.user
        elif not self.instance.user:
            self.instance.user = self.user

        # clean the form
        super().clean()

        # check that user can add/edit this sample
        if not self.instance.pk and not self.instance.user_can(self.user, 'edit'):
            raise ValidationError('User is not allowed to add this sample')
        if self.instance.pk and not self.instance.user_can(self.user, 'edit'):
            raise ValidationError('User is not allowed to edit this sample')

    def save(self, *args, **kwargs):
        # save the instance
        return_val = super().save(*args, **kwargs)

        # tags need the instance to exist in the DB before creating them...
        tags_dict = {term: self.cleaned_data[field] for term, field in self.tag_field_names.items()}

        # update the tag information
        # TODO: this could result in a ValidationError() from the full_clean() of
        # tag objects
        self.instance.update_tags(_values=tags_dict)

        # return whatever the super() returned
        return return_val


class BulkAddFormset(BaseModelFormSet):

    def __init__(self, *args, user=None, project=None, tag_field_names=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.project = project
        self.tag_field_names = list(tag_field_names)

        # add additional terms that exist in the queryset
        for term in self.model.get_all_terms(self.queryset):
            self.tag_field_names.append(term.slug)

        # add additional terms that exist in the form data
        for key in self.data:
            if re.match('^form-[0-9]+-tag_form_field_(.*)$', key):
                self.tag_field_names.append(re.search('^form-[0-9]+-tag_form_field_(.*)$', key).group(1))

    @property
    def media(self):
        media = super().media
        media._js.append('lims/js/bulk_form.js')
        return media

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['user'] = self.user
        kwargs['project'] = self.project
        kwargs['tag_field_names'] = self.tag_field_names
        return kwargs


class BulkEditViewBase(ObjectFormView):
    template_name = 'lims/forms/sample_bulk_form.html'
    model = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_list = []

    def get_model_form_class(self):
        raise NotImplementedError()

    def get_model_formset_class(self):
        return BulkAddFormset

    def get_extra_forms(self):
        n_samples = self.request.GET.get('n_samples', 5)
        try:
            return int(n_samples)
        except ValueError:
            return 5

    def get_form_class(self):
        return modelformset_factory(
            self.model,
            form=self.get_model_form_class(),
            formset=self.get_model_formset_class(),
            extra=self.get_extra_forms()
        )

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        formset = form_class(**self.get_form_kwargs())

        for form in formset:
            form.user = self.request.user
            for field in form.fields:
                current_widget = form.fields[field].widget
                if isinstance(current_widget, Textarea):
                    form.fields[field].widget = TextInput()

        return formset

    def get_object_queryset(self):
        return self.model.objects.none()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['queryset'] = self.get_object_queryset()
        return kwargs

    def form_valid(self, form):
        # completely empty forms are valid, but the user should probably stay on this page
        if not [sub_form for sub_form in form if sub_form.has_changed()]:
            return self.form_invalid(form)

        # if the user requested additional tag columns but all the models were valid,
        # the user should probably stay on this page
        if self.request.POST.get('add-form-tag-column', None):
            return self.form_invalid(form)

        with reversion.create_revision():
            form.save()
            return_value = super().form_valid(form)

            # add information about from whence it came
            reversion.set_user(self.request.user)
            reversion.set_comment('bulk object creation from SampleBulkAddView')

            return return_value
