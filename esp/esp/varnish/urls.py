from django.urls import path

from esp.varnish import views

urlpatterns = [
    path('purge_page', views.varnish_purge),
]
