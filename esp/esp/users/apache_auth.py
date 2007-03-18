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
    from esp.datatree.models import get_lowest_parent

    
    request=AccessHandler()(req)
    if request.user.is_authenticated():
        qsc  = get_lowest_parent('Q/Static/' + uri.strip('/'))
        verb = get_lowest_parent(permission_verb_name)
        if UserBit.UserHasPerms(request.user, qsc, verb):
            return apache.OK

    return apache.HTTP_UNAUTHORIZED
