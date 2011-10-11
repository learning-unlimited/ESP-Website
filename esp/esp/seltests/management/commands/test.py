from django_selenium.management.commands import test_selenium
from south.management.commands import test as test_south

class Command(test_south.Command, test_selenium.Command):

   def handle(self, *test_labels, **options):
       super(Command, self).handle(*test_labels, **options)
