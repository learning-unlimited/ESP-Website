from esp.users.views.usersearch import *
from esp.users.views.registration import *
from esp.users.views.password_reset import *

from django.http import HttpResponseRedirect
from esp.web.util.main import render_to_response
from django.contrib.auth.views import login

def login_checked(request, *args, **kwargs):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')
    
    kwargs['template_name'] = 'users/login.html'
    return login(request, *args, **kwargs)


def signed_out_message(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')

    return render_to_response('registration/logged_out.html',
                              request, request.get_node('Q/Web/myesp'),
                              {})
