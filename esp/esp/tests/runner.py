""" Test runner that keeps tests out of other processes' cache entries.

Tests share memcached with the dev server, which uses the same cache
prefix, and with each other's worker processes under --parallel.  Each run,
and each parallel worker, starts on its own random cache prefix.
(CacheFlushTestCase also switches prefix around every test.)

Parallel workers are forked from the main process after it has already
connected to memcached, so each also drops the inherited memcached client:
workers sharing one socket read each other's replies (errors like "error 16
from memcached_add: SUCCESS"), which breaks tests at random.
"""
from django.core.cache import caches
from django.test.runner import DiscoverRunner, ParallelTestSuite, _init_worker

from esp.tests.util import use_random_cache_prefix


def _drop_inherited_cache_clients():
    for cache in caches.all():
        # esp.utils.memcached_multikey.CacheClass wraps Django's PyLibMCCache,
        # which keeps its client in the _cache cached_property; removing it
        # makes the next use open a fresh connection.
        backend = getattr(cache, '_wrapped_cache', cache)
        backend.__dict__.pop('_cache', None)


def _init_worker_with_own_cache(counter):
    _init_worker(counter)
    _drop_inherited_cache_clients()
    use_random_cache_prefix()


class ESPParallelTestSuite(ParallelTestSuite):
    # Django calls this in each worker process as it starts.
    init_worker = _init_worker_with_own_cache


class ESPTestRunner(DiscoverRunner):
    parallel_test_suite = ESPParallelTestSuite

    def setup_test_environment(self, **kwargs):
        super(ESPTestRunner, self).setup_test_environment(**kwargs)
        use_random_cache_prefix()
