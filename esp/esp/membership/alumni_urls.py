from django.conf.urls.defaults import *

urlpatterns = patterns('esp.membership.views',
                      (r'^contact/?$', 'alumnicontact'),
                      (r'^lookup/?$', 'alumnilookup'),
                      (r'^/?$', 'alumnihome'),
                      (r'^rsvp/?$', 'alumnirsvp'),
                      (r'^thread/([-A-Za-z0-9_ ]+)?$', 'thread'),
)
