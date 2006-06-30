

class TestCase:
    """ Yay, it's a hacked minimal implementation of TestCase! """
    def runTest(self):
        print "no Run"
    def setUp(self):
        print "no setUp"
    def tearDown(self):
        print "no tearDown"


class TestSuite:
    testList = []
    def __init__(self, arg=[]):
        self.addTest(arg)
    def addTest(self, test):
        self.testList.append(test)


class TextTestRunner:
    def run(self, tests):
        if type(tests) == type([]):
            for t in tests:
                self.run(t)
        elif type(tests) == type(TestSuite()):
            for t in tests.testList:
                self.run(t)
        else:
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

            print t.__doc__ + " successful!"
