
from esp.users.forms.password_reset import PasswordResetForm,NewPasswordSetForm
from django.contrib.auth.models import User
from django.template import loader
from django.http import HttpResponseRedirect
from django.db.models.query import Q
from esp.users.models import PersistentQueryFilter, ESPUser, PasswordRecoveryTicket
from esp.web.util.main import render_to_response
from esp.users.decorators import anonymous_only
from django.contrib.auth import authenticate, login

__all__ = ['initial_passwd_request','email_passwd_followup','email_passwd_cancel']

@anonymous_only()
def initial_passwd_request(request, success=None):
    """
    This view represents the initial request
    to have the password reset.

    Upon successful completion of this view,
    the user will be emailed at their account.
    """

    if success:
        return render_to_response('users/recovery_request_success.html',
                                  request, request.get_node('Q/Web/myesp'),{})
                                  

    if request.method == 'POST':
        form = PasswordResetForm(request.POST)

        if form.is_valid():
            
            username = form.cleaned_data['username']
            if username != '':
                users = User.objects.filter(username = username)
            else:
                users = User.objects.filter(email__iexact = form.cleaned_data['email'])

            for user in users:
                ESPUser(user).recoverPassword()

            return HttpResponseRedirect('%ssuccess/' % request.path)


    else:
        form = PasswordResetForm()

    return render_to_response('users/recovery_request.html',request,
                              request.get_node('Q/Web/myesp'),
                              {'form':form})


def email_passwd_followup(request,success=None):
    """ Allow users to reset their password, given a recovery code. """

    if success:
        return render_to_response('users/recovery_finished.html',
                                  request, request.get_node('Q/Web/myesp'),{})
    try:
        code = request.GET['code']
    except KeyError:
        code = request.POST.get('code','')

    ticket = PasswordRecoveryTicket.objects.filter(recover_key=code)[:1]
    if len(ticket) == 0 or not ticket[0].is_valid():
        return render_to_response('users/recovery_invalid_code.html',
                                  request,request.get_node('Q/Web/myesp'),{})
    ticket = ticket[0]

    if request.method == 'POST':
        form = NewPasswordSetForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            changed = ticket.change_password(username, password)

            if changed:
                auth_user = authenticate(username = form.cleaned_data['username'],
                                         password = form.cleaned_data['password'])
                login(request, auth_user)
                return HttpResponseRedirect('%ssuccess/' % request.path)
            else:
                return render_to_response('users/recovery_invalid_code.html',
                                  request,request.get_node('Q/Web/myesp'),{})

    else:
        form = NewPasswordSetForm(initial={'code':code})

    return render_to_response('users/recovery_email.html', request,
                              request.get_node('Q/Web/myesp'),
                              {'form':form})

def email_passwd_cancel(request,success=None):
    """ Allow users to cancel a mis-assigned recovery code. """

    if success:
        return render_to_response('users/recovery_finished.html',
                                  request, request.get_node('Q/Web/myesp'),{})
    try:
        code = request.GET['code']
    except KeyError:
        code = request.POST.get('code','')

    ticket = PasswordRecoveryTicket.objects.filter(recover_key=code)[:1]
    if len(ticket) == 0 or not ticket[0].is_valid():
        return render_to_response('users/recovery_invalid_code.html',
                                  request,request.get_node('Q/Web/myesp'),{})
    ticket = ticket[0]
    ticket.cancel()

    return render_to_response('users/recovery_cancelled.html',
                request, request.get_node('Q/Web/myesp'),{})
