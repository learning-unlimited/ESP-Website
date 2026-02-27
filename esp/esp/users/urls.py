from django.conf.urls import url

from esp.users import views
from esp.users.views.registration import GradeChangeRequestView
from esp.web.views import bio
from esp.web.views import main
from esp.web.views import myesp

urlpatterns = [
    url(r'^register/?$', views.user_registration_phase1,
        name='esp.users.views.user_registration_phase1'),
    url(r'^register/information/?$', views.user_registration_phase2,
        name='esp.users.views.user_registration_phase2'),
    url(r'^activate/?$', views.registration.activate_account, name='activate_account'),
    url(r'^passwdrecover/(success)?/?$', views.initial_passwd_request, name='passwd_recover'),
    url(r'^passwdrecover/?$', views.initial_passwd_request),
    url(r'^recoveremail/(success)?/?$', views.email_passwd_followup, name='recover_email'),
    url(r'^recoveremail/?$', views.email_passwd_followup),
    url(r'^cancelrecover/?$', views.email_passwd_cancel, name='cancel_recover'),
    url(r'^resend/?$', views.resend_activation_view,
        name='esp.users.views.resend_activation_view'),
    url(r'^signout/?$', views.signout, name='signout'),
    url(r'^signedout/?$', views.signed_out_message, name='signed_out'),
    url(r'^login/?$', views.CustomLoginView.as_view(), name="login"),
    url(r'^disableaccount/?$', views.disable_account, name='disable_account'),
    url(r'^grade_change_request/?$', GradeChangeRequestView.as_view(),
        name='grade_change_request'),
    url(r'^makeadmin/?$', views.make_admin, name='make_admin'),
    url(r'^loginhelp', views.LoginHelpView.as_view(), name='Login Help'),
    url(r'^morph/?$', views.morph_into_user, name='morph_into_user'),
    url(r'^unsubscribe/(?P<username>[^/]+)/(?P<token>[\w.:\-_=]+)/$',
        views.unsubscribe, name="unsubscribe"),
    url(r'^unsubscribe_oneclick/(?P<username>[^/]+)/(?P<token>[\w.:\-_=]+)/$',
        views.unsubscribe_oneclick, name="unsubscribe_oneclick"),
]

urlpatterns += [
    url(r'^redirect/?$', main.registration_redirect, name='registration_redirect'),
]

urlpatterns += [
    url(r'^switchback/?$', myesp.myesp_switchback, name='myesp_switchback'),
    url(r'^onsite/?$', myesp.myesp_onsite, name='myesp_onsite'),
    url(r'^passwd/?$', myesp.myesp_passwd, name='myesp_passwd'),
    url(r'^accountmanage/?$', myesp.myesp_accountmanage, name='myesp_accountmanage'),
    url(r'^profile/?$', myesp.edit_profile, name='myesp_profile'),
]

urlpatterns += [
    url(r'^teacherbio/?$', bio.bio_edit, name='myesp_teacherbio'),
]
