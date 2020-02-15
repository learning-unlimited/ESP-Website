from esp.utils.apps import InstallConfig

class ModulesConfig(InstallConfig):
    name = 'esp.program.modules'

    def ready(self):
        super(ModulesConfig, self).ready()
        # TODO(benkraft): add a thing to InstallConfig that imports a signals
        # file if one exists.
        import esp.program.modules.signals
