
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

    # user object views
    url(r'^user/(?P<pk>[0-9]+)$', views.UserDetailView.as_view(), name="user_detail"),
    url(r'^project/(?P<project_id>[0-9]+)/user/(?P<pk>[0-9]+)$',
        views.UserDetailView.as_view(),
        name="project_user_detail"
    ),

    # term object views
    url(r'^term/(?P<pk>[0-9]+)$', views.TermDetailView.as_view(), name="term_detail"),

    # attachment object views
    url(r'^attachment/(?P<pk>[0-9]+)$', views.AttachmentDetailView.as_view(), name="attachment_detail"),
    url(r'^attachment/(?P<pk>[0-9]+)/download$', views.AttachmentDownloadView.as_view(), name="attachment_download"),

    # action views
    url(r'^(?P<model>[a-z]+)/(?P<pk>[0-9]+)/action/(?P<action>[a-z-]+)$', views.item_action_view, name='item_action'),
    url(r'^(?P<model>[a-z]+)/action/(?P<action>[a-z-]+)$', views.base_action_view, name='bulk_action'),
    url(r'^(?P<model>[a-z]+)/action/$', views.resolve_action_view, name='resolve_bulk_action'),

    # ajax views
    url(r'^ajax/select2/(?P<model_name>[A-Za-z]+)/$', views.LimsSelect2Ajax.as_view(), name='ajax_select2'),

]
