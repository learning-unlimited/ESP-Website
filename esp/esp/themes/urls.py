
from esp.themes.views import editor, selector, landing

from django.conf.urls.defaults import *

urlpatterns = patterns('',
                        (r'^$', landing),
                        (r'^select/?$', selector),
                        (r'^customize/?$', editor),
                      )
