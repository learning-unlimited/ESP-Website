from esp.utils.apps import InstallConfig
from esp.customforms.linkfields import cf_cache

class CustomformsConfig(InstallConfig):
    name = 'esp.customforms'

    def ready(self):
        super(CustomformsConfig, self).ready()

        # Initialize the model cache for customforms
        cf_cache._populate()
