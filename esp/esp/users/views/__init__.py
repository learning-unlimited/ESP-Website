from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
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
    """
    A lightweight helper used throughout the login flow.

    Instead of returning a normal Django redirect response,
    this returns a small HTML page that performs a meta refresh.
    Historically this was used to work around certain cookie
    handling issues in older browsers.
    """
    response = HttpResponse()
    response.status = 200
    response.content = """
    <html><head>
    <meta http-equiv="refresh" content="0; url=%s">
    </head>
    <body>
    Thank you for logging in. Please click <a href="%s">here</a> if you are not redirected.
    </body>
    </html>
    """ % (location, location)
    return response


# Locations where we override redirects with smarter defaults
mask_locations = ['/', '/myesp/signout', '/myesp/signout/', '/admin/logout/']


def mask_redirect(user, next):
    """
    Redirect users to a more meaningful landing page depending
    on their role (admin, teacher, or student).
    """

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
    """
    Custom login view extending Django's default LoginView.

    This version includes:
    • Support for logging in using either username or email
    • Smart redirects based on user role
    • Handling of forwarded/merged accounts
    • Additional template context for login error messaging
    """

    template_name = 'registration/login.html'

    def render_to_response(self, context, **response_kwargs):
        """
        Render the login template using ESP's custom render helper.
        """
        response_kwargs.setdefault("content_type", self.content_type)
        return render_to_response(
            request=self.request,
            template=self.get_template_names(),
            context=context,
            **response_kwargs,
        )

    def get(self, request, *args, **kwargs):
        """
        If a logged-in user visits the login page,
        redirect them instead of showing the form again.
        """

        if request.user.is_authenticated:
            return self.handle_authenticated_user(request)

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Extend the login POST flow to support authentication
        using either username or email.

        If an email address is entered, we look up the matching
        user and transparently replace the POSTed username field.
        """

        if request.user.is_authenticated:
            return self.handle_authenticated_user(request)

        username_input = request.POST.get("username", "")

        # If the input looks like an email address, attempt lookup
        if "@" in username_input:
            try:
                user = ESPUser.objects.get(email__iexact=username_input)

                request.POST = request.POST.copy()
                request.POST["username"] = user.username

            except ESPUser.DoesNotExist:
                # Let the default authentication logic handle invalid users
                pass

        return super().post(request, *args, **kwargs)

    def handle_authenticated_user(self, request):
        """
        Determine where authenticated users should be redirected.
        """

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
        """
        Add helpful context variables to the template
        to show better login error messages.
        """

        context = super().get_context_data(**kwargs)

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
        """
        Handle successful authentication.
        """

        user = form.get_user()
        old_username = user.username

        # Follow any configured account forwarders
        user, forwarded = UserForwarder.follow(user)

        login(self.request, user)

        if forwarded:

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

        next_url = self.get_success_url()

        if not RegistrationProfile.objects.filter(user=user).exists():
            reply = HttpMetaRedirect('/myesp/profile')

        elif next_url in mask_locations:
            reply = mask_redirect(user, next_url)

        else:
            reply = HttpMetaRedirect(next_url)

        reply._new_user = user
        reply.no_set_cookies = False

        return reply


def signout(request):
    """
    Log out the current user and show the goodbye page.
    """

    logout(request)
    request._cached_user = request.user

    redirect_path = request.GET.get('redirect')

    if redirect_path:
        return HttpResponseRedirect(redirect_path)

    return render_to_response('registration/logged_out.html', request, {})


def signed_out_message(request):
    """
    Display the logout confirmation page.
    """

    if request.user.is_authenticated:
        return HttpResponseRedirect('/')

    return render_to_response('registration/logged_out.html', request, {})


@login_required
def disable_account(request):
    """
    Allow users to disable or re-enable their account.
    """

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
        'will_deactivate_others': curUser.is_active and other_users and settings.USE_MAILMAN,
    }

    return render_to_response('users/disable_account.html', request, context)


def unsubscribe(request, username, token, oneclick=False):
    """
    Process unsubscribe requests from email links or user actions.
    """

    users = ESPUser.objects.filter(username=username)

    if users.exists():
        users_active = users.filter(is_active=True)

        if users_active.exists():
            user = users_active[0]
        else:
            raise ESPError("User " + users[0].username + " is already unsubscribed.")

    else:
        raise ESPError("No user matching that unsubscribe request.")

    if request.POST.get("List-Unsubscribe") == "One-Click" or oneclick == True:

        user.is_active = False
        user.save()

        return render_to_response(
            'users/unsubscribe.html',
            request,
            context={'user': user, 'deactivated': True}
        )

    if ((request.user.is_authenticated and request.user == user) or user.check_token(token)):

        return render_to_response(
            'users/unsubscribe.html',
            request,
            context={'user': user}
        )

    elif request.user.is_authenticated and request.user != user:

        raise ESPError(
            "You are logged into a different account than the one you are trying to unsubscribe."
        )

    else:

        next_url = reverse(
            'unsubscribe',
            kwargs={'username': username, 'token': token}
        )

        return HttpResponseRedirect('%s?next=%s' % (reverse('login'), next_url))


@csrf_exempt
def unsubscribe_oneclick(request, username, token):
    """
    Endpoint used by email clients to trigger one-click unsubscribe.
    """

    if request.POST.get("List-Unsubscribe") == "One-Click":
        return unsubscribe(request, username, token, oneclick=True)

    raise ESPError("Invalid oneclick data.")


@admin_required
def morph_into_user(request):
    user_id = request.POST.get('morph_user')
    if not user_id:
        return HttpResponseBadRequest("Missing morph_user parameter.")
    try:
        morph_user = ESPUser.objects.get(id=user_id)
    except (ValueError, ESPUser.DoesNotExist):
        return HttpResponseBadRequest("Invalid morph_user parameter.")
    try:
        onsite = Program.objects.get(id=request.POST.get('onsite'))
    except (KeyError, ValueError, Program.DoesNotExist):
        onsite = None

    request.user.switch_to_user(
        request,
        morph_user,
        '/manage/userview?username=' + morph_user.username,
        'User Search for ' + morph_user.name(),
        onsite is not None
    )

    if onsite is not None:
        return HttpResponseRedirect('/learn/%s/studentreg' % onsite.getUrlBase())

    else:
        return HttpResponseRedirect('/')


class LoginHelpView(DefaultQSDView):
    """
    Simple informational page providing login help to users.
    """

    template_name = "users/loginhelp.html"