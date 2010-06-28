

def custom_test_runner(test_labels, verbosity=1, interactive=True, extra_tests=[]):

    ## Django plays some really weird games with transactions in test cases.
    ## Their monkeypatching isn't quite thorough enough to be compatible
    ## with what we do.
    ## But, none of our test cases really test our transaction usage, because
    ## our transaction usage is to prevent concurrent-access problems without
    ## killing performance, and the tester is single-threaded.
    ## So, we can either disable their games; this makes tests run slower:
    ## WARNING:  We have to un-patch some more stuff in Django, I haven't found it all yet
    #import django.test.testcases
    #django.test.testcases.TestCase = django.test.testcases.TransactionTestCase
    ## Or we can fix their monkeypatching
    from django.test.testcases import nop
    import django.db.transaction
    django.db.transaction.commit = nop
    django.db.transaction.commit_manually = nop
    import esp.datatree.sql.set_isolation_level
    esp.datatree.sql.set_isolation_level.DISABLE_TRANSACTIONS = True

    ## Now, run the standard tester
    from django.test.simple import run_tests as django_test_runner
    return django_test_runner(test_labels, verbosity, interactive, extra_tests)
