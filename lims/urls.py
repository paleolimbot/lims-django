
from django.conf.urls import url
from . import views

app_name = 'lims'
urlpatterns = [
    # the index page
    url(r'^$', views.IndexView.as_view(), name="index"),

    # login/account pages
    url(r'^account/$', views.AccountView.as_view(), name='account'),
    url(r'^login/$', views.LoginView.as_view(), name='login'),
    url(r'^logout/$', views.LogoutView.as_view(), name='logout'),
    url(r'^account/change_password/$', views.ChangePasswordView.as_view(), name='change_password'),

    # sample static views
    url(r'^sample/$', views.SampleListView.as_view(), name="sample_list"),
    url(r'^sample/add_bulk$', views.SampleBulkAddView.as_view(), name="sample_add_bulk"),
    url(r'^sample/add$', views.SampleAddView.as_view(), name="sample_add"),
    url(r'^sample/action$', views.sample_action, name="sample_action"),
    url(r'^sample/delete$', views.SampleDeleteView.as_view(), name='sample_delete'),
    url(r'^sample/print_barcode', views.SamplePrintBarcodeView.as_view(), name='sample_print_barcode'),

    # sample object views
    url(r'^sample/(?P<pk>[0-9]+)$', views.SampleDetailView.as_view(), name="sample_detail"),
    url(r'^sample/(?P<pk>[0-9]+)/change$', views.SampleChangeView.as_view(), name="sample_change"),
    url(r'^sample/(?P<pk>[0-9]+)/action/(?P<action>[a-z-]+)$', views.sample_action, name='sample_item_action'),

    # location static views
    url(r'^location/$', views.LocationListView.as_view(), name="location_list"),
    url(r'^location/add$', views.LocationAddView.as_view(), name="location_add"),
    url(r'^location/action$', views.location_action, name="location_action"),
    url(r'^location/delete$', views.LocationDeleteView.as_view(), name="location_delete"),

    # location object views
    url(r'^location/(?P<pk>[0-9]+)$', views.LocationDetailView.as_view(), name="location_detail"),
    url(r'^location/(?P<pk>[0-9]+)/change$', views.LocationChangeView.as_view(), name="location_change"),
    url(r'^location/(?P<pk>[0-9]+)/action/(?P<action>[a-z-]+)$', views.location_action, name='location_item_action'),

    # user object views
    url(r'^user/(?P<pk>[0-9]+)$', views.UserDetailView.as_view(), name="user_detail"),
]
