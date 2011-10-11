from esp.settings import INSTALLED_APPS

def custom_test_runner(test_labels, verbosity=1, interactive=True, extra_tests=[]):
    import esp.datatree.sql.set_isolation_level
    esp.datatree.sql.set_isolation_level.DISABLE_TRANSACTIONS = True    

    ## Now, run the standard tester
    from django.test.simple import run_tests as django_test_runner
    return django_test_runner(test_labels, verbosity, interactive, extra_tests)

from django_selenium.selenium_runner import SeleniumTestRunner

class CustomSeleniumTestRunner(SeleniumTestRunner):
    """
    Custom test runner that subclasses the regular selenium test runner
    to include the esp database isolation code.
    """
    def __init__(self, **kwargs):
        import esp.datatree.sql.set_isolation_level
        esp.datatree.sql.set_isolation_level.DISABLE_TRANSACTIONS = True    

        SeleniumTestRunner.__init__(self, **kwargs)

