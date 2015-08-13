from django.conf.urls import patterns

urlpatterns = patterns('',
                       (r'^$', 'esp.resources.views.main'),
                       (r'^locations/$', 'esp.resources.views.locations'),
                       )
