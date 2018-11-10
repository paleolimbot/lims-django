
import django.forms as django_forms
from django.urls import reverse_lazy
from django.utils.html import format_html

from django_select2.forms import HeavySelect2Widget


class WidgetError(Exception):
    pass


_input_widgets = {}
_output_widgets = {}


def register_input_widget(widget_class, name=None):
    global _input_widgets
    if name is None:
        name = widget_class.__name__
    try:
        if not callable(widget_class.render):
            raise WidgetError("Widget's render attribute is not callable")
    except AttributeError:
        raise WidgetError('Widget does not have a render attribute')

    _input_widgets[name] = widget_class
    return widget_class


def register_output_widget(widget_class, name=None):
    global _output_widgets
    if name is None:
        name = widget_class.__name__
    try:
        if not callable(widget_class.render):
            raise WidgetError("Widget's render attribute is not callable")
    except AttributeError:
        raise WidgetError('Widget does not have a render attribute')

    _output_widgets[name] = widget_class
    return widget_class


def resolve_input_widget_class(name):
    try:
        return _input_widgets[name]
    except KeyError:
        raise WidgetError('Input widget class must be one of %s' % ', '.join(str(x) for x in _input_widgets.keys()))


def resolve_output_widget_class(name):
    try:
        return _output_widgets[name]
    except KeyError:
        raise WidgetError('Output widget class must be one of %s' % ', '.join(str(x) for x in _output_widgets.keys()))


def resolve_input_widget(name, **kwargs):
    try:
        return resolve_input_widget_class(name)(**kwargs)
    except Exception as e:
        raise WidgetError('Could not instantiate input widget: %s' % e)


def resolve_output_widget(name, **kwargs):
    try:
        return resolve_output_widget_class(name)(**kwargs)
    except Exception as e:
        raise WidgetError('Could not instantiate output widget: %s' % e)


# -------------- Register built-in input widgets ---------------


register_input_widget(django_forms.CheckboxInput)
register_input_widget(django_forms.DateInput)
register_input_widget(django_forms.DateTimeInput)
register_input_widget(django_forms.EmailInput)
register_input_widget(django_forms.HiddenInput)
register_input_widget(django_forms.NullBooleanSelect)
register_input_widget(django_forms.PasswordInput)
register_input_widget(django_forms.RadioSelect)
register_input_widget(django_forms.Select)
register_input_widget(django_forms.SelectDateWidget)
register_input_widget(django_forms.SelectMultiple)
register_input_widget(django_forms.SplitDateTimeWidget)
register_input_widget(django_forms.TextInput)
register_input_widget(django_forms.Textarea)
register_input_widget(django_forms.TimeInput)


# ----------------- Create custom widgets --------------------

# this makes no sense for a tag but would be great for model forms
@register_input_widget
class LimsSelect2(HeavySelect2Widget):

    def __init__(self, model_name='Term', attrs=None, **kwargs):
        self.model_name = model_name
        # having these be form fields that don't exist doesn't appear to cause problems
        default_dependent_fields = {'project': 'project', 'taxonomy': 'taxonomy'}
        dependent_fields = kwargs.pop('dependent_fields', {})
        default_dependent_fields.update(**dependent_fields)
        defaults = {
            # can't call reverse_lazy until runtime
            'data_url': 'not_a_url_but_cant_be_none',
            'dependent_fields': default_dependent_fields
        }
        defaults.update(**kwargs)
        super().__init__(attrs=attrs, **defaults)

    def get_url(self):
        return reverse_lazy('lims:ajax_select2', kwargs={'model_name': self.model_name})


# ------------- Register output widgets --------------------


class OutputWidget(metaclass=django_forms.MediaDefiningClass):
    def render(self, instance, context=None):
        raise NotImplementedError()


@register_output_widget
class EmptyOutput(OutputWidget):
    def render(self, instance, context=None):
        return None


@register_output_widget
class IdentityOutput(OutputWidget):
    def render(self, instance, context=None):
        return instance if instance else ''
