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

        # The debug toolbar can be enabled or disabled on the page with the
        # 'debug_toolbar' GET param.  If present, the value of this param is
        # stored in the session, so that the toolbar stays enabled or disabled
        # while navigating.
        param = request.GET.get('debug_toolbar')
        if param is not None:
            request.session['debug_toolbar'] = param

        super(ESPDebugToolbarMiddleware, self).process_request(request)

    @staticmethod
    def custom_show_toolbar(request):
        """
        Default implementation of DEBUG_TOOLBAR_CONFIG['SHOW_TOOLBAR_CALLBACK'].
        """
        from django.conf import settings

        # settings.DEBUG_TOOLBAR must be True to enable the toolbar.
        # Assuming this is set:
        #   - Always show toolbar when debugging,
        #     unless request.session['debug_toolbar'] == 'f'.
        #   - Show toolbar when request.session['debug_toolbar'] == 't'
        #     while logged in as an admin.
        # NOTE (jmoldow): The ordering is intentional. It takes advantage of
        # short-circuiting to only call request.user.isAdmin() when necessary,
        # because calling request.user.isAdmin() sets Vary:Cookie and prevents
        # proxy caching. See Github issue #739.
        return (not request.is_ajax()) and settings.DEBUG_TOOLBAR and \
                ((settings.DEBUG and not request.session.get('debug_toolbar') == 'f') or \
                (request.session.get('debug_toolbar') == 't' and request.user.isAdmin()))

