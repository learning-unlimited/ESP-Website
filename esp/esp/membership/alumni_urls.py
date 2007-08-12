from django.conf.urls.defaults import *

urlpatterns = patterns('esp.membership.views',
                      (r'^contact/?$', 'alumniform'),
                      (r'^rsvp/?$', 'alumnirsvp'),
)
