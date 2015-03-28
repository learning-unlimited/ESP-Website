from django.conf.urls.defaults import *

urlpatterns = patterns('',
                       (r'^$', 'esp.resources.views.main'),
                       (r'^locations/$', 'esp.resources.views.locations'),
                       )
