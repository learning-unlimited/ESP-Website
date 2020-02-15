from django.conf.urls import url

from esp.formstack import views

urlpatterns = [
    url(r'^medicalsyncapi$', views.medicalsyncapi),
    url(r'^formstack_webhook/?$', views.formstack_webhook)
]
