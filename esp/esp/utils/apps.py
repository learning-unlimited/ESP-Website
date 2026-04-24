from django.apps import AppConfig
from django.db.models import signals

def run_install(sender, **kwargs):
    models_module = getattr(sender, "models_module", None)
    if models_module is not None:
        install = getattr(models_module, "install", None)
        if callable(install):
            install()

class InstallConfig(AppConfig):
    """
    Base class for app configs of modules that use install() for initial
    data. Don't use this on its own, subclass it to provide a name.
    """

    def ready(self):
        signals.post_migrate.connect(run_install, sender=self)
