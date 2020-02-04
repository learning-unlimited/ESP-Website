
from esp.themes.views import editor, selector, configure, confirm_overwrite, landing, recompile

from django.conf.urls import url

urlpatterns = [
    url(r'^/?$', landing),
    url(r'^/select', selector),
    url(r'^/setup', configure),
    url(r'^/confirm_overwrite', confirm_overwrite),
    url(r'^/customize', editor),
    url(r'^/recompile', recompile),
]
