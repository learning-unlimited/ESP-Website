from django.db.models import signals
from django.apps import AppConfig

def run_install(sender, **kwargs):
    if sender.name == 'esp.resources':
        sender.models_module.install()

class ResourcesConfig(AppConfig):
    name = 'esp.resources'

    def ready(self):
        signals.post_migrate.connect(run_install)
