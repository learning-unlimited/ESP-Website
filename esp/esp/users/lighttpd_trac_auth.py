#!/usr/bin/python

# Taken largely from Django snippets #1149 and #56

from __future__ import with_statement
import sys, os

# Add a custom Python path.
sys.path.insert(0, "/esp/web/mit/esp/")

# Switch to the directory of your project. (Optional.)
os.chdir("/esp/web/mit/esp/")

# Set the DJANGO_SETTINGS_MODULE environment variable.
os.environ['DJANGO_SETTINGS_MODULE'] = "esp.settings"

def handler(environ, start_response):
    if environ['REQUEST_URI'][:11] == '/code/login':
        def unauthorized():
            start_response( '401 Authorization Required',
                [ ('WWW-Authenticate', 'Basic realm="ESP Project"'),
                  ('Content-Type', 'text/html') ] )
            return '<html><head><title>401 Authorization Required</title></head><body><h1>401 Authorization Required</h1></body></html>'
        # Decode the input
        try:
            # Require basic authentication
            method, auth = environ['HTTP_AUTHORIZATION'].split(' ', 1)
            if method.lower() != 'basic':
                return unauthorized()
            username, password = auth.strip().decode('base64').split(':')
        except: #(KeyError, ValueError, base64.binascii.Error)
            return unauthorized()
        # Check that the user exists
        try:
            from django.contrib.auth.models import User
            from esp.datatree.models import get_lowest_parent
            from esp.users.models import UserBit
            user = User.objects.get(username=username, is_active=True)
        except User.DoesNotExist:
            return unauthorized()
        # Check the password and any permission given
        if not ( user.check_password(password) and user.is_authenticated() ):
            return unauthorized()
        qsc  = get_lowest_parent('Q/Static/' + environ['REQUEST_URI'].strip('/'))
        verb = get_lowest_parent('V/Flags/Public')
        if not UserBit.UserHasPerms(user, qsc, verb):
            return unauthorized()
        # By now we've verified the user's login and permissions
        environ['REMOTE_USER'] = username
    # Eventually pass all requests to Trac
    from trac.web.main import dispatch_request
    return dispatch_request(environ, start_response)

if __name__ == '__main__':
    if len( sys.argv ) == 3:
        # Assume the arguments are a socket and a pidfile.
        from flup.server.fcgi_fork import WSGIServer
        from django.utils.daemonize import become_daemon
        become_daemon()
        with open( sys.argv[2], 'w' ) as pidfile:
            pidfile.write( '%d\n' % os.getpid() )
        WSGIServer(handler, bindAddress=sys.argv[1]).run()
    else:
        from flup.server.fcgi import WSGIServer
        WSGIServer(handler).run()
