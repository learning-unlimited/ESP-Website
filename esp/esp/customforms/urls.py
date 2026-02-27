from django.conf.urls import url

from esp.customforms import views

urlpatterns = [
    url(r'^/?$', views.landing, name='customforms_landing'),
    url(r'^/create/?$', views.formBuilder, name='customforms_create'),
    url(r'^/submit/$', views.onSubmit, name='customforms_submit'),
    url(r'^/modify/$', views.onModify, name='customforms_modify'),
    url(r'^/view/(?P<form_id>\d{1,6})/$', views.viewForm, name='customforms_view'),
    url(r'^/success/(?P<form_id>\d{1,6})/$', views.success, name='customforms_success'),
    url(r'^/responses/(?P<form_id>\d{1,6})/$', views.viewResponse, name='customforms_responses'),
    url(r'^/getData/$', views.getData, name='customforms_get_data'),
    url(r'^/metadata/$', views.getRebuildData, name='customforms_metadata'),
    url(r'^/getperms/$', views.getPerms, name='customforms_get_perms'),
    url(r'^/getlinks/$', views.get_links, name='customforms_get_links'),
    url(r'^/getmodules/$', views.get_modules, name='customforms_get_modules'),
    url(r'^/builddata/$', views.formBuilderData, name='customforms_build_data'),
    url(r'^/exceldata/(?P<form_id>\d{1,6})/$', views.getExcelData, name='customforms_excel_data'),
    url(r'^/bulkdownloadfiles/?', views.bulkDownloadFiles, name='customforms_bulk_download'),
]
