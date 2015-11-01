from argcache.apps import ArgCacheConfig

class ESPCacheConfig(ArgCacheConfig):
    """ Makes sure all caches are inserted. Replacement for cache_loader. """

    def ready(self):
        from argcache.registry import _finalize_caches, _lock_caches
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

        # Fix up the queued events
        _finalize_caches()
        _lock_caches()
