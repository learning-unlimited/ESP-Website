from django.conf.urls import *

urlpatterns = patterns('',
                        (r'^purge_page$', 'esp.varnish.views.varnish_purge'),
                        )
