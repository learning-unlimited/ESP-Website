from django.urls import re_path
from esp.web.views import bio

urlpatterns = [
    # bios (/learn URLs are deprecated)
    re_path(r'^(?P<username>[^/]+)/bio\.html$', bio.bio, name='teacher_bio'),
    re_path(r'^(?P<username>[^/]+)/bio\.edit\.html/?$', bio.bio_edit, name='teacher_bio_edit'),
]
