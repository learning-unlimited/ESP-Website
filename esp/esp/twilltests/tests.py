#
# Twill Unit Tests
#
# This app is for UnitTest tests that use the Twill framework
# to test general features of the website.
#
# Ultimately, these tests should be split off into 'test.py' files in the
# apps that they test.  However, there should be one unified place from
# which one can call all Twill tests, as a Web sanity check.
# Therefore, if you're writing a Twill test, for now please put it
# in this file (or import it into this file), or add a comment to this
# file noting where it is.
#
# If START_DEVSERVER == True, an instance of the dev server will be started
# before running any tests.  If you write a new 
#

# SETTINGS:
SERVER_HOSTNAME = 'esp.mit.edu'
SERVER_PORT = '80'
START_DEVSERVER = False # Warning: Tests will currently fail if this is True because the test database isn't prepopulated with enough data.  This is a bug.


# NOT SETTINGS:
if SERVER_HOSTNAME == None or SERVER_HOSTNAME == '':
    SERVER_HOSTNAME = '127.0.0.1'

if SERVER_PORT == None or SERVER_PORT == '':
    SERVER_PORT = ''
    
import unittest

class AllFilesTest(unittest.TestCase):
    """
    Executes all of the .twill test files in the 'twilltests' app directory.

    If 'START_DEVSERVER' is set, assumes that 
    """
    
    def setUp(self):
        """ Create the deafult test user, as used by these tests, if we're using the local devserver """
        if START_DEVSERVER:
            from django.contrib.auth.models import User
            (testUser, temp) = User.objects.get_or_create(username='testuser', first_name = 'Test', last_name = 'UserPerson')
            testUser.set_password('password')
            testUser.save()

    def testFiles(self):
        """
        Scan 'twilltests/' looking for files ending in '.twill'.
        Execute each such file as a Twill script.

        Hack twill slightly s.t. it tests against the server specified
        with SERVER_HOSTNAME and SERVER_PORT.  Ignore SERVER_HOSTNAME
        and use 127.0.0.1 if START_DEVSERVER is set.

        If START_DEVSERVER is set, tell Twill to launch the dev server
        while testing, and tell it to wait for 1 second after launching
        the server to begin testing.  If the dev server takes more than 1
        second to start, this should be adjusted.
        """
        import os
        files = [os.path.join('twilltests', x) for x in os.listdir('twilltests') if x[-6:] == '.twill']

        def get_url():
            """ Implement our own get_url for Twill """
            if START_DEVSERVER:
                return "http://127.0.0.1:%s/" % SERVER_PORT
            else:
                return "http://%s:%s/" % (SERVER_HOSTNAME, SERVER_PORT)
        
        def startWebserver():
            """
            Function that Twill calls to start any relevant
            servers/services before starting to test

            Note that this function should never end naturally,
            Twill will terminate it.  If it does end, Twill will
            determine that it crashed and that all (future?) tests fail.
            """
            if START_DEVSERVER:
                from django.core.management import runserver
                runserver('127.0.0.1', SERVER_PORT, False)
            else:
                import time
                while True:
                    time.sleep(999999)

        import twill.unit

        for testFile in files:
            if START_DEVSERVER:
                sleepTime = 1 # Server Start Sleep Hack.  Feel free to tweak.
            else:
                sleepTime = 0
                
            test_info = twill.unit.TestInfo(testFile, startWebserver, SERVER_PORT, sleepTime)
            test_info.get_url = get_url # Use our modified get_url
            twill.unit.run_test(test_info)
