from esp.users.views.usersearch import *
from esp.users.views.registration import *
from esp.users.views.password_reset import *

from django.http import HttpResponseRedirect
from esp.web.util.main import render_to_response
from django.contrib.auth.views import login
from django.contrib.auth.decorators import login_required

def login_checked(request, *args, **kwargs):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')

    return login(request, *args, **kwargs)


def signed_out_message(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')

    return render_to_response('registration/logged_out.html',
                              request, request.get_node('Q/Web/myesp'),
                              {})
                              
@login_required
def disable_account(request):
    
    curUser = request.user
    
    if 'enable' in request.GET:
        curUser.is_active = True
        curUser.save()
    elif 'disable' in request.GET:
        curUser.is_active = False
        curUser.save()
        
    context = {'user': curUser}
        
    return render_to_response('users/disable_account.html', request, request.get_node('Q/Web/myesp'), context)
