from django.conf.urls.defaults import *


urlpatterns = patterns('esp.users.views',
                       (r'^ajax_login/?', 'ajax_login'),
                       (r'^register/?$', 'user_registration',),
                       (r'^activate/?$', 'registration.activate_account',),
                       (r'^emaillist/?$', 'join_emaillist',),                   
                       (r'^passwdrecover/(success)?/?$', 'initial_passwd_request',),
                       (r'^passwdrecover/?$', 'initial_passwd_request',),
                       (r'^recoveremail/(success)?/?$', 'email_passwd_followup',),
                       (r'^recoveremail/?$', 'email_passwd_followup',),
                       (r'^cancelrecover/?$', 'email_passwd_cancel',),
                       (r'^signedout/?$', 'signed_out_message',),
                       (r'^login/?$',   'login_checked',),
                       (r'^login/byschool/?$',   'login_byschool.login_byschool',),
                       (r'^login/byschool/([0-9]+)/?$',   'login_byschool.login_byschool_pickname',),
                       (r'^login/byschool/new/?$',   'login_byschool.login_byschool_new',),
                       (r'^login/bybday/?$',   'login_by_bday.login_by_bday',),
                       (r'^login/bybday/([0-9]+)/([0-9]+)/?$',   'login_by_bday.login_by_bday_pickname',),
                       (r'^login/bybday/new/?$',   'login_by_bday.login_by_bday_new',),
                       (r'^disableaccount/?$', 'disable_account'),
                       (r'^emailpref/?$', 'emailpref'),
                       (r'^emailpref/(success)?/?$', 'emailpref'),
                       )

urlpatterns += patterns('esp.web.views.main',
                        (r'^redirect/?$', 'registration_redirect',),
                       )
