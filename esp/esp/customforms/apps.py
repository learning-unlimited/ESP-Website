from esp.utils.apps import InstallConfig

class CustomformsConfig(InstallConfig):
    name = 'esp.customforms'

    def ready(self):
        super(CustomformsConfig, self).ready()

        # Initialize the model cache for customforms
        # This import needs to go here because it will indirectly
        # import some models and that shouldn't happen yet when
        # this file is imported
        from esp.customforms.linkfields import cf_cache
        cf_cache._populate()
