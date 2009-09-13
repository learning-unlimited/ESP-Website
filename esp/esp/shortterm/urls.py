from django.conf.urls.defaults import *

urlpatterns = patterns('esp.shortterm.views',
                       (r'^school_response/?', 'school_response_form'),
                       (r'^volunteer/signup/?$', 'volunteer_signup',),
                      )
