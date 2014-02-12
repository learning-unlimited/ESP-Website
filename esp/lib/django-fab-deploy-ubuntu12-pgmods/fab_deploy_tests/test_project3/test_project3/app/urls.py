# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.conf.urls import patterns, include, url

urlpatterns = patterns('test_project3.app.views',
    url(r'^get/$', 'get_all'),
    url(r'^create/(?P<name>.+)/$', 'create'),
)
