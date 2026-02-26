from __future__ import absolute_import
from django.apps import AppConfig
import copyreg

class ApplicationConfig(AppConfig):
    name = 'esp.application'

    def ready(self):
        import esp.application.signals
        # h/t https://github.com/noripyt/django-cachalot/issues/125
        # https://docs.python.org/3/library/copyreg.html#copyreg.pickle
        copyreg.pickle(memoryview, lambda val: (memoryview, (bytes(val),)))
