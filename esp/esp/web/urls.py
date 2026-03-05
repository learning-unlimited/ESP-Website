from django.conf.urls import url

from esp.web.views import bio

urlpatterns = [
    # bios (/learn URLs are deprecated)
    url(r'^(?P<username>[^/]+)/bio\.html$', bio.bio, name='teacher_bio'),
    url(r'^(?P<username>[^/]+)/bio\.edit\.html/?(.*)$', bio.bio_edit, name='teacher_bio_edit'),
    # more deprecated URLs for bios
    url(r'^(?P<last>[-A-Za-z0-9_ \.]+)/(?P<first>[-A-Za-z_ \.]+)(?P<usernum>[0-9]*)/bio\.html$', bio.bio, name='teacher_bio_by_name'),
    url(r'^(?P<last>[-A-Za-z0-9_ ]+)/(?P<first>[-A-Za-z_ ]+)(?P<usernum>[0-9]*)/bio\.edit\.html/?(.*)$', bio.bio_edit, name='teacher_bio_edit_by_name'),
]
