
import re

from django.views import generic
from django.http import HttpResponse, HttpResponseForbidden, Http404

from .. import models
from ..widgets.widgets import WidgetError
from ..widgets import data_widget

_data_widgets = {}


def register_data_widget(data_widget_class, name=None):
    global _data_widgets
    if name is None:
        name = data_widget_class.__name__
    try:
        if not callable(data_widget_class.bind):
            raise WidgetError("Widget's 'bind' attribute is not callable")
    except AttributeError:
        raise WidgetError("Widget does not have a 'bind' attribute")

    _data_widgets[name] = data_widget_class
    return data_widget_class


def unregister_data_widget(data_widget_class):
    global _data_widgets

    for name in list(_data_widgets.keys()):
        dw = data_widget_class[name]
        if name == data_widget_class or dw == data_widget_class:
            del _data_widgets[name]
            return dw

    return None


for item in ['AttachmentDataWidget', 'ProjectDataWidget', 'SampleDataWidget', 'TagDataWidget', 'TermDataWidget']:
    register_data_widget(getattr(data_widget, item), re.sub(r'DataWidget$', '', item))


class DataWidgetView(generic.View):

    def dispatch(self, request, model=None, data_widget=None, output_type='html', scope='widget', **kwargs):
        if not request.user.pk:
            return HttpResponseForbidden()
        bound_dw = self.bound_data_widget(request, model, data_widget, output_type)
        try:
            return HttpResponse(getattr(bound_dw, 'as_' + scope)())
        except (AttributeError, TypeError):
            raise Http404("Cannot find scope '%s'" % scope)

    def get_queryset(self, model):
        model_class = models.LimsModelField.get_model(model)
        if model_class is None:
            raise Http404("Cannot find model '%s'" % model)
        return model_class.objects.all()

    def data_widget(self, data_widget, **kwargs):
        if data_widget is None or data_widget not in _data_widgets:
            raise Http404("Cannot find data widget '%s'" % data_widget)
        return _data_widgets[data_widget](**kwargs)

    def bound_data_widget(self, request, model, data_widget, output_type='html', **kwargs):
        return self.data_widget(data_widget).bind(
            request,
            self.get_queryset(model),
            output_type,
            **kwargs
        )
