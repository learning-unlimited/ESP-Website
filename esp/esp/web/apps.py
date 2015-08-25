from django.db.models import signals
from django.apps import AppConfig

def run_install(sender, **kwargs):
    if sender.name == 'esp.web':
        sender.models_module.install()

class WebConfig(AppConfig):
    name = 'esp.web'

    def ready(self):
        signals.post_migrate.connect(run_install)
