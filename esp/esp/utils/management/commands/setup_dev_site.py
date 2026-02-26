from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = "Sets the Django Site domain and name to 'localhost' for local development."

    def handle(self, *args, **kwargs):
        count = Site.objects.all().count()
        if count == 0:
            self.stdout.write(self.style.WARNING('No Site objects found. Creating a default localhost Site.'))
            Site.objects.create(id=1, domain='localhost', name='localhost')
        else:
            Site.objects.update(domain='localhost', name='localhost')
        self.stdout.write(self.style.SUCCESS("Successfully updated Site domain and name to 'localhost'."))
