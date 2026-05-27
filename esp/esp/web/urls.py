from django.urls import re_path

from esp.web.views import bio

urlpatterns = [
    # bios (/learn URLs are deprecated)
    re_path(r'^(?P<username>[^/]+)/bio\.html$', bio.bio, name='teacher_bio'),
    re_path(r'^(?P<username>[^/]+)/bio\.edit\.html/?(?:.*)$', bio.bio_edit, name='teacher_bio_edit'),
    # more deprecated URLs for bios
    re_path(r'^(?P<last>[-A-Za-z0-9_ \.]+)/(?P<first>[-A-Za-z_ \.]+)(?P<usernum>[0-9]*)/bio\.html$', bio.bio, name='teacher_bio_by_name'),
    re_path(r'^(?P<last>[-A-Za-z0-9_ ]+)/(?P<first>[-A-Za-z_ ]+)(?P<usernum>[0-9]*)/bio\.edit\.html/?(?:.*)$', bio.bio_edit, name='teacher_bio_edit_by_name'),
]
