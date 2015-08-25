from django.db.models import signals
from django.apps import AppConfig

def run_install(sender, **kwargs):
    if sender.name == 'esp.users':
        sender.models_module.install()

class UsersConfig(AppConfig):
    name = 'esp.users'

    def ready(self):
        signals.post_migrate.connect(run_install)
