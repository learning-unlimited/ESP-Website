from esp.unittest.unittest import TestSuite, TextTestRunner
from esp.unittest.dbmail_test import dbmailTestSuite
#from esp.unittest.users_test import usersTestSuite
#from esp.unittest.workflow_test import dbmailTestSuite
from esp.unittest.datatree_test import datatreeTestSuite

all_tests = TestSuite()
all_tests.addTest(dbmailTestSuite)
all_tests.addTest(datatreeTestSuite)


#if __name__ == "__main__":
#    main()

TextTestRunner().run(all_tests)
