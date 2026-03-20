from django.urls import re_path

from esp.qsdmedia import views

urlpatterns = [
    re_path(r'^\/([^/]+)/?$', views.qsdmedia2),
    re_path(r'^\/([^/]+)\/([^/]+)/?$', views.qsdmedia2)]
