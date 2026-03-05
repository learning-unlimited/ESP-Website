from django.conf.urls import url

from esp.web.views import bio

urlpatterns = [
    url(r'^(?P<username>[^/]+)/bio\.html$', bio.bio),
    url(r'^(?P<username>[^/]+)/bio\.edit\.html/?(.*)$', bio.bio_edit),
]
