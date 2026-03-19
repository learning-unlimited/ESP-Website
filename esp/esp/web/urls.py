from django.urls import re_path
from esp.web.views import bio

urlpatterns = [
    re_path(r'^(?P<username>[^/]+)/bio\.html$', bio.bio),
    re_path(r'^(?P<username>[^/]+)/bio\.edit\.html/?(.*)$', bio.bio_edit),
]
