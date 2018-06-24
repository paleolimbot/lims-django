
from django.conf.urls import url, include
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

    # project views
    url(r'^project/$', views.ProjectListView.as_view(), name="project_list"),
    url(r'^project/(?P<pk>[0-9]+)$', views.ProjectDetailView.as_view(), name="project_detail"),

    # sample static views
    url(r'^sample/$', views.SampleListView.as_view(), name="sample_list"),
    url(r'^project/(?P<project_id>[0-9]+)/sample/$', views.SampleListView.as_view(), name="project_sample_list"),
    url(r'^sample/my$', views.MySampleListView.as_view(), name="my_sample_list"),
    url(r'^project/(?P<project_id>[0-9]+)/sample/my$', views.MySampleListView.as_view(), name="project_my_sample_list"),
    url(r'^project/(?P<project_id>[0-9]+)/sample/add_bulk$', views.SampleBulkAddView.as_view(), name="sample_add_bulk"),
    url(r'^project/(?P<project_id>[0-9]+)/sample/add$', views.SampleAddView.as_view(), name="sample_add"),

    # sample object views
    url(r'^sample/(?P<pk>[0-9]+)$', views.SampleDetailView.as_view(), name="sample_detail"),
    url(r'^sample/(?P<pk>[0-9]+)/change$', views.SampleChangeView.as_view(), name="sample_change"),

    # location static views
    url(r'^location/$', views.LocationListView.as_view(), name="location_list"),
    url(r'^project/(?P<project_id>[0-9]+)/location/$', views.LocationListView.as_view(), name="project_location_list"),
    url(r'^project/(?P<project_id>[0-9]+)/location/add$', views.LocationAddView.as_view(), name="location_add"),

    # location object views
    url(r'^location/(?P<pk>[0-9]+)$', views.LocationDetailView.as_view(), name="location_detail"),
    url(r'^location/(?P<pk>[0-9]+)/change$', views.LocationChangeView.as_view(), name="location_change"),

    # template views
    url(r'^template/$', views.TemplateListView.as_view(), name='template_list'),
    url(r'^project/(?P<project_id>[0-9]+)/template/$', views.TemplateListView.as_view(), name='project_template_list'),
    url(r'^template/(?P<template_pk>[0-9]+)$', views.TemplateFormView.as_view(), name='template_form'),
    url(r'^template/(?P<template_pk>[0-9]+)/bulk/$', views.TemplateBulkView.as_view(), name='template_bulk'),

    # user object views
    url(r'^user/(?P<pk>[0-9]+)$', views.UserDetailView.as_view(), name="user_detail"),
    url(r'^project/(?P<project_id>[0-9]+)/user/(?P<pk>[0-9]+)$',
        views.UserDetailView.as_view(),
        name="project_user_detail"
        ),

    # term object views
    url(r'^term/(?P<pk>[0-9]+)$', views.TermDetailView.as_view(), name="term_detail"),

    # action views
    url(r'^(?P<model>[a-z]+)/(?P<pk>[0-9]+)/action/(?P<action>[a-z-]+)$', views.item_action_view, name='item_action'),
    url(r'^(?P<model>[a-z]+)/action/(?P<action>[a-z-]+)$', views.base_action_view, name='bulk_action'),
    url(r'^(?P<model>[a-z]+)/action/$', views.resolve_action_view, name='resolve_bulk_action'),

]
