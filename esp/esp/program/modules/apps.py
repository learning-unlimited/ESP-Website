from django.db.models import signals
from django.apps import AppConfig

def run_install(sender, **kwargs):
    if sender.name == 'esp.program.modules':
        sender.models_module.install()

class ModulesConfig(AppConfig):
    name = 'esp.program.modules'

    def ready(self):
        signals.post_migrate.connect(run_install)
