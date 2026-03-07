from django.apps import AppConfig
from django.db.models import signals
import sys

def run_install(sender, **kwargs):
    if "check" in sys.argv or "runserver" in sys.argv:
        return;

    models_module = getattr(sender, "models_module", None)
    if(models_module and hasattr(models_module, "install")):
        models_module.install()

class InstallConfig(AppConfig):
    """
    Base class for app configs of modules that use install() for initial
    data. Don't use this on its own, subclass it to provide a name.
    """

    def ready(self):
        signals.post_migrate.connect(run_install, sender=self)
