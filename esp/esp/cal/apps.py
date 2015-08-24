from django.db.models import signals
from django.apps import AppConfig

def run_install(sender, **kwargs):
    if sender.name == 'esp.cal':
        sender.models_module.install()

class CalConfig(AppConfig):
    name = 'esp.cal'

    def ready(self):
        signals.post_migrate.connect(run_install)
