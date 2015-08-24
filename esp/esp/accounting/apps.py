from django.db.models import signals
from django.apps import AppConfig

def run_install(sender, **kwargs):
    if sender.name == 'esp.accounting':
        sender.models_module.install()

class AccountingConfig(AppConfig):
    name = 'esp.accounting'

    def ready(self):
        signals.post_migrate.connect(run_install)
