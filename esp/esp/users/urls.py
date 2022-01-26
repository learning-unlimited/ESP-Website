from django.conf.urls import url

from esp.users import views
from esp.users.views.registration import GradeChangeRequestView
from esp.web.views import bio
from esp.web.views import main
from esp.web.views import myesp
from django.views.generic import TemplateView

urlpatterns = [
    url(r'^register/?$', views.user_registration_phase1,
        name='esp.users.views.user_registration_phase1'),
    url(r'^register/information/?$', views.user_registration_phase2,
        name='esp.users.views.user_registration_phase2'),
    url(r'^activate/?$', views.registration.activate_account),
    url(r'^passwdrecover/(success)?/?$', views.initial_passwd_request),
    url(r'^passwdrecover/?$', views.initial_passwd_request),
    url(r'^recoveremail/(success)?/?$', views.email_passwd_followup),
    url(r'^recoveremail/?$', views.email_passwd_followup),
    url(r'^cancelrecover/?$', views.email_passwd_cancel),
    url(r'^resend/?$', views.resend_activation_view,
        name='esp.users.views.resend_activation_view'),
    url(r'^signout/?$', views.signout),
    url(r'^signedout/?$', views.signed_out_message),
    url(r'^login/?$',   views.login_checked),
    url(r'^disableaccount/?$', views.disable_account),
    url(r'^grade_change_request/?$', GradeChangeRequestView.as_view(), name = 'grade_change_request'),
    url(r'^makeadmin/?$', views.make_admin),
    url(r'^loginhelp', TemplateView.as_view(template_name='users/loginhelp.html'), name='Login Help'),
    url(r'^morph/?$', views.morph_into_user),
]

urlpatterns += [
    url(r'^redirect/?$', main.registration_redirect),
]

urlpatterns += [
    url(r'^switchback/?$', myesp.myesp_switchback),
    url(r'^onsite/?$', myesp.myesp_onsite),
    url(r'^passwd/?$', myesp.myesp_passwd),
    url(r'^accountmanage/?$', myesp.myesp_accountmanage),
    url(r'^profile/?$', myesp.edit_profile),
]

urlpatterns += [
    url(r'^teacherbio/?$', bio.bio_edit)
]
