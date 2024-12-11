
from __future__ import absolute_import
from esp.themes.views import editor, selector, configure, confirm_overwrite, landing, recompile, logos

from django.conf.urls import url

urlpatterns = [
    url(r'^/?$', landing),
    url(r'^/select', selector),
    url(r'^/setup', configure),
    url(r'^/confirm_overwrite', confirm_overwrite),
    url(r'^/logos', logos),
    url(r'^/customize', editor),
    url(r'^/recompile', recompile),
]
