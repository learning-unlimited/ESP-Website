from django.urls import re_path

from esp.customforms import views

urlpatterns = [
    re_path(r'^/?$', views.landing),
    re_path(r'^/create/?$', views.formBuilder),
    re_path(r'^/submit/$', views.onSubmit),
    re_path(r'^/modify/$', views.onModify),
    re_path(r'^/view/(?P<form_id>\d{1,6})/$', views.viewForm),
    re_path(r'^/success/(?P<form_id>\d{1,6})/$', views.success),
    re_path(r'^/responses/(?P<form_id>\d{1,6})/$', views.viewResponse),
    re_path(r'^/getData/$', views.getData),
    re_path(r'^/metadata/$', views.getRebuildData),
    re_path(r'^/getperms/$', views.getPerms),
    re_path(r'^/getlinks/$', views.get_links),
    re_path(r'^/getmodules/$', views.get_modules),
    re_path(r'^/builddata/$', views.formBuilderData),
    re_path(r'^/exceldata/(?P<form_id>\d{1,6})/$', views.getExcelData),
    re_path(r'^/bulkdownloadfiles/?', views.bulkDownloadFiles)
]
