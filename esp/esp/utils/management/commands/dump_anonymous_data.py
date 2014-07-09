from django.core.management.color import color_style, no_style
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models.loading import get_apps
from django.db import connection
from django.core.management import call_command

app_list = ["accounting",
             "accounting_core",
             "cal",
             "dbmail", 
             "miniblog", 
             "program", 
             "modules",
             "shortterm",
             "users",
             "web"]

class Command(BaseCommand):
    
    help = "Anonymizes data and dumps a single fixture for the the following apps: %s"%app_list

    def handle(self, *args, **options):
        app_names = ' '.join(self.app_list)
        call_command('anonymize_data', *self.app_list, interactive=True)
        call_command('dumpdata', *self.app_list, stdout=f)

        
