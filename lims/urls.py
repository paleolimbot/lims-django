
from django.conf.urls import url
from . import views

app_name = 'lims'
urlpatterns = [
    # the index page
    url(r'^$', views.index, name="index"),
    url(r'^sample/$', views.SampleListView.as_view(), name="sample_list"),
    url(r'^sample/add$', views.SampleAddView.as_view(), name="sample_add"),
    url(r'^sample/(?P<pk>[0-9]+)$', views.SampleDetailView.as_view(), name="sample_detail"),
    url(r'^location/$', views.LocationListView.as_view(), name="location_list"),
    url(r'^location/add$', views.LocationAddView.as_view(), name="location_add"),
    url(r'^location/(?P<pk>[0-9]+)$', views.LocationDetailView.as_view(), name="location_detail"),
    url(r'^user/(?P<pk>[0-9]+)$', views.UserDetailView.as_view(), name="user_detail"),
]

