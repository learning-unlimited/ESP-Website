from django_selenium.management.commands import test_selenium
from south.management.commands import test as test_south

class Command(test_south.Command, test_selenium.Command):

   def handle(self, *test_labels, **options):
      # Call both super methods (south first, so it can set up the DB correctly)
      test_south.Command.handle(self, *test_labels, **options)
      test_selenium.Command.handle(self, *test_labels, **options)
