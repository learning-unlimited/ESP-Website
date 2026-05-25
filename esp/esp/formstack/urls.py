from django.urls import re_path

from esp.formstack import views

urlpatterns = [
    re_path(r'^medicalsyncapi$', views.medicalsyncapi, name='formstack_medicalsyncapi'),
    re_path(r'^formstack_webhook/?$', views.formstack_webhook, name='formstack_webhook'),
]
