
from esp.themes.views import editor, selector, configure, confirm_overwrite, landing, recompile, logos

from django.urls import re_path

urlpatterns = [
    re_path(r'^/?$', landing, name='themes_landing'),
    re_path(r'^/select', selector, name='themes_select'),
    re_path(r'^/setup', configure, name='themes_configure'),
    re_path(r'^/confirm_overwrite', confirm_overwrite, name='themes_confirm_overwrite'),
    re_path(r'^/logos', logos, name='themes_logos'),
    re_path(r'^/customize', editor, name='themes_editor'),
    re_path(r'^/recompile', recompile, name='themes_recompile'),
]
