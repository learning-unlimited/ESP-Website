from django.conf.urls import url
from django.urls import path
from esp.themes.views import editor, selector, configure, confirm_overwrite, landing, recompile, logos, admin_toolbar_links

urlpatterns = [
    url(r'^/?$', landing),
    url(r'^/select', selector),
    url(r'^/setup', configure),
    url(r'^/confirm_overwrite', confirm_overwrite),
    url(r'^/logos', logos),
    url(r'^/customize', editor),
    url(r'^/recompile', recompile),
    url(r'^/api/toolbar-links/$', admin_toolbar_links, name='admin_toolbar_links'),
]