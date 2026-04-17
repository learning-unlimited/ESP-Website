from django.utils.cache import patch_cache_control
from django.utils.deprecation import MiddlewareMixin


class CacheControlMiddleware(MiddlewareMixin):
    """
    Apply a default Cache-Control policy to responses that do not already
    define one, using ``patch_cache_control`` with ``private`` and
    ``no_cache``.

    This prevents shared caches such as intermediate proxies from storing
    the response, and requires private caches such as browsers to revalidate
    before reusing it. Views may still override behavior (for example with
    ``@cache_control`` or ``patch_cache_control`` on the response).
    """

    def process_response(self, request, response):
        if not response.has_header('Cache-Control'):
            patch_cache_control(response, private=True, no_cache=True)
        return response
