
from esp.themes.views import editor, selector, configure, landing, recompile

from django.conf.urls import *

urlpatterns = patterns('',
                        (r'^/?$', landing),
                        (r'^/select', selector),
                        (r'^/setup', configure),
                        (r'^/customize', editor),
                        (r'^/recompile', recompile),
                      )
