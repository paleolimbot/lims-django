
from django.shortcuts import redirect
from django.urls import reverse_lazy

from .accounts import *
from .actions import *
from .delete import *
from .edit import *
from .list import *
from .detail import *


def index(request):
    return redirect(reverse_lazy('lims:sample_list'))
