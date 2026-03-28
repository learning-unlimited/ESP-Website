from django.utils.deprecation import MiddlewareMixin

class CacheControlMiddleware(MiddlewareMixin):
    """
    Middleware that sets a default 'Cache-Control: private, no-cache'
    header on responses that do not explicitly define one.
    This ensures that dynamic pages are not cached by intermediate
    proxies or browsers, while allowing specific views to override
    this behavior (e.g. using @cache_control).
    """
    def process_response(self, request, response):
        if not response.has_header('Cache-Control'):
            response['Cache-Control'] = 'private, no-cache'
        return response
