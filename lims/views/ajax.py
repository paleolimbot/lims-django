
import json

from django.views import generic
from django.http import HttpResponse, HttpResponseForbidden

from .. import models
from lims.widgets.data_widget import query_string_filter


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
        if model_name not in ('Project', 'ProjectTag'):
            if not query_dict.get('project', ''):
                return self.error_data('Please select a project')

        # terms need a taxonomy
        if model_name in ('Term', 'TermTag'):
            if not query_dict.get('taxonomy', ''):
                return self.error_data('Please select a taxonomy')

        if model_name == 'Project':
            query_dict['status'] = 'published'

            use_fields = ['status']
            search_fields = ['name', 'slug']

        elif model_name in ('Sample', 'Attachment'):
            query_dict['status'] = 'published'

            use_fields = ['project', 'status']
            search_fields = ['name', 'slug']

        elif model_name == 'Term':
            query_dict['status'] = 'published'

            use_fields = ['project', 'taxonomy', 'status']
            search_fields = ['name', 'slug']

        elif model_name in ('SampleTag', 'AttachmentTag', 'TermTag'):
            query_dict['object__project'] = query_dict['project']
            del query_dict['project']
            query_dict['object__status'] = 'published'

            use_fields = ['object__project', 'object__status']
            search_fields = ['object__name', 'object__slug', 'key__name', 'key__slug']

        elif model_name == 'ProjectTag':
            query_dict['object__status'] = 'published'

            use_fields = ['object__status']
            search_fields = ['object__name', 'object__slug', 'key__name', 'key__slug']

        elif model_name == 'SampleTagTag':
            query_dict['object__object__project'] = query_dict['project']
            del query_dict['project']
            query_dict['object__object__status'] = 'published'

            use_fields = ['object__object__project']
            search_fields = ['object__object__name', 'object__object__slug', 'key__name', 'key__slug']
        else:
            return self.error_data("Don't know how to filter for model '%s'" % model_name)

        queryset = query_string_filter(
            queryset,
            query_dict,
            search=search_fields,
            use=use_fields
        )

        # currently limiting to 100 could paginate here?
        # should also probably order_by(), probably by '-modified'

        return {
            'err': 'nil',
            'results': [{'id': obj.pk, 'text': str(obj)} for obj in queryset[:10]]
        }

    def error_data(self, message):
        # not sure how to get this error message to show up on the widget
        return {
            'err': message
        }
