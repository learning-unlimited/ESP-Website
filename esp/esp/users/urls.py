from django.urls import re_path, path

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
    re_path(r'^activate/?$', views.registration.activate_account),
    re_path(r'^passwdrecover/(success)?/?$', views.initial_passwd_request),
    re_path(r'^passwdrecover/?$', views.initial_passwd_request),
    re_path(r'^recoveremail/(success)?/?$', views.email_passwd_followup),
    re_path(r'^recoveremail/?$', views.email_passwd_followup),
    re_path(r'^cancelrecover/?$', views.email_passwd_cancel),
    re_path(r'^resend/?$', views.resend_activation_view,
        name='esp.users.views.resend_activation_view'),
    re_path(r'^signout/?$', views.signout),
    re_path(r'^signedout/?$', views.signed_out_message),
    re_path(r'^login/?$', views.CustomLoginView.as_view(), name="login"),
    re_path(r'^disableaccount/?$', views.disable_account),
    re_path(r'^grade_change_request/?$', GradeChangeRequestView.as_view(),
        name='grade_change_request'),
    re_path(r'^makeadmin/?$', views.make_admin),
    path('loginhelp', views.LoginHelpView.as_view(), name='Login Help'),
    re_path(r'^morph/?$', views.morph_into_user),
    re_path(r'^unsubscribe/(?P<username>[^/]+)/(?P<token>[\w.:\-_=]+)/$',
        views.unsubscribe, name="unsubscribe"),
    re_path(r'^unsubscribe_oneclick/(?P<username>[^/]+)/(?P<token>[\w.:\-_=]+)/$',
        views.unsubscribe_oneclick, name="unsubscribe_oneclick"),
]

urlpatterns += [
    re_path(r'^redirect/?$', main.registration_redirect),
]

urlpatterns += [
    re_path(r'^switchback/?$', myesp.myesp_switchback),
    re_path(r'^stop_testing/?$', myesp.myesp_stop_testing),
    re_path(r'^onsite/?$', myesp.myesp_onsite),
    re_path(r'^passwd/?$', myesp.myesp_passwd),
    re_path(r'^accountmanage/?$', myesp.myesp_accountmanage),
    re_path(r'^profile/?$', myesp.edit_profile),
]

urlpatterns += [
    re_path(r'^teacherbio/?$', bio.bio_edit)
]
