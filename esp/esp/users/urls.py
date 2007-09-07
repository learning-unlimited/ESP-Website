from django.conf.urls.defaults import *


urlpatterns = patterns('esp.users.views',
                       (r'^register/?$', 'user_registration',),
                       (r'^emaillist/?$', 'join_emaillist',),                   
                       (r'^passwdrecover/(success)?/?$', 'initial_passwd_request',),
                       (r'^recoveremail/(success)?/?$', 'email_passwd_followup',),
                       (r'^passwdrecover/?$', 'initial_passwd_request',),
                       (r'^recoveremail/?$', 'email_passwd_followup',),
                       (r'^signedout/?$', 'signed_out_message',),
                       (r'^login/?$',   'login_checked',),
                       (r'^disableaccount/?$', 'disable_account'),
                       )
