from django.conf.urls import url

from esp.tests import views

urlpatterns = [url('^/?$', views.javascript_tests)]
