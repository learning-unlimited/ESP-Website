from django.conf import settings
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import login
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext

from esp.program.models import Program
from esp.tagdict.models import Tag
from esp.users.models import ESPUser, admin_required
from esp.users.models.forwarder import UserForwarder
from esp.users.views.make_admin import *
from esp.users.views.password_reset import *
from esp.users.views.registration import *
from esp.users.views.usersearch import *
from esp.utils.web import render_to_response


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

    if hasattr(reply, 'context_data'):
        if not request.GET:
            reply.context_data['initiated_login'] = True
        if request.POST and request.POST['username']:
            #if a user was entered and it's not in the database, the pw must be wrong
            if ESPUser.objects.filter(username=request.POST['username']).exists():
                reply.context_data['wrong_pw'] = True
            else:
                reply.context_data['wrong_user'] = True

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
                return render_to_response('users/login_duplicate_warning.html', request, context)

    mask_locations = ['/', '/myesp/signout', '/myesp/signout/', '/admin/logout/']
    if reply.get('Location', '') in mask_locations:
        # We're getting redirected to somewhere undesirable.
        # Let's try to do something smarter.
        admin_home_url = Tag.getTag('admin_home_page')
        if request.user.isAdmin() and admin_home_url:
            reply = HttpMetaRedirect(admin_home_url)
        elif request.user.isTeacher():
            reply = HttpMetaRedirect("/teach/index.html")
        else:
            reply = HttpMetaRedirect("/learn/index.html")
    elif reply.status_code == 302:
        #   Even if the redirect was going to a reasonable place, we need to
        #   turn it into a 200 META redirect in order to set the cookies properly.
        reply = HttpMetaRedirect(reply.get('Location', ''))

    #   Stick the user in the response in order to set cookies if necessary
    reply._new_user = request.user
    reply.no_set_cookies = False

    if request.user.is_authenticated():
        return reply
    else:
        return render_to_response("registration/login.html", reply._request, reply.context_data)

def signout(request):
    """ This view merges Django's logout view with our own "Goodbye" message. """
    auth_logout(request)
    #   Tag the (now anonymous) user object so our middleware knows to delete cookies
    request._cached_user = request.user

    redirect_path = request.GET.get('redirect')
    if redirect_path:
        return HttpResponseRedirect(redirect_path)

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

    other_users = ESPUser.objects.filter(email=curUser.email).exclude(id=curUser.id)

    context = {
            'user': curUser,
            'other_users': other_users,
            # Right now, we only deactivate the other users with the same email
            # address if we are using mailman.
            'will_deactivate_others': curUser.is_active and other_users and settings.USE_MAILMAN,
    }

    return render_to_response('users/disable_account.html', request, context)


@admin_required
def morph_into_user(request):
    morph_user = ESPUser.objects.get(id=request.GET[u'morph_user'])
    try:
        onsite = Program.objects.get(id=request.GET[u'onsite'])
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
