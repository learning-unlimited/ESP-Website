from __future__ import absolute_import
from django.conf.urls import url

from esp.tests import views

urlpatterns = [url('^/?$', views.javascript_tests)]
