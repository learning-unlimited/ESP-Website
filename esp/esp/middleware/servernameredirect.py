from django.conf import settings
from django.shortcuts import redirect


class ServerNameRedirect(object):

    def process_request(self, request):
        siteName = settings.SITE_INFO[1]

        # Don't redirect when we're running the test server
        if ('SERVER_NAME' not in request.META or
            'REQUEST_URI' not in request.META or
            request.META['SERVER_NAME'] in ('127.0.0.1', 'localhost')):
            return None

        serverName = request.META['SERVER_NAME']
        requestURI = request.META['REQUEST_URI']
        if serverName.lower() != siteName.lower():
            return redirect(('http://' if not request.is_secure() else 'https://') + siteName + requestURI)

        return None

    
