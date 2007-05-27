
from esp.users.forms.password_reset import PasswordResetForm,NewPasswordSetForm
from django.contrib.auth.models import User
from django.template import loader
from django.http import HttpResponseRedirect
from esp.db.models import Q
from esp.users.models import PersistentQueryFilter, ESPUser
from esp.web.util.main import render_to_response
from esp.users.decorators import anonymous_only
from django.contrib.auth import authenticate, login

__all__ = ['initial_passwd_request','email_passwd_followup']

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
            username = form.clean_data['username']
            user = User.objects.get(username = username)
            user = ESPUser(user)
            user.recoverPassword()
            return HttpResponseRedirect('%ssuccess/' % request.path)


    else:
        form = PasswordResetForm()

    return render_to_response('users/recovery_request.html',request,
                              request.get_node('Q/Web/myesp'),
                              {'form':form})


def email_passwd_followup(request,success=None):

    if success:
        return render_to_response('users/recovery_finished.html',
                                  request, request.get_node('Q/Web/myesp'),{})
    try:
        code = request.GET['code']
    except KeyError:
        code = request.POST.get('code','')

    if len(User.objects.filter(password = code).values('id')[:1]) == 0:
        return render_to_response('users/recovery_invalid_code.html',
                                  request,request.get_node('Q/Web/myesp'),{})

    if request.method == 'POST':
        form = NewPasswordSetForm(request.POST)

        if form.is_valid():
            user = User.objects.get(username = form.clean_data['username'])
            user.set_password(form.clean_data['password'])
            user.save()
            auth_user = authenticate(username = form.clean_data['username'],
                                     password = form.clean_data['password'])
            login(request, auth_user)
            return HttpResponseRedirect('%ssuccess/' % request.path)
                              
    else:
        form = NewPasswordSetForm(initial={'code':code})

    return render_to_response('users/recovery_email.html', request,
                              request.get_node('Q/Web/myesp'),
                              {'form':form})
