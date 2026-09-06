from django.conf import settings
from django.utils.cache import patch_cache_control
from django.utils.deprecation import MiddlewareMixin


class CacheControlMiddleware(MiddlewareMixin):
    """
    Apply ``settings.DEFAULT_CACHE_CONTROL`` to responses that do not already
    define a ``Cache-Control`` header.

    The default policy (``private, no-cache``) keeps shared caches such as
    Varnish and other proxies from storing dynamic pages, and requires private
    caches such as browsers to revalidate before reusing them. Responses that
    set their own policy -- with ``@cache_control``, ``@never_cache`` or
    ``patch_cache_control()`` -- are left untouched, so views remain free to
    opt into real caching.

    This is registered near the start of ``MIDDLEWARE`` so that its response
    handling runs last (responses are processed in reverse order) and so sees
    headers set by every middleware further in.
    """

    def process_response(self, request, response):
        directives = getattr(settings, 'DEFAULT_CACHE_CONTROL', None)
        if directives and not response.has_header('Cache-Control'):
            patch_cache_control(response, **directives)
        return response
