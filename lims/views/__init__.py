
from .accounts import *
from .actions import *
from .edit import *
from .list import *
from .detail import *
from .templates import *

from django.views import generic


class IndexView(LimsLoginMixin, generic.RedirectView):
    permanent = False
    query_string = False
    pattern_name = 'lims:template_list'
