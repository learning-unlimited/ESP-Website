from django import http
from debug_toolbar.middleware import DebugToolbarMiddleware

class ESPDebugToolbarMiddleware(DebugToolbarMiddleware):
    """
    A subclass of DebugToolbarMiddleware that does some additional processing
    on the request before calling DebugToolbarMiddleware.process_request().

    Adds an additional optional setting,
    DEBUG_TOOLBAR_CONFIG['CONDITIONAL_PANELS'], which should be a function that
    accepts request as an argument. Whenever the ESPDebugToolbarMiddleware
    processes a request, it will call this function before calling
    DebugToolbarMiddleware.process_request(). This gives the opportunity to add
    conditional panels, based on the request, before
    DebugToolbarMiddleware.process_request() starts instantiating the panels.

    Any conditional panels triggered by a query string in the URL should use
    query string keys that start with 'debug_toolbar'.
    """
    def process_request(self, request):
        from django.conf import settings
        DEBUG_TOOLBAR_CONFIG = getattr(settings, 'DEBUG_TOOLBAR_CONFIG', {})
        CONDITIONAL_PANELS = DEBUG_TOOLBAR_CONFIG.get('CONDITIONAL_PANELS', None)
        if callable(CONDITIONAL_PANELS):
            CONDITIONAL_PANELS(request)

        if hasattr(request.META, 'HTTP_REFERER'):
            # Reconstruct the QueryDict from the query string of the referer
            # URL. Keep any that start with 'debug_toolbar'. That way, any
            # conditional debug_toolbar settings get carried over when
            # navigating around the site.
            if '?' in request.META.HTTP_REFERER:
                query = request.META.HTTP_REFERER.split('?',1)[1]
                query = http.QueryDict(query, encoding=settings.DEFAULT_CHARSET)
                for q in filter(lambda q: 'debug_toolbar' in q[0], query.items()):
                    request.GET[q[0]] = q[1]
        super(ESPDebugToolbarMiddleware, self).process_request(request)

    @staticmethod
    def custom_show_toolbar(request):
        """
        Default implementation of DEBUG_TOOLBAR_CONFIG['SHOW_TOOLBAR_CALLBACK'].
        """
        from django.conf import settings

        # Always show toolbar when debugging,
        # or when given a special GET param
        # while logged in as an admin.
        # NOTE (jmoldow): The ordering is intentional. It takes advantage of
        # short-circuiting to only call request.user.isAdmin() when necessary,
        # because calling request.user.isAdmin() sets Vary:Cookie and prevents
        # proxy caching. See Github issue #739.
        return settings.DEBUG or \
                (request.GET.get('debug_toolbar', None) == 't' and request.user.isAdmin())

