from django.urls import re_path

from esp.tests import views

urlpatterns = [re_path('^/?$', views.javascript_tests)]
