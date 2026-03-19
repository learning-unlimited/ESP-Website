from django.urls import re_path

from esp.varnish import views

urlpatterns = [
    re_path(r'^purge_page$', views.varnish_purge),
]
