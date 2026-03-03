from django.urls import path, re_path

from esp.formstack import views

urlpatterns = [
    path('medicalsyncapi', views.medicalsyncapi),
    re_path(r'^formstack_webhook/?$', views.formstack_webhook)
]
