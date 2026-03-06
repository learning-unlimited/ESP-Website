import logging
import re
import urllib.request, urllib.parse, urllib.error

from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

log = logging.getLogger(__name__)

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseRedirect
from django.template import loader
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.decorators import method_decorator

from vanilla import CreateView

from esp.dbmail.models import send_mail
from esp.middleware.esperrormiddleware import ESPError
from esp.tagdict.models import Tag
from esp.users.controllers.usersearch import UserSearchController
from esp.users.forms.user_reg import UserRegForm, EmailUserRegForm, AwaitingActivationEmailForm, SinglePhaseUserRegForm, GradeChangeRequestForm
from esp.users.models import ESPUser
from esp.users.tokens import account_activation_token
from esp.utils.web import render_to_response


__all__ = ['user_registration_phase1', 'user_registration_phase2', 'resend_activation_view']


def user_registration_validate(request):
    """Handle the account creation logic when the form is submitted

This function is overloaded to handle either one or two phase reg"""

    if not Tag.getBooleanTag("ask_about_duplicate_accounts"):
        form = SinglePhaseUserRegForm(request.POST)
    else:
        form = UserRegForm(request.POST)

    if form.is_valid():
        try:
            #there is an email-only account with that email address to upgrade
            user = ESPUser.objects.get(email=form.cleaned_data['email'],
                                       password = 'emailuser')
        except ESPUser.DoesNotExist:
            try:
                #there is an inactive account with that username
                user = ESPUser.objects.filter(
                    username = form.cleaned_data['username'],
                    is_active = False).latest('date_joined')

            except ESPUser.DoesNotExist:
                user = ESPUser.objects.create_user(username=form.cleaned_data['username'],
                                                   email=form.cleaned_data['email'])

        user.username   = form.cleaned_data['username']
        user.last_name  = form.cleaned_data['last_name']
        user.first_name = form.cleaned_data['first_name']
        user.set_password(form.cleaned_data['password'])

        #   Disable account until email activation if required
        if Tag.getBooleanTag('require_email_validation'):
            user.is_active = False

        user.save()

        user.groups.add(Group.objects.get(name=form.cleaned_data['initial_role']))

        if not Tag.getBooleanTag('require_email_validation'):
            user = authenticate(username=form.cleaned_data['username'],
                                    password=form.cleaned_data['password'])

            login(request, user)
            return HttpResponseRedirect('/myesp/profile/')
        else:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = account_activation_token.make_token(user)
            send_activation_email(user, uid, token)
            return render_to_response('registration/account_created_activation_required.html', request,
                                      {'user': user, 'site': Site.objects.get_current()})
    else:
        return render_to_response('registration/newuser.html',
                                  request, {'form':form})

def user_registration_checkemail(request):
    """Method to handle the first phase of registration when submitted as a form.

The method user_registration_phase1 calls this function when it's given a POST request.
When the form isn't valid, re-render the same template but with the form errors.
When there are already accounts with this email address (depending on some tags), give the user information about them before proceeding.
"""
    form = EmailUserRegForm(request.POST)

    if form.is_valid():
        ## First, check to see if we have any users with the same email
        if not 'do_reg_no_really' in request.POST and Tag.getBooleanTag('ask_about_duplicate_accounts'):
            accounts_role = ESPUser.objects.filter(ESPUser.getAllOfType(form.cleaned_data['initial_role'], True))
            existing_accounts = accounts_role.filter(email=form.cleaned_data['email'], is_active=True).exclude(password='emailuser')
            awaiting_activation_accounts = accounts_role.filter(email=form.cleaned_data['email'], is_active=False).exclude(password='emailuser')
            if len(existing_accounts)+len(awaiting_activation_accounts) != 0:
                #they have accounts. go back to the same page, but ask them
                #if they want to try to log in
                return render_to_response(
                    'registration/newuser_phase1.html',
                    request,
                    { 'accounts': existing_accounts,'awaitings':awaiting_activation_accounts, 'email':form.cleaned_data['email'], 'initial_role':form.cleaned_data['initial_role'], 'site': Site.objects.get_current(), 'form': form })

        #form is valid, and not caring about multiple accounts
        email = urllib.parse.quote(form.cleaned_data['email'])
        initial_role = urllib.parse.quote(form.cleaned_data['initial_role'])
        return HttpResponseRedirect(reverse('esp.users.views.user_registration_phase2')+'?email='+email+'&initial_role='+initial_role)
    else: #form is not valid
        return render_to_response('registration/newuser_phase1.html',
                                  request,
                                  {'form':form, 'site': Site.objects.get_current()})

def user_registration_phase1(request):
    """Displays phase 1, and receives and passes off phase 1 submissions."""
    if request.user.is_authenticated:
        return render_to_response('registration/already_logged_in.html',
                                  request, {})

    #depending on a tag, we'll either have registration all in one page,
    #or in two separate ones
    if not Tag.getBooleanTag("ask_about_duplicate_accounts"):
        if request.method == 'POST':
            return user_registration_validate(request)

        form=SinglePhaseUserRegForm()
        return render_to_response('registration/newuser.html',
                                  request,
                                  {'form':form, 'site': Site.objects.get_current()})

    #we do want to ask about duplicate accounts
    if request.method == 'POST':
        return user_registration_checkemail(request)

    form=EmailUserRegForm()
    return render_to_response('registration/newuser_phase1.html',
                              request,
                              {'form':form, 'site': Site.objects.get_current()})

def user_registration_phase2(request):
    """Displays the second part of account creation, and when that form is submitted, call a function to handle the actual validation and creation."""
    if request.method == 'POST':
        return user_registration_validate(request)

    if not Tag.getBooleanTag("ask_about_duplicate_accounts"):
        return HttpResponseRedirect(reverse("esp.users.views.user_registration_phase1"))

    try:
        email = urllib.parse.unquote(request.GET['email'])
        initial_role = urllib.parse.unquote(request.GET['initial_role'])
    except MultiValueDictKeyError:
        return HttpResponseRedirect(reverse("esp.users.views.user_registration_phase1"))
    form = UserRegForm(initial={'email':email,'confirm_email':email,'initial_role':initial_role})
    return render_to_response('registration/newuser.html',
                              request, {'form':form, 'email':email})


def activate_account(request, uidb64, token):
    """Activate account using a secure HMAC token (new-style links)."""
    u = None
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        u = ESPUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, ESPUser.DoesNotExist):
        pass

    if u is None:
        raise ESPError("Invalid activation link. Please use the <a href='/myesp/resend/'>resend form</a> to get a new one.", log=False)

    if u.is_active:
        raise ESPError('This account is already activated. <a href="/accounts/login/?next=/myesp/profile/">Log in</a> or <a href="/myesp/passwdrecover/">recover your password</a>.', log=False)

    if not account_activation_token.check_token(u, token):
        raise ESPError("This activation link is invalid or has expired. Please use the <a href='/myesp/resend/'>resend form</a> to get a new link.", log=False)

    # Remove legacy activation token suffix from password field if present
    u.password = re.sub(r'_\d+$', '', u.password)
    u.is_active = True
    u.save()
    return HttpResponseRedirect('/myesp/profile/')


def activate_account_legacy(request):
    """Handle old-style activation links (?username=X&key=Y). Kept for backward compatibility."""
    if 'username' not in request.GET or 'key' not in request.GET:
        raise ESPError("Invalid account activation information. Please use the <a href='/myesp/resend/'>resend form</a> to get a new link.", log=False)

    try:
        u = ESPUser.objects.get(username=request.GET['username'])
    except ESPUser.DoesNotExist:
        raise ESPError("Invalid account username. Please contact us if this error persists.", log=False)

    if u.is_active:
        raise ESPError('This account is already activated. <a href="/accounts/login/?next=/myesp/profile/">Log in</a> or <a href="/myesp/passwdrecover/">recover your password</a>.', log=False)

    if not u.password.endswith("_%s" % request.GET['key']):
        raise ESPError("Incorrect key. Please use the <a href='/myesp/resend/'>resend form</a> to get a new activation link.", log=False)

    u.password = u.password[:-(len("_%s" % request.GET['key']))]
    u.is_active = True
    u.save()
    return HttpResponseRedirect('/myesp/profile/')

def send_activation_email(user, uid, token):
    t = loader.get_template('registration/activation_email.txt')
    c = {'user': user, 'uid': uid, 'token': token, 'site': Site.objects.get_current()}
    send_mail("Account Activation", t.render(c), settings.SERVER_EMAIL, [user.email], fail_silently=False)

def resend_activation_view(request):
    if request.user.is_authenticated:
        return render_to_response('registration/already_logged_in.html',
                                  request, {})

    if request.method == 'POST':
        form=AwaitingActivationEmailForm(request.POST)
        if not form.is_valid():
            return render_to_response('registration/resend.html', request,
                                      {'form':form, 'site': Site.objects.get_current()})
        user = ESPUser.objects.get(username=form.cleaned_data['username'])
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = account_activation_token.make_token(user)
        send_activation_email(user, uid, token)
        return render_to_response('registration/resend_done.html', request,
                                  {'form':form, 'site': Site.objects.get_current()})
    else:
        form=AwaitingActivationEmailForm()
        return render_to_response('registration/resend.html', request,
                                  {'form':form, 'site': Site.objects.get_current()})


class GradeChangeRequestView(CreateView):
    """
    Handles Display of Grade Change Request Form and dispatching of request.
    """
    template_name = 'users/profiles/gradechangerequestform.html'
    form_class = GradeChangeRequestForm
    success_url = reverse_lazy('grade_change_request')

    def form_valid(self, form):
        change_request = form.save(commit=False)
        change_request.requesting_student = self.request.user
        change_request.grade_before_request = self.request.user.getGrade()
        change_request.save()
        messages.add_message(self.request, messages.SUCCESS, "Your grade change request was sent! You will receive an email containing your approval status shortly.")

        log.info('grade change request sent by user %s'%(self.request.user,))

        return HttpResponseRedirect(self.success_url)

    def render_to_response(self, context):
        #   Override rendering function to use our context processors.
        from esp.utils.web import render_to_response as render_to_response_base
        return render_to_response_base(self.template_name, self.request, context)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


