from django.db.models import signals
from django.apps import AppConfig

def run_install(sender, **kwargs):
    if sender.name == 'esp.program':
        sender.models_module.install()

class ProgramConfig(AppConfig):
    name = 'esp.program'

    def ready(self):
        signals.post_migrate.connect(run_install)
