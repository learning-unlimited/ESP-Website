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

##########
# SETTINGS:
##########

SERVER_HOSTNAME = 'esp.mit.edu' # Server to test against
SERVER_PORT = '80' # Port for the webserver on SERVER_HOSTNAME

# Warning: Tests will currently fail if this is True because the test database isn't prepopulated with enough data.  This is a bug.
START_DEVSERVER = False # Start the Django development web server?
DEVSERVER_START_TIME = 2 # Wait this many seconds after starting the dev server server process, before starting tests

STRESS_TEST_THREADS = 20 # Number of simultaneous Twill threads executing tests in the Stress Test
STRESS_TEST_TESTLOOPS_PER_THREAD = 20 # Number of times each Twill thread iterates through all available .twill files, in the Stress Test


##########
# NOT SETTINGS:
##########
if SERVER_HOSTNAME == None or SERVER_HOSTNAME == '':
    SERVER_HOSTNAME = '127.0.0.1'

if SERVER_PORT == None or SERVER_PORT == '':
    SERVER_PORT = ''
    
import unittest

class AllFilesTest(unittest.TestCase):
    """
    Executes all of the .twill test files in the 'twilltests' app directory.

    If 'START_DEVSERVER' is set, assumes that the server to be tested is
    '127.0.0.1:SERVER_PORT'
    """

    # Override this variable in subclasses to have the subclasses
    # test against files in a different module.
    # There should be a way to do this automagically via introspection;
    # I don't know it, though...
    test_module = __module__.split('.')[-2]

    # Use local copies of these variables,
    # so that they can be overridden in subclasses
    # NOTE: Subclasses can't yet actually override these,
    # so don't use them as such yet.
    stress_test_threads = STRESS_TEST_THREADS
    stress_test_testloops_per_thread = STRESS_TEST_TESTLOOPS_PER_THREAD
    server_hostname = SERVER_HOSTNAME
    server_port = SERVER_PORT
    start_devserver = START_DEVSERVER
    devserver_start_time = DEVSERVER_START_TIME

    def setUp(self):
        """
        Create the deafult test user, as used by these tests,
        if we're using the local devserver
        """
        if self.start_devserver:
            from django.contrib.auth.models import User
            (testUser, temp) = User.objects.get_or_create(username='testuser', first_name = 'Test', last_name = 'UserPerson')
            testUser.set_password('password')
            testUser.save()

    def _files(self):
        """
        Return the set of .twill test files in the root directory
        of the Python module that this class was defined in.

        Assumes that the class containing this test is defined in
        'tests.py' or 'models.py' in the module directory, per
        Django's auto-testing requirements.
        """

        module_name = self.test_module
        file_extension = '.twill'
        
        import os
        return [os.path.join(module_name, x) for x in os.listdir(module_name) if x[-len(file_extension):] == file_extension]

    def get_get_url(self):
        """
        Return a get_url() function that takes no parameters,
        suitable for Twill's usage
        """
        
        def get_url():
            """
            Implement our own get_url for Twill:
            Return 'http://SERVER_HOSTNAME:SERVER_PORT/',
            using '127.0.0.1' instead of SERVER_HOSTNAME if START_DEVSERVER == True
            """
            if self.start_devserver:
                return "http://127.0.0.1:%s/" % self.server_port
            else:
                return "http://%s:%s/" % (self.server_hostname, self.server_port)

        return get_url

    def get_url(self):
        """
        A convenience function that calls get_get_url()()
        in case we want to get the URL locally, instead of handing it off to Twill
        """
        return self.get_get_url()()

    def _test_info(self, testFile):
        """
        Return a Twill TestInfo instance that will execute
        the specified test against the server specified by
        SERVER_HOSTNAME and SERVER_PORT

        If no test is specified but self.start_devserver == True,
        the returned object will still be able to start the
        Django test server.
        """

        def startWebserver():
            """
            Function that Twill calls to start any relevant
            servers/services before starting to test

            Note that this function should never end naturally,
            Twill will terminate it.  If it does end, Twill will
            determine that it crashed and that all (future?) tests fail.
            """
            if self.start_devserver:
                from django.core.management import runserver
                runserver('127.0.0.1', self.server_port, False)
            else:
                import time
                while True:
                    # Loop forever, using as little CPU power as possible
                    # (to meet our spec of "this function never ends")
                    time.sleep(999999)

        import twill.unit

        # Only sleep before tests if we're starting the dev server
        if self.start_devserver:
            sleepTime = self.devserver_start_time # Server Start Sleep Hack
        else:
            sleepTime = 0

        # Finally make the test, using all accumulated parameters
        test_info = twill.unit.TestInfo(testFile, startWebserver, self.server_port, sleepTime)
        test_info.get_url = self.get_get_url() # Use our modified get_url

        return test_info

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
        files = self._files()

        import twill.unit
        for testFile in files:
            print "---------- Testing %s: ----------" % testFile
            twill.unit.run_test(self._test_info(testFile))


    def testStressTest(self):
        print "Error: Stress test doesn't work within the Django tester."
        print "Cancelling this test."
        return
        """
        Same functionality as testFiles(), except that the 'twill-fork'
        stress-testing program is invoked to execute the scripts
        instead of just executing one test at a time.
        
        See the documentation for 'twill-fork'.

        Fair warning: This stress test is fully capable of providing rather
        absurd amounts of load to any of:
        - The target test server
        - The machine running this test
        - The network between the two (if applicable)
        It can't, however, tell which is the bottleneck.  That's your job.
        """
        import os

        argv_for_twill = ['-u%s' % self.get_url(), '-n%s' % str(self.stress_test_threads * self.stress_test_testloops_per_thread), '-p%s' % str(self.stress_test_threads)]
        argv_for_twill += self._files()

        # The following few lines are basically straight from the Twill source code.
        # Apparently, this is the Pythonic way to start and later kill a separate process/thread.
        pid = os.fork()

        if pid is 0:
            import twill.unit
            twill.unit.run_child_process(self._test_info('')) # Never returns
        else:
            child_pid = pid

        # Execute twill-fork from the command line.
        # This turns out to be notably easier than invoking it
        # with Python directly, because it uses builtins to parse
        # command-line options.
        os.system("twill-fork %s" % ' '.join(argv_for_twill))
        os.kill(child_pid, 9)
