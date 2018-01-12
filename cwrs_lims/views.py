
from django.shortcuts import redirect
from django.urls import reverse_lazy


def index(request):
    return redirect(reverse_lazy('lims:index'))
