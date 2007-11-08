from django.core.cache import cache

__all__ = ['GenericCacheHelper']

class GenericCacheHelper(object):
    """
    Allows you to shortcut the userbit caching mechanism::

        value = UserBit.objects.cache(user)['key']
        UserBit.objects.cache(user)['key'] = 'new value'
    """

    # 1-hour caching
    cache_time = 3600
    def __init__(self, class_):
        self.class_ = class_

    def get_key_for_item(self):
        return self.__class__.get_key(self.class_)

    def update(self):
        """ Purges all userbit-related cache. """
        cache.delete(self.get_key_for_item())

    def __getitem__(self, key):
        cache_dict = cache.get(self.get_key_for_item())
        if cache_dict is None:
            return None
        if key in cache_dict:
            return cache_dict[key]
        else:
            return None

    def __setitem__(self, key, value):
        global_key = self.get_key_for_item()
        cache_dict = cache.get(global_key)
        if cache_dict is None:
            cache_dict = {}
        cache_dict[key] = value

        cache.set(global_key, cache_dict, self.cache_time)

    def __delitem__(self, key):
        global_key = self.get_key_for_item()
        cache_dict = cache.get(global_key)
        if cache_dict is None: return

        if key in cache_dict: del cache_dict[key]

        cache.set(global_key, cache_dict, self.cache_time)

