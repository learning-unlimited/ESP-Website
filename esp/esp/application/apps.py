from __future__ import absolute_import
from django.apps import AppConfig

class ApplicationConfig(AppConfig):
    name = 'esp.application'

    def ready(self):
        import esp.application.signals
