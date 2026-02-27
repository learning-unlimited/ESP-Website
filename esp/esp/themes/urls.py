
from esp.themes.views import editor, selector, configure, confirm_overwrite, landing, recompile, logos

from django.conf.urls import url

urlpatterns = [
    url(r'^/?$', landing, name='themes_landing'),
    url(r'^/select', selector, name='themes_select'),
    url(r'^/setup', configure, name='themes_configure'),
    url(r'^/confirm_overwrite', confirm_overwrite, name='themes_confirm_overwrite'),
    url(r'^/logos', logos, name='themes_logos'),
    url(r'^/customize', editor, name='themes_editor'),
    url(r'^/recompile', recompile, name='themes_recompile'),
]
