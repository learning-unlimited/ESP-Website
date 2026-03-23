from django.urls import re_path

from esp.qsdmedia import views

urlpatterns = [
    re_path(r'^\/([^/]+)/?$', views.qsdmedia2, name='qsdmedia'),
    re_path(r'^\/([^/]+)\/([^/]+)/?$', views.qsdmedia2, name='qsdmedia_with_dir'),
]
