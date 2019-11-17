
import re

from django.shortcuts import get_object_or_404
from django.views import generic
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.utils.functional import cached_property

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

    def bound_data_widget(self, *args, **kwargs):
        return DataWidgetView.bound_data_widget(*args, view=self, **kwargs)

    @staticmethod
    def get_queryset(model):
        model_class = models.LimsModelField.get_model(model)
        if model_class is None:
            raise Http404("Cannot find model '%s'" % model)
        return model_class.objects.all()

    @staticmethod
    def data_widget(data_widget, **kwargs):
        if data_widget is None or data_widget not in _data_widgets:
            raise Http404("Cannot find data widget '%s'" % data_widget)
        kwargs.update({'name': data_widget})
        return _data_widgets[data_widget](**kwargs)

    @staticmethod
    def static_bound_data_widget(request, model, data_widget, output_type='html', view=None, **kwargs):
        dw = DataWidgetView.data_widget(data_widget)
        project_id = kwargs.pop('project_id') if 'project_id' in kwargs else \
            request.GET.get(dw.name + '_project_id', None)

        context = kwargs.pop('context', {})
        if 'view' not in context and view is not None:
            context['view'] = view

        if project_id is not None and 'project' not in context:
            context['project'] = get_object_or_404(models.Project, pk=project_id)

        return dw.bind(
            DataWidgetView.get_queryset(model),
            request,
            output_type,
            project_id=project_id,
            context=context,
            **kwargs
        )


class LazyDataWidget:

    def __init__(self, request, model, data_widget, output_type='html', **kwargs):
        self.request = request
        self.model = model
        self.data_widget = data_widget
        self.output_type = output_type
        self.kwargs = kwargs

    @cached_property
    def bound_widget(self):
        return DataWidgetView.static_bound_data_widget(
            request=self.request,
            model=self.model,
            data_widget=self.data_widget,
            output_type=self.output_type,
            **self.kwargs
        )

    def __str__(self):
        return self.bound_widget.as_widget()
