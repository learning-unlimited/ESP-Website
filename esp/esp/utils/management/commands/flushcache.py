from django.core.cache import cache
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    """
    This clears the cache just like /manage/flushcache
    """
    def handle(self, *args, **options):
        _cache = cache
        while hasattr(_cache, "_wrapped_cache"):
            _cache = _cache._wrapped_cache
        if hasattr(_cache, "clear"):
            _cache.clear()
