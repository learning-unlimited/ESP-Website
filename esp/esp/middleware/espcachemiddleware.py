from django.conf import settings
from django.core.cache import cache
from django.utils.cache import get_cache_key, learn_cache_key, patch_response_headers

NO_CACHE_IPS = ('127.0.0.1',)

class CacheMiddleware(object):
    """
    This cache middleware behaves much like Django's cache middleware
    with two major exceptions:
    
      # Requests from NO_CACHE_IPS will create caches, instead of using them.
      # If 'no-cache' is inside the Cache-Control response header, it won't
        cache the page.
    
    """

    def __init__(self, cache_timeout=None, key_prefix=None, cache_anonymous_only=None):
        self.cache_timeout = cache_timeout
        if cache_timeout is None:
            self.cache_timeout = settings.CACHE_MIDDLEWARE_SECONDS
        self.key_prefix = key_prefix
        if key_prefix is None:
            self.key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        if cache_anonymous_only is None:
            self.cache_anonymous_only = getattr(settings, 'CACHE_MIDDLEWARE_ANONYMOUS_ONLY', False)
        else:
            self.cache_anonymous_only = cache_anonymous_only
            
        self._no_cache_ips = getattr(settings, 'NO_CACHE_IPS', NO_CACHE_IPS)
        

    def process_request(self, request):
        "Checks whether the page is already cached and returns the cached version if available."
        if self.cache_anonymous_only:
            assert hasattr(request, 'user'), "The Django cache middleware with CACHE_MIDDLEWARE_ANONYMOUS_ONLY=True requires authentication middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.auth.middleware.AuthenticationMiddleware' before the CacheMiddleware."

        if not request.method in ('GET', 'HEAD') or request.GET:
            request._cache_update_cache = False
            return None # Don't bother checking the cache.

        if self.cache_anonymous_only and request.user.is_authenticated():
            request._cache_update_cache = False
            return None # Don't cache requests from authenticated users.

        if request.META['REMOTE_ADDR'] in self._no_cache_ips:
            request._cache_update_cache = True
            return None # Store cache, but do not use it since this is a NO cache IP

        cache_key = get_cache_key(request, self.key_prefix)
        if cache_key is None:
            request._cache_update_cache = True
            return None # No cache information available, need to rebuild.

        response = cache.get(cache_key, None)
        if response is None:
            request._cache_update_cache = True
            return None # No cache information available, need to rebuild.


        request._cache_update_cache = False
        return response

    def process_response(self, request, response):
        "Sets the cache, if needed."
        if not hasattr(request, '_cache_update_cache') or not request._cache_update_cache:
            # We don't need to update the cache, just return.
            return response

        try:
            if 'no-cache' in response['Cache-Control']:
                # Told not to cache, just return
                return response
        except KeyError:
            pass
        
        if request.method != 'GET':
            # This is a stronger requirement than above. It is needed
            # because of interactions between this middleware and the
            # HTTPMiddleware, which throws the body of a HEAD-request
            # away before this middleware gets a chance to cache it.
            return response
        if not response.status_code == 200:
            return response
        patch_response_headers(response, self.cache_timeout)
        cache_key = learn_cache_key(request, response, self.cache_timeout, self.key_prefix)
        cache.set(cache_key, response, self.cache_timeout)
        return response
