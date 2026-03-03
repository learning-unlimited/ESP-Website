from django.urls import path, re_path
from esp.random import views

urlpatterns = [
    re_path(r'^/?$', views.main),
    path('/ajax', views.ajax),
]
