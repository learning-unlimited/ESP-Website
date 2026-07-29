from __future__ import absolute_import
from django.conf.urls import url

from esp.varnish import views

urlpatterns = [
    url(r'^purge_page$', views.varnish_purge),
]
