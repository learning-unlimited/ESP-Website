from django.conf.urls import url
from esp.random import views

urlpatterns = [
    url(r'^/?$', views.main),
    url(r'^/ajax$', views.ajax),
]
