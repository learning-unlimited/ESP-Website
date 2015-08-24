from django.apps import AppConfig
from django.db.models import signals

class InstallConfig(AppConfig):
    """
    Base class for app configs of modules that use install() for initial
    data. Don't use this on its own, subclass it to provide a name.
    """

    def ready(self):
        def run_install(sender, **kwargs):
            if sender.name == self.name:
                sender.models_module.install()

        signals.post_migrate.connect(run_install)
