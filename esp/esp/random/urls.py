from django.conf.urls import url
from esp.random import views

urlpatterns = [
    url(r'^/?$', views.main, name='random_main'),
    url(r'^/ajax$', views.ajax, name='random_ajax'),
]
