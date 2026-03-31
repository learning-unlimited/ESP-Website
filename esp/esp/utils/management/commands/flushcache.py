from django.core.cache import cache
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    """
    This clears the cache just like /manage/flushcache
    """
    def handle(self, *args, **options):
        if hasattr(cache, "clear"):
            cache.clear()
