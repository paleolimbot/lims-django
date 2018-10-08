
import json

from django.views import generic
import django.forms as forms
from django.http import HttpResponse, HttpResponseForbidden, QueryDict

from .. import widgets
from .. import models
from .list import query_string_filter


class AjaxBaseView(generic.View):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.pk:
            return HttpResponseForbidden()
        return HttpResponse(
            content=json.dumps(self.request_data(request, *args, **kwargs)),
            content_type='application/json'
        )

    def request_data(self, request, *args, **kwargs):
        raise NotImplementedError()

    def error_data(self, message):
        return {'error': message}


class LimsSelect2Ajax(AjaxBaseView):

    def request_data(self, request, *args, **kwargs):
        model_name = kwargs['model_name']
        model = models.LimsModelField.get_model(model_name)

        # filter for permissions
        queryset = models.queryset_for_user(model, request.user, 'view')

        # filter for query, which is named differently for use with query_string_filter()
        query_dict = request.GET.copy()
        q = request.GET.get('term', '')
        if q:
            query_dict['q'] = query_dict['term']
        if 'term' in query_dict:
            del query_dict['term']

        # filter using querystring (which fields to use depends on the model)
        use_fields = []
        search_fields = []

        # all models except project don't make sense without a project context
        if model_name != 'Project':
            if not query_dict.get('project', ''):
                return self.error_data('Please select a project')
            use_fields.append('project')

        # terms don't make sense in this widget without a taxonomy
        if model_name == 'Term':
            if not query_dict.get('taxonomy', ''):
                return self.error_data('Please select a taxonomy')
            use_fields.append('taxonomy')

        if issubclass(model, models.Tag):
            search_fields = search_fields + ['object__name', 'object__slug']
        elif issubclass(model, models.BaseObjectModel):
            search_fields = search_fields + ['name', 'slug']

        queryset = query_string_filter(
            queryset, query_dict,
            search=search_fields,
            use=use_fields
        )

        # I can't think of any situation in which an unpublished object should end up in a search for a select2
        queryset = queryset.filter(status='published')

        # currently limiting to 100 could paginate here?
        # should also probably order_by(), probably by '-modified'

        return {
            'err': 'nil',
            'results': [{'id': obj.pk, 'text': str(obj)} for obj in queryset[:100]]
        }

    def error_data(self, message):
        return {
            'err': message
        }


class TestForm(forms.Form):
    project = forms.CharField(widget=widgets.LimsSelect2('Project'))
    taxonomy = forms.CharField(initial='Sample')
    select_term = forms.CharField(widget=widgets.LimsSelect2('Term'))
    select_sample = forms.CharField(widget=widgets.LimsSelect2('Sample'))


class AjaxTest(generic.FormView):
    form_class = TestForm
    template_name = 'lims/ajax_test.html'
