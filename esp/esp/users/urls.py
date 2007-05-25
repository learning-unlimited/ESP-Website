from django.conf.urls.defaults import *


urlpatterns = patterns('esp.users.views',
                       (r'^register/?$', 'user_registration',),
                       (r'^emaillist/?$', 'join_emaillist',),
                       )
