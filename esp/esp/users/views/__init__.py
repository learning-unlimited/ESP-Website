from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from esp.program.models import Program, RegistrationProfile
from esp.tagdict.models import Tag
from esp.users.models import ESPUser, admin_required
from esp.users.models.forwarder import UserForwarder
from esp.users.views.make_admin import *
from esp.users.views.password_reset import *
from esp.users.views.registration import *
from esp.users.views.usersearch import *
from esp.utils.web import render_to_response
from esp.web.views.main import DefaultQSDView


#   This is a huge hack while we figure out what to do about logins and cookies.
#   - Michael P 12/28/2011
def HttpMetaRedirect(location='/'):
    response = HttpResponse()
    response.status = 200
    response.content = """
    <html><head>
    <meta http-equiv="refresh" content="0; url=%s">
    </head>
    <body>Thank you for logging in.  Please click <a href="%s">here</a> if you are not redirected.</body>
    </html>
    """ % (location, location)
    return response

mask_locations = ['/', '/myesp/signout', '/myesp/signout/', '/admin/logout/']
def mask_redirect(user, next):
    # We're getting redirected to somewhere undesirable.
    # Let's try to do something smarter.
    admin_home_url = Tag.getTag('admin_home_page')
    teacher_home_url = Tag.getTag('teacher_home_page')
    student_home_url = Tag.getTag('student_home_page')
    if user.isAdmin() and admin_home_url:
        return HttpMetaRedirect(admin_home_url)
    elif user.isTeacher() and teacher_home_url:
        return HttpMetaRedirect(teacher_home_url)
    elif user.isStudent() and student_home_url:
        return HttpMetaRedirect(student_home_url)
    else:
        return HttpMetaRedirect('/')

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def render_to_response(self, context, **response_kwargs):
        response_kwargs.setdefault("content_type", self.content_type)
        return render_to_response(
            request=self.request,
            template=self.get_template_names(),
            context=context,
            **response_kwargs,
        )

    def get(self, request, *args, **kwargs):
        # If already authenticated, handle redirect logic
        if request.user.is_authenticated:
            return self.handle_authenticated_user(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # If already authenticated, handle redirect logic
        if request.user.is_authenticated:
            return self.handle_authenticated_user(request)
        return super().post(request, *args, **kwargs)

    def handle_authenticated_user(self, request):
        """Handle redirects for users who are already logged in."""
        next_url = request.GET.get('next', '')

        if not RegistrationProfile.objects.filter(user=request.user).exists():
            reply = HttpMetaRedirect('/myesp/profile')
        elif next_url in mask_locations:
            reply = mask_redirect(request.user, next_url)
        elif next_url:
            reply = HttpMetaRedirect(next_url)
        else:
            reply = HttpMetaRedirect('/')

        reply._new_user = request.user
        reply.no_set_cookies = False
        return reply

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add context for wrong username/password feedback
        if 'form' in context and not context['form'].is_valid():
            username = self.request.POST.get('username', '')
            if username:
                if ESPUser.objects.filter(username=username).exists():
                    context['wrong_pw'] = True
                else:
                    context['wrong_user'] = True
        if not self.request.GET:
            context['initiated_login'] = True
        return context

    def form_valid(self, form):
        """Handle successful login with user forwarding and profile checks."""
        user = form.get_user()
        old_username = user.username

        # Check for user forwarders
        user, forwarded = UserForwarder.follow(user)

        # Log in the (possibly forwarded) user
        login(self.request, user)

        if forwarded:
            # Display duplicate account warning
            if not RegistrationProfile.objects.filter(user=user).exists():
                next_uri = '/myesp/profile'
            else:
                next_uri = self.get_success_url()

            context = {
                'request': self.request,
                'old_username': old_username,
                'next_uri': next_uri,
                'next_title': next_uri if next_uri != '/' else 'the home page',
            }
            return render_to_response(
                'users/login_duplicate_warning.html',
                self.request,
                context
            )

        # Handle profile check and mask redirects
        next_url = self.get_success_url()

        if not RegistrationProfile.objects.filter(user=user).exists():
            reply = HttpMetaRedirect('/myesp/profile')
        elif next_url in mask_locations:
            reply = mask_redirect(user, next_url)
        else:
            # form_valid() is only called on successful authentication, so we
            # are always on the success path here — no need to check status_code.
            reply = HttpMetaRedirect(next_url)

        reply._new_user = user
        reply.no_set_cookies = False
        return reply

def signout(request):
    """ This view merges Django's logout view with our own "Goodbye" message. """
    logout(request)
    #   Tag the (now anonymous) user object so our middleware knows to delete cookies
    request._cached_user = request.user

    redirect_path = request.GET.get('redirect')
    if redirect_path:
        return HttpResponseRedirect(redirect_path)

    return render_to_response('registration/logged_out.html', request, {})


def signed_out_message(request):
    """ If the user is indeed logged out, show them a "Goodbye" message. """
    if request.user.is_authenticated:
        return HttpResponseRedirect('/')

    return render_to_response('registration/logged_out.html', request, {})


@login_required
def disable_account(request):

    curUser = request.user

    if 'enable' in request.GET:
        curUser.is_active = True
        curUser.save()
    elif 'disable' in request.GET:
        curUser.is_active = False
        curUser.save()

    other_users = ESPUser.objects.filter(email=curUser.email).exclude(id=curUser.id)

    context = {
            'user': curUser,
            'other_users': other_users,
            # Right now, we only deactivate the other users with the same email
            # address if we are using mailman.
            'will_deactivate_others': curUser.is_active and other_users and settings.USE_MAILMAN,
    }

    return render_to_response('users/disable_account.html', request, context)

# modified from here: https://www.grokcode.com/819/one-click-unsubscribes-for-django-apps/
def unsubscribe(request, username, token, oneclick = False):
    """
    User is immediately unsubscribed if they are logged in as username, or
    if they came from an unexpired unsubscribe link. Otherwise, they are
    redirected to the login page and unsubscribed as soon as they log in.
    """

    # render our own error message if the username doesn't match
    users = ESPUser.objects.filter(username=username)
    if users.exists():
        users_active = users.filter(is_active=True)
        if users_active.exists():
            user = users_active[0]
        else:
            raise ESPError("User " + users[0].username + " is already unsubscribed.")
    else:
        raise ESPError("No user matching that unsubscribe request.")

    # if POSTing, they clicked the confirm button
    # if oneclick=True, then they came here from an email client
    if request.POST.get("List-Unsubscribe") == "One-Click" or oneclick == True:
        # "unsubscribe" them (deactivate their account)
        user.is_active = False
        user.save()
        return render_to_response('users/unsubscribe.html', request, context = {'user': user, 'deactivated': True})

    # otherwise show them a confirmation button
    # if they are logged into the correct account or the token is valid
    if ( (request.user.is_authenticated and request.user == user) or user.check_token(token)):
        return render_to_response('users/unsubscribe.html', request, context = {'user': user})
    # if they are logged into a different account
    # tell them to log out and try again
    elif request.user.is_authenticated and request.user != user:
        raise ESPError("You are logged into a different account than the one you are trying to unsubscribe. Please log out and try your request again.")
    # otherwise they will need to log in (or find a more recent link)
    # so show the login page (with a custom alert message)
    else:
        next_url = reverse('unsubscribe', kwargs={'username': username, 'token': token,})
        return HttpResponseRedirect('%s?next=%s' % (reverse('login'), next_url))

# have an email client (etc) POST to this view to process a
# "oneclick" unsubscribe
@csrf_exempt
def unsubscribe_oneclick(request, username, token):
    if request.POST.get("List-Unsubscribe") == "One-Click":
        return unsubscribe(request, username, token, oneclick = True)
    raise ESPError("Invalid oneclick data.")

@admin_required
def morph_into_user(request):
    morph_user = ESPUser.objects.get(id=request.GET['morph_user'])
    try:
        onsite = Program.objects.get(id=request.GET['onsite'])
    except (KeyError, ValueError, Program.DoesNotExist):
        onsite = None
    request.user.switch_to_user(request,
                                morph_user,
                                '/manage/userview?username=' + morph_user.username,
                                'User Search for '+morph_user.name(),
                                onsite is not None)

    if onsite is not None:
        return HttpResponseRedirect('/learn/%s/studentreg' % onsite.getUrlBase())
    else:
        return HttpResponseRedirect('/')

class LoginHelpView(DefaultQSDView):
    template_name = "users/loginhelp.html"
