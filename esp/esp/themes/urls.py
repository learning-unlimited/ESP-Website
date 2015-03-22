
from esp.themes.views import editor, selector, configure, confirm_overwrite, landing, recompile

from django.conf.urls import *

urlpatterns = patterns('',
                        (r'^/?$', landing),
                        (r'^/select', selector),
                        (r'^/setup', configure),
                        (r'^/confirm_overwrite', confirm_overwrite),
                        (r'^/customize', editor),
                        (r'^/recompile', recompile),
                      )
