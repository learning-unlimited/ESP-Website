from django.conf.urls import url

from esp.customforms import views

urlpatterns = [
    url(r'^/?$', views.landing),
    url(r'^/create/$', views.formBuilder),
    url(r'^/submit/$', views.onSubmit),
    url(r'^/modify/$', views.onModify),
    url(r'^/view/(?P<form_id>\d{1,6})/$', views.viewForm),
    url(r'^/success/(?P<form_id>\d{1,6})/$', views.success),
    url(r'^/responses/(?P<form_id>\d{1,6})/$', views.viewResponse),
    url(r'^/getData/$', views.getData),
    url(r'^/metadata/$', views.getRebuildData),
    url(r'^/getperms/$', views.getPerms),
    url(r'^/getlinks/$', views.get_links),
    url(r'^/builddata/$', views.formBuilderData),
    url(r'^/exceldata/(?P<form_id>\d{1,6})/$', views.getExcelData),
]
