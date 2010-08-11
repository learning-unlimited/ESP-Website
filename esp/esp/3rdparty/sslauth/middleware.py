from django.contrib.auth import authenticate, login, get_user
from django.contrib.auth.models import AnonymousUser
from django.conf import settings

from util import SSLInfo, settings_get

class SSLAuthMiddleware(object):
    """
    attempts to find a valid user based on the client certificate info
    """
    def process_request(self, request):
        if hasattr(request, "user") and request.user.is_authenticated():
            return
        
        USE_COOKIE = settings_get('SSLAUTH_USE_COOKIE')
        
        if USE_COOKIE:
            request.user = get_user(request)
            if request.user.is_authenticated():
                return

        ssl_info  = SSLInfo(request)
        user = authenticate(ssl_info=ssl_info) or AnonymousUser()
        
        if not user.is_authenticated() and ssl_info.verify and settings_get('SSLAUTH_CREATE_USER'):
            from backends import SSLAuthBackend
            if SSLAuthBackend().create_user(ssl_info):
                user = authenticate(ssl_info=ssl_info) or AnonymousUser()

        if user.is_authenticated() and USE_COOKIE:
            login(request, user)
        else:
            request.user = user
