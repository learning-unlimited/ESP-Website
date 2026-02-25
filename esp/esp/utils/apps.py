from django.apps import AppConfig
from django.db.models import signals


def run_install(sender, **kwargs):
    """
    Post-migrate hook used by apps that define an install() helper on their
    models module to populate initial data.

    Some apps (like esp.utils) use InstallConfig but do not need an install()
    function; in that case we should simply do nothing rather than error.
    """
    models_module = sender.models_module
    if hasattr(models_module, "install"):
        models_module.install()


class InstallConfig(AppConfig):
    """
    Base class for app configs of modules that use install() for initial
    data. Don't use this on its own, subclass it to provide a name.
    """

    def ready(self):
        signals.post_migrate.connect(run_install, sender=self)


class UtilsConfig(InstallConfig):
    name = 'esp.utils'
