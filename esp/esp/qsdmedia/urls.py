from django.conf.urls import url

from esp.qsdmedia import views

urlpatterns = [
    url(r'^\/([^/]+)/?$', views.qsdmedia2, name='qsdmedia'),
    url(r'^\/([^/]+)\/([^/]+)/?$', views.qsdmedia2, name='qsdmedia_with_dir'),
]
