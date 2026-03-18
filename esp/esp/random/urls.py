from django.urls import re_path
from esp.random import views

urlpatterns = [
    re_path(r'^/?$', views.main),
    re_path(r'^/ajax$', views.ajax),
]
