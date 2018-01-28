
import re

from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.http import QueryDict, HttpResponseBadRequest

LOCATION_ACTIONS = {
    'delete-locations': reverse_lazy('lims:location_delete')
}

SAMPLE_ACTIONS = {
    'delete-samples': reverse_lazy('lims:sample_delete'),
    'print-barcodes': reverse_lazy('lims:sample_print_barcode')
}


def location_action(request, pk=None, action=None):
    return do_action(request, pk, action, LOCATION_ACTIONS)


def sample_action(request, pk=None, action=None):
    return do_action(request, pk, action, SAMPLE_ACTIONS)


def do_action(request, pk, action, action_dict):

    if action and pk:
        ids_query = QueryDict('id__in=' + pk)
    else:
        post_vars = request.POST
        if not post_vars or 'action' not in post_vars:
            return HttpResponseBadRequest('No action provided')

        ids_query = extract_selected_ids(post_vars)
        action = post_vars['action']

    if action not in action_dict:
        return HttpResponseBadRequest('Unrecognized action: "%s"' % action)

    if 'from' in request.GET:
        ids_query['from'] = request.GET['from']

    action_url = action_dict[action]
    return redirect(action_url + '?' + ids_query.urlencode())


def extract_selected_ids(data):
    regex = re.compile(r'object-([0-9]+)-selected')
    ids = []
    for key, value in data.items():
        if regex.match(key) and value:
            ids.append(int(regex.search(key).group(1)))
    ids_query = QueryDict(mutable=True)
    ids_query.setlist('id__in', ids)
    return ids_query
