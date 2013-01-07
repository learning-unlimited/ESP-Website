
from esp.themes.views import editor, selector, configure, landing

from django.conf.urls.defaults import *

urlpatterns = patterns('',
                        (r'^$', landing),
                        (r'^select/?$', selector),
                        (r'^setup/?$', configure),
                        (r'^customize/?$', editor),
                      )
