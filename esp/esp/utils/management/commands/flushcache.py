from django.conf import settings
from django.core.cache import cache
from django.core.management.base import NoArgsCommand

import logging
logger = logging.getLogger(__name__)
import os

class Command(NoArgsCommand):
    """
    This clears the cache just like /manage/flushcache
    """
    def handle_noargs(self, **options):
        _cache = cache
        while hasattr(_cache, "_wrapped_cache"):
            _cache = _cache._wrapped_cache
        if hasattr(_cache, "clear"):
            _cache.clear()
