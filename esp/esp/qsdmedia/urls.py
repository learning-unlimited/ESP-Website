from django.conf.urls import url

from esp.qsdmedia import views

urlpatterns = [
    url(r'^\/([^/]+)/?$', views.qsdmedia2),
    url(r'^\/([^/]+)\/([^/]+)/?$', views.qsdmedia2)]
