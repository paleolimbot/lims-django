
from .accounts import *
from .actions import *
from .edit import *
from .list import *
from .detail import *
from .ajax import *
from .data_view import *

from django.views import generic


class IndexView(LimsLoginMixin, generic.RedirectView):
    permanent = False
    query_string = False
    pattern_name = 'lims:project_list'
