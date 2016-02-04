from django_selenium.selenium_runner import SeleniumTestRunner
from optparse import make_option
from south.management.commands import patch_for_test_db_setup
from south.management.commands import test as test_south

import logging
logger = logging.getLogger(__name__)
import sys


class Command(test_south.Command):

   option_list = test_south.Command.option_list + (
      make_option('--selenium-tests', action='store_true', dest='run_selenium_tests', default=False, help='Run Selenium tests only.'),
      make_option('--normal-tests', action='store_true', dest='run_normal_tests', default=False, help='Run non-Selenium tests only.')
   )

   def handle(self, *test_labels, **options):
      """Trigger both south and selenium tests."""

      run_south_tests = bool(options.get('run_normal_tests', False))
      run_selenium_tests = bool(options.get('run_selenium_tests', False))

      # Check test types
      if (run_south_tests and run_selenium_tests or
         not run_south_tests and not run_selenium_tests):
         logger.error("You must specify exactly one of --selenium-tests and --normal-tests.")
         sys.exit(1)

      # Apply the south patch for syncdb, migrate commands during tests
      patch_for_test_db_setup()

      if run_south_tests:
         test_south.Command.handle(self, *test_labels, **options)
      elif run_selenium_tests:
         # We don't want to call any super handle function, because it will
         # try to run tests in addition to parsing command line options.
         # Instead, we parse the relevant options ourselves.
         verbosity = int(options.get('verbosity', 1))
         interactive = options.get('interactive', True)
         failfast = options.get('failfast', False)

         test_runner = SeleniumTestRunner(verbosity=verbosity, interactive=interactive, failfast=failfast)
         test_runner.selenium = True
         test_runner.selenium_only = True
         failures = test_runner.run_tests(test_labels)
         if failures:
            sys.exit(bool(failures))
