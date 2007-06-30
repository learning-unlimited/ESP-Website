
# We don't want to do "from esp.twilltests.tests import AllFilesTest
# because then UnitTest sees AllFilesTest twice and tries to run it
# twice, which is unnecessary.
# Just using plain 'import' thwarts UnitTest's introspection magic.
import esp.twilltests.tests

# Define a new AllFilesTest subclass
class WebTest(esp.twilltests.tests.AllFilesTest):
    # This class will test all .twill files in the 'web' Django app
    test_module = 'web'

    

