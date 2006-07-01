

class TestCase(object):
    """ Yay, it's a hacked minimal implementation of TestCase! """
    def runTest(self):
        print "no Run"
    def setUp(self):
        print "no setUp"
    def tearDown(self):
        print "no tearDown"


class TestSuite(object):
    testList = []
    def __init__(self, arg=[]):
        self.addTest(arg)
    def addTest(self, test):
        self.testList.append(test)


class TextTestRunner(object):
    def run(self, tests):
        print "Running Test: " + str(tests)
        if type(tests) == type([]):
            print "Branching on a list"
            for t in tests:
                if t != tests:
                    self.run(t)
        elif type(tests) == type(TestSuite()):
            print "Branching"
            for t in tests.testList:
                if t != tests.testList:
                    self.run(t)
        else:
            print "Running!"
            t = tests()
            print str(tests)
            print str(t)
            
            try:
                t.setUp()
            except:
                print "Error in setUp: " + str(t.__doc__)
                raise
            
            try:
                t.runTest()
            except:
                print "Error in runTest: " + str(t.__doc__)
                raise

            try:
                t.tearDown()
            except:
                print "Error in tearDown: " + str(t.__doc__)
                raise

            print str(t.__doc__) + " successful!"
