from django.conf import settings
from django.shortcuts import redirect
from django.db import connection
from django.core.cache import cache

# Middleware to enable/disable online debugging ("idebug").
#
# This is used as middleware twice! Once before anything happens, and once after session middleware.
#
# The first time lets us turn on debugging very early, before user authentication and sessions,
# so that we can begin record queries & cache hits as early as possible. This is only possible
# when debugging is activated using the 'debug' GET flag.
#
# The second time turns on debugging if the session has debugging activated. When activated this way,
# we miss the earliest queries, but capture the page-specific debug info.
#

class IDebug(object):
    def process_request(self, request):

        # Already enabled first time?
        if hasattr(request, 'idebug') and request.idebug:
            return None
           
        request.idebug = False

        # If we see 'idebug' in the GET string, start recording
        if 'idebug' in request.GET:
            request.idebug = True

        # idebug enabled in session?
        if hasattr(request, 'session') and 'idebug' in request.session and request.session['idebug']:
            request.idebug = True

        # Enable Recording
        if request.idebug:
            connection.idebug_on()
            if hasattr(cache, 'idebug_on'):
                cache.idebug_on()

        return None    


    def process_response(self, request, response):
        if hasattr(request, 'idebug') and request.idebug:
          if hasattr(cache, 'idebug_off'):
              cache.idebug_off()
          connection.idebug_off()
          request.idebug = False

        return response
