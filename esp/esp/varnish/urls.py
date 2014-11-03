from django.conf.urls.defaults import *

urlpatterns = patterns('',
                        (r'^purge_page$', 'esp.varnish.views.varnish_purge'),
                        )
