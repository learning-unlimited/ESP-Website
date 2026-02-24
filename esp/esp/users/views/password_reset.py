from esp.users.forms.password_reset import PasswordResetForm
from django.contrib.auth.views import PasswordResetConfirmView
from django.http import HttpResponseRedirect
from esp.users.models import ESPUser
from esp.utils.web import render_to_response
from esp.users.decorators import anonymous_only
from django.contrib.auth import authenticate, login

__all__ = ['initial_passwd_request', 'password_reset_confirm', 'password_reset_done']

@anonymous_only()
def initial_passwd_request(request, success=None):
    """
    This view represents the initial request
    to have the password reset.

    Upon successful completion of this view,
    the user will be emailed at their account with a
    password reset link that uses Django's built-in
    token generator (no plaintext token is stored in the DB).
    """

    if success:
        return render_to_response('users/recovery_request_success.html',
                                  request, {})


    if request.method == 'POST':
        form = PasswordResetForm(request.POST)

        if form.is_valid():

            username = form.cleaned_data['username']
            if username != '':
                users = ESPUser.objects.filter(username = username)
            else:
                users = ESPUser.objects.filter(email__iexact = form.cleaned_data['email'])

            for user in users:
                user.recoverPassword()

            return HttpResponseRedirect('/%s/success/' % request.path.strip('/'))


    else:
        form = PasswordResetForm()

    return render_to_response('users/recovery_request.html', request,
                              {'form':form})


class ESPPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Wraps Django's PasswordResetConfirmView to use ESP's templates
    and auto-login the user after password reset.

    Django's PasswordResetConfirmView validates the token using
    PasswordResetTokenGenerator which computes an HMAC from the user's
    pk, password hash, and last_login timestamp.  No token is ever
    stored in the database, so a database leak cannot expose valid
    reset tokens.
    """
    template_name = 'users/recovery_email.html'
    success_url = '/myesp/resetpassword/done/'

    def form_valid(self, form):
        user = form.save()
        # Activate the user (in case they were inactive)
        if not user.is_active:
            user.is_active = True
            user.save()
        # Auto-login the user after successful password reset
        auth_user = authenticate(
            username=user.username,
            password=form.cleaned_data['new_password1']
        )
        if auth_user is not None:
            login(self.request, auth_user)
        return HttpResponseRedirect(self.success_url)


password_reset_confirm = ESPPasswordResetConfirmView.as_view()


def password_reset_done(request):
    """Show the password reset complete page."""
    return render_to_response('users/recovery_finished.html', request, {})
