from django.conf.urls.defaults import *

urlpatterns = patterns('',
                        (r'^view_all/?$', 'esp.cache.views.view_all'),
                        (r'^flush/([0-9]+)/?$', 'esp.cache.views.flush')
                        )
