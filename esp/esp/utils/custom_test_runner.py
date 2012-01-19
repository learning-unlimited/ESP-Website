from django_selenium.selenium_runner import SeleniumTestRunner

class CustomSeleniumTestRunner(SeleniumTestRunner):
    """
    Custom test runner that subclasses the regular selenium test runner
    to include the esp database isolation code.
    """
    def __init__(self, **kwargs):
        SeleniumTestRunner.__init__(self, **kwargs)

