from django.urls import re_path

from esp.users import views
from esp.users.views.registration import GradeChangeRequestView
from esp.web.views import bio
from esp.web.views import main
from esp.web.views import myesp

urlpatterns = [
    re_path(r'^register/?$', views.user_registration_phase1,
        name='esp.users.views.user_registration_phase1'),
    re_path(r'^register/information/?$', views.user_registration_phase2,
        name='esp.users.views.user_registration_phase2'),
    re_path(r'^activate/?$', views.registration.activate_account, name='activate_account'),
    re_path(r'^passwdrecover/(success)?/?$', views.initial_passwd_request, name='passwd_recover_success'),
    re_path(r'^passwdrecover/?$', views.initial_passwd_request, name='passwd_recover'),
    re_path(r'^resetpassword/(?P<uidb64>[-\w]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.password_reset_confirm, name='password_reset_confirm'),
    re_path(r'^resetpassword/done/?$', views.password_reset_done),
    re_path(r'^resend/?$', views.resend_activation_view,
        name='esp.users.views.resend_activation_view'),
    re_path(r'^signout/?$', views.signout, name='signout'),
    re_path(r'^signedout/?$', views.signed_out_message, name='signed_out'),
    re_path(r'^login/?$', views.CustomLoginView.as_view(), name="login"),
    re_path(r'^disableaccount/?$', views.disable_account, name='disable_account'),
    re_path(r'^grade_change_request/?$', GradeChangeRequestView.as_view(),
        name='grade_change_request'),
    re_path(r'^makeadmin/?$', views.make_admin, name='make_admin'),
    re_path(r'^loginhelp', views.LoginHelpView.as_view(), name='Login Help'),
    re_path(r'^morph/?$', views.morph_into_user, name='morph_into_user'),
    # username uses [^/]+ (not the narrower [\w.@+-]+) to preserve routing for
    # legacy usernames that may contain characters outside that charset.
    re_path(r'^unsubscribe/(?P<username>[^/]+)/(?P<token>[\w.:\-_=]+)/$',
        views.unsubscribe, name="unsubscribe"),
    re_path(r'^unsubscribe_oneclick/(?P<username>[^/]+)/(?P<token>[\w.:\-_=]+)/$',
        views.unsubscribe_oneclick, name="unsubscribe_oneclick"),
]

urlpatterns += [
    re_path(r'^redirect/?$', main.registration_redirect, name='registration_redirect'),
]

urlpatterns += [
    re_path(r'^switchback/?$', myesp.myesp_switchback, name='myesp_switchback'),
    re_path(r'^stop_testing/?$', myesp.myesp_stop_testing, name='myesp_stop_testing'),
    re_path(r'^onsite/?$', myesp.myesp_onsite, name='myesp_onsite'),
    re_path(r'^passwd/?$', myesp.myesp_passwd, name='myesp_passwd'),
    re_path(r'^accountmanage/?$', myesp.myesp_accountmanage, name='myesp_accountmanage'),
    re_path(r'^profile/?$', myesp.edit_profile, name='myesp_profile'),
]

urlpatterns += [
    re_path(r'^teacherbio/?$', bio.bio_edit, name='myesp_teacherbio'),
]
