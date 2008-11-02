import os
from mod_python import apache
from django.core.handlers.base import BaseHandler
from django.core.handlers.modpython import ModPythonRequest

class AccessHandler(BaseHandler):
    def __call__(self, req):
        from django.conf import settings
        # set up middleware
        if self._request_middleware is None:
            self.load_middleware()
	# populate the request object
	request = ModPythonRequest(req)
	# and apply the middleware to it
	# actually only session and auth middleware would be needed here
	for middleware_method in self._request_middleware:
		middleware_method(request)
	return request

def accesshandler(req):
    os.environ.update(req.subprocess_env)
    
    uri = req.subprocess_env['REQUEST_URI']
        
    # check for PythonOptions
    _str_to_bool = lambda s: s.lower() in ('1', 'true', 'on', 'yes')

    options = req.get_options()
    permission_verb_name = options.get('ESPPermissionName', 'V/Flags/Public')
    settings_module = options.get('DJANGO_SETTINGS_MODULE', None)
    
    
    if settings_module:
        os.environ['DJANGO_SETTINGS_MODULE'] = settings_module

    from esp.users.models import UserBit
    from esp.datatree.models import *

    
    request=AccessHandler()(req)
    if request.user.is_authenticated():
        qsc  = get_lowest_parent('Q/Static/' + uri.strip('/'))
        verb = get_lowest_parent(permission_verb_name)
        if UserBit.UserHasPerms(request.user, qsc, verb):
            return apache.OK

    return apache.HTTP_UNAUTHORIZED


def authenhandler(req, **kwargs):
    """
    Authentication handler that checks against Django's auth database.
    """

    # mod_python fakes the environ, and thus doesn't process SetEnv.  This fixes
    # that so that the following import works
    os.environ.update(req.subprocess_env)
    uri = req.subprocess_env['REQUEST_URI']

    # check for PythonOptions
    _str_to_bool = lambda s: s.lower() in ('1', 'true', 'on', 'yes')

    options = req.get_options()
    permission_verb_name = options.get('ESPPermissionName', 'V/Flags/Public')
    settings_module = options.get('DJANGO_SETTINGS_MODULE', None)
    
    if settings_module:
        os.environ['DJANGO_SETTINGS_MODULE'] = settings_module
            
    from esp.users.models import UserBit
    from esp.datatree.models import *



    from django.contrib.auth.models import User
    from django import db
    db.reset_queries()

    # check that the username is valid
    kwargs = {'username': req.user, 'is_active': True}

    try:
        try:
            user = User.objects.get(**kwargs)
        except User.DoesNotExist:
            return apache.HTTP_UNAUTHORIZED
    
        # check the password and any permission given
        if user.check_password(req.get_basic_auth_pw()):
            if user.is_authenticated():
                qsc  = get_lowest_parent('Q/Static/' + uri.strip('/'))
                verb = get_lowest_parent(permission_verb_name)
                if UserBit.UserHasPerms(user, qsc, verb):
                    return apache.OK
                else:
                    return apache.HTTP_UNAUTHORIZED
        else:
            return apache.HTTP_UNAUTHORIZED
    finally:
        db.connection.close()
