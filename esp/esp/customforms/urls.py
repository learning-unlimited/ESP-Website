from django.urls import path, re_path

from esp.customforms import views

urlpatterns = [
    re_path(r'^/?$', views.landing),
    re_path(r'^/create/?$', views.formBuilder),
    path('/submit/', views.onSubmit),
    path('/modify/', views.onModify),
    re_path(r'^/view/(?P<form_id>\d{1,6})/$', views.viewForm),
    re_path(r'^/success/(?P<form_id>\d{1,6})/$', views.success),
    re_path(r'^/responses/(?P<form_id>\d{1,6})/$', views.viewResponse),
    path('/getData/', views.getData),
    path('/metadata/', views.getRebuildData),
    path('/getperms/', views.getPerms),
    path('/getlinks/', views.get_links),
    path('/getmodules/', views.get_modules),
    path('/builddata/', views.formBuilderData),
    re_path(r'^/exceldata/(?P<form_id>\d{1,6})/$', views.getExcelData),
    re_path(r'^/bulkdownloadfiles/?', views.bulkDownloadFiles)
]
