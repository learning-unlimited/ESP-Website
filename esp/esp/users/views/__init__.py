from esp.users.views.usersearch import *
from esp.users.views.registration import *
from esp.users.views.password_reset import *
from esp.users.views.emailpref import *
from esp.users.models import ESPUser

from django.http import HttpResponseRedirect, HttpResponse
from esp.web.util.main import render_to_response
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.views import login
from django.contrib.auth.decorators import login_required

from esp.tagdict.models import Tag
from esp.users.models.forwarder import UserForwarder

def filter_username(username, password):
    #   Allow login by e-mail address if so specified
    if username and '@' in username and Tag.getTag('login_by_email'):
        accounts = User.objects.filter(email = username)
        matches = []
        for u in accounts:
            if u.check_password(password):
                matches.append(u)
        if len(matches) > 0:
            username = matches[0].username
            
    return username

def login_checked(request, *args, **kwargs):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')

    reply = login(request, *args, **kwargs)

    # Check for user forwarders
    if request.user.is_authenticated():
        old_username = request.user.username
        user, forwarded = UserForwarder.follow(request.user)
        if forwarded:
            auth_logout(request)
            auth_login(request, user)
            # Try to display a friendly error message
            next_uri = reply.get('Location', '').strip()
            if next_uri:
                context = {
                    'request': request,
                    'old_username': old_username,
                    'next_uri': next_uri,
                    'next_title': next_uri,
                }
                if next_uri == '/':
                    context['next_title'] = 'the home page'
                return render_to_response('users/login_duplicate_warning.html', request, request.get_node('Q/Web/myesp'), context)

    if reply.get('Location', '') == '/':
        # We're getting redirected to the homepage.
        # Let's try to do something smarter.
        request.user = ESPUser(request.user)
        if request.user.isTeacher():
            return HttpResponseRedirect("/teach/index.html")
        else:
            return HttpResponseRedirect("/learn/index.html")

    return reply

def ajax_login(request, *args, **kwargs):
    import simplejson as json
    from django.contrib.auth import authenticate
    from django.template.loader import render_to_string

    username = None
    password = None
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

    username = filter_username(username, password)

    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            result_str = 'Login successful'
            user, forwarded = UserForwarder.follow(user)
            if forwarded:
                result_str = 'Logged in as "%s" ("%s" is marked as a duplicate account)' % (user.username, username)
            auth_login(request, user)
        else:
            result_str = 'Account disabled'
    else:
        result_str = 'Invalid username or password'
        
    request.user = ESPUser(user)
    content = render_to_string('users/loginbox_content.html', {'request': request, 'login_result': result_str})
    
    return HttpResponse(json.dumps({'loginbox_html': content}))

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
