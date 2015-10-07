from django.apps import AppConfig

class CacheConfig(AppConfig):
    """ Makes sure all caches are inserted. Replacement for cache_loader. """

    name = 'esp.cache'

    def ready(self):
        import sys
        from django.conf import settings
        from esp.cache.registry import _finalize_caches, _lock_caches
        from django.apps import apps

        # Make sure everything's already imported

        #Initializing the model cache for customforms
        from esp.customforms.linkfields import cf_cache
        cf_cache._populate()

        # Import views files from INSTALLED_APPS
        for app_config in apps.get_app_configs():
            __import__(app_config.name, {}, {}, ['models'])

        #   Make sure template override cache is registered
        import esp.utils.template

        #   Make sure all cached inclusion tags are registered
        import esp.utils.inclusion_tags

        # import esp.cache.test

        # Fix up the queued events
        _finalize_caches()
        _lock_caches()

        print "Caches loaded"
