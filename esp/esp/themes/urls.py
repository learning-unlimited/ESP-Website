
from esp.themes.views import editor, selector, configure, confirm_overwrite, landing, recompile, logos

from django.urls import re_path

urlpatterns = [
    re_path(r'^/?$', landing),
    re_path(r'^/select', selector),
    re_path(r'^/setup', configure),
    re_path(r'^/confirm_overwrite', confirm_overwrite),
    re_path(r'^/logos', logos),
    re_path(r'^/customize', editor),
    re_path(r'^/recompile', recompile),
]
