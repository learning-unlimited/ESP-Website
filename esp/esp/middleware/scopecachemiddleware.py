from django.conf import settings
from django.core.cache import cache

def prefix_cache_object(cache_prefix, cache_obj):
    if not cache_prefix:
        return

    cache_class = cache_obj.__class__

    if getattr(cache_class, '_PREFIXED', False):
        # If we're already prefixed, return.
        return

    def prefix_key(method):
        def _new_func(self, key, *args, **kwargs):
            if kwargs.get('use_global_namespace', False):
                return method(self, key, *args, **kwargs)
            return method(self, cache_prefix + key,
                          *args, **kwargs)

        _new_func.__doc__ = method.__doc__
        _new_func.__name__ = method.__name__
        return _new_func

    def prefix_many(method):
        def _new_func(self, keys, *args, **kwargs):
            if kwargs.get('use_global_namespace', False):
                return method(self, keys, *args, **kwargs)
            keys = [cache_prefix + key for key in keys]
            return method(self, keys, *args, **kwargs)

        _new_func.__doc__ = method.__doc__
        _new_func.__name__ = method.__name__
        return _new_func

    cache_class._PREFIXED = True
    cache_class.get = prefix_key(cache_class.get)
    cache_class.set = prefix_key(cache_class.set)
    cache_class.delete = prefix_key(cache_class.delete)
    cache_class.has_key = prefix_key(cache_class.has_key)
    cache_class.get_many = prefix_many(cache_class.get_many)


class ScopeCacheMiddleware(object):
    """ Middleware which adds scoping to all of the
    cache methods.
    If settings.CACHE_PREFIX is defined, replace
    all django.core.cache.cache methods with new
    methods that automatically prefix the keys
    appropriately.

    Warning: May not work with psyco!
    """
    def process_request(self, request):
        if getattr(settings, 'CACHE_PREFIX', False):
            prefix_cache_object(settings.CACHE_PREFIX, cache)
        return
