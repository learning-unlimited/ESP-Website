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
    # Prevent Django 3.2+ from auto-selecting this base class as the
    # default AppConfig for esp.utils (it has no name of its own).
    default = False

    def ready(self):
        signals.post_migrate.connect(run_install, sender=self)

class UtilsConfig(AppConfig):
    name = 'esp.utils'

