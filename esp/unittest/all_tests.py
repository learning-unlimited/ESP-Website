from esp.unittest.unittest import TestSuite, TextTestRunner
from esp.unittest.dbmail_test import dbmailTestSuite
#from esp.unittest.users_test import usersTestSuite
#from esp.unittest.workflow_test import dbmailTestSuite
from esp.unittest.watchlists_test import watchlistsTestSuite

all_tests = TestSuite((dbmailTestSuite, watchlistsTestSuite))


#if __name__ == "__main__":
#    main()

TextTestRunner().run(all_tests)
