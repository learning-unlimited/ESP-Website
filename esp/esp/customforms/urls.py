from django.urls import re_path

from esp.customforms import views

urlpatterns = [
    re_path(r'^/?$', views.landing, name='customforms_landing'),
    re_path(r'^/create/?$', views.formBuilder, name='customforms_create'),
    re_path(r'^/submit/$', views.onSubmit, name='customforms_submit'),
    re_path(r'^/modify/$', views.onModify, name='customforms_modify'),
    re_path(r'^/view/(?P<form_id>\d{1,6})/$', views.viewForm, name='customforms_view'),
    re_path(r'^/success/(?P<form_id>\d{1,6})/$', views.success, name='customforms_success'),
    re_path(r'^/responses/(?P<form_id>\d{1,6})/$', views.viewResponse, name='customforms_responses'),
    re_path(r'^/getData/$', views.getData, name='customforms_get_data'),
    re_path(r'^/metadata/$', views.getRebuildData, name='customforms_metadata'),
    re_path(r'^/getperms/$', views.getPerms, name='customforms_get_perms'),
    re_path(r'^/getlinks/$', views.get_links, name='customforms_get_links'),
    re_path(r'^/getprograms/$', views.get_programs, name='customforms_get_programs'),
    re_path(r'^/getmodules/$', views.get_modules, name='customforms_get_modules'),
    re_path(r'^/builddata/$', views.formBuilderData, name='customforms_build_data'),
    re_path(r'^/exceldata/(?P<form_id>\d{1,6})/$', views.getExcelData, name='customforms_excel_data'),
    re_path(r'^/bulkdownloadfiles/?', views.bulkDownloadFiles, name='customforms_bulk_download'),
]
