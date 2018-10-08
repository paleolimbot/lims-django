
import django.forms as django_forms


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
        raise WidgetError('Could not find input widget: "%s"' % name)


def resolve_output_widget_class(name):
    try:
        return _output_widgets[name]
    except KeyError:
        raise WidgetError('Could not find output widget: "%s"' % name)


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


class OutputWidget(metaclass=django_forms.MediaDefiningClass):
    def render(self, value, context):
        raise NotImplementedError()


@register_output_widget
class EmptyOutput(OutputWidget):
    def render(self, value, context):
        return None


@register_output_widget
class IdentityOutput(OutputWidget):
    def render(self, value, context):
        return value
