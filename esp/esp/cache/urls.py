from django.conf.urls.defaults import *

urlpatterns = patterns('',
                        (r'^view_all/?$', 'esp.cache.views.view_all'),
                        (r'^varnish_purge$', 'esp.cache.views.varnish_purge'),
                        )
