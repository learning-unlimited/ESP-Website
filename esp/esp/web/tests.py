from django.test.client import Client
from esp.tests.util import CacheFlushTestCase as TestCase

# We don't want to do "from esp.twilltests.tests import AllFilesTest
# because then UnitTest sees AllFilesTest twice and tries to run it
# twice, which is unnecessary.
# Just using plain 'import' thwarts UnitTest's introspection magic.
import esp.twilltests.tests

# Define a new AllFilesTest subclass
class WebTest(esp.twilltests.tests.AllFilesTest):
    # This class will test all .twill files in the 'web' Django app
    test_module = 'web'

# Make sure that we can actually download the homepage
class PageTest(TestCase):
    """ Validate common hard-coded flatpages """

    # Util Functions
    def assertStringContains(self, string, contents):
        if not (contents in string):
            self.assert_(False, "'%s' not in '%s'" % (contents, string))

    def assertNotStringContains(self, string, contents):
        if contents in string:
            self.assert_(False, "'%s' are in '%s' and shouldn't be" % (contents, string))

    
    def testHomePage(self):
        """ Make sure that we can actually download the homepage """
        c = Client()
        
        response = c.get("/")

        # Make sure the page load/render was a success
        self.assertEqual(response.status_code, 200)

        # Make sure that we've gotten an HTML document, and not a Django error
        self.assertStringContains(response.content, "<html")
        self.assertNotStringContains(response.content, "You're seeing this error because you have <code>DEBUG = True</code>")
