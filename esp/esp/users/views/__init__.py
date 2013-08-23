from esp.users.views.usersearch import *
from esp.users.views.registration import *
from esp.users.views.password_reset import *
from esp.users.views.emailpref import *
from esp.users.views.make_admin import *
from esp.users.models import ESPUser

from esp.program.modules.base import needs_admin

from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from esp.web.util.main import render_to_response
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.views import login
from django.contrib.auth.decorators import login_required

from esp.tagdict.models import Tag
from esp.users.models.forwarder import UserForwarder

def filter_username(username, password):
    #   Allow login by e-mail address if so specified
    if username and '@' in username and Tag.getTag('login_by_email'):
        accounts = ESPUser.objects.filter(email = username)
        matches = []
        for u in accounts:
            if u.check_password(password):
                matches.append(u)
        if len(matches) > 0:
            username = matches[0].username
            
    return username

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

def login_checked(request, *args, **kwargs):
    if request.user.is_authenticated():
        #   Set response cookies in case of repeat login
        reply = HttpMetaRedirect('/')
        reply._new_user = request.user
        reply.no_set_cookies = False
        return reply

    reply = login(request, *args, **kwargs)

    # Check for user forwarders
    if request.user.is_authenticated():
        old_username = request.user.username
        user, forwarded = UserForwarder.follow(ESPUser(request.user))
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
                return render_to_response('users/login_duplicate_warning.html', request, context)

    mask_locations = ['/', '/myesp/signout/', '/admin/logout/']
    if reply.get('Location', '') in mask_locations:
        # We're getting redirected to somewhere undesirable.
        # Let's try to do something smarter.
        request.user = ESPUser(request.user)
        if request.user.isTeacher():
            reply = HttpMetaRedirect("/teach/index.html")
        else:
            reply = HttpMetaRedirect("/learn/index.html")
    elif reply.status_code == 302:
        #   Even if the redirect was going to a reasonable place, we need to
        #   turn it into a 200 META redirect in order to set the cookies properly.
        request.user = ESPUser(request.user)
        reply = HttpMetaRedirect(reply.get('Location', ''))

    #   Stick the user in the response in order to set cookies if necessary
    reply._new_user = request.user
    reply.no_set_cookies = False

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
            user, forwarded = UserForwarder.follow(ESPUser(user))
            if forwarded:
                result_str = 'Logged in as "%s" ("%s" is marked as a duplicate account)' % (user.username, username)
            auth_login(request, user)
        else:
            result_str = 'Account disabled'
    else:
        result_str = 'Invalid username or password'
        
    request.user = ESPUser(user)
    content = render_to_string('users/loginbox_content.html', RequestContext(request, {'request': request, 'login_result': result_str}))
    result_dict = {'loginbox_html': content}
    
    if request.user.isAdministrator():
        admin_home_url = Tag.getTag('admin_home_page')
        if admin_home_url:
            result_dict['script'] = render_to_string('users/loginbox_redirect.js', {'target': admin_home_url})

    return HttpResponse(json.dumps(result_dict))

def signout(request):
    """ This view merges Django's logout view with our own "Goodbye" message. """
    auth_logout(request)
    
    #   Tag the (now anonymous) user object so our middleware knows to delete cookies
    request._cached_user = request.user
    
    return render_to_response('registration/logged_out.html', request, {})

def signed_out_message(request):
    """ If the user is indeed logged out, show them a "Goodbye" message. """
    if request.user.is_authenticated():
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
        
    context = {'user': curUser}
        
    return render_to_response('users/disable_account.html', request, context)

def morph_into_user(request):
    morph_user = ESPUser.objects.get(id=request.GET[u'morph_user'])
    request.user.switch_to_user(request,
                                morph_user,
                                '/manage/userview?username=' + morph_user.username,
                                'User Search for '+morph_user.name(),
                                False)

    return HttpResponseRedirect('/')
