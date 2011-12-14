from django_selenium.testcases import SeleniumTestCase
from esp.users.views.make_admin import make_user_admin
from esp.users.models import ESPUser
from esp.users.models import UserBit
from esp.settings import VARNISH_PORT
from esp.datatree.models import GetNode
from esp.seltests import try_login, logout
from esp.qsd.models import QuasiStaticData
from esp.web.models import NavBarCategory
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium import selenium
from sys import stdout, stderr, exc_info


def noActiveAjax(driver):
    return driver.execute_script("return numAjaxConnections == 0")

class TestQsdCachePurging(SeleniumTestCase):
    """
       This test requires Varnish (or some proxy caching server that accepts PURGE requests)
       to be set up on the port and host specified in local_settings.py as VARNISH_HOST (a
       string) and VARNISH_PORT (an int).
    """

    PASSWORD_STRING = 'password'
    TEST_STRING = 'Hello there from a django test!'

    def editQSD(self):
        elem = self.find_element_by_class_name("qsd_header")
        elem.click()
        stdout.write("Clicked the qsd header!\n")
        elem = self.find_element_by_name("qsd_content")
        stdout.write("Found the text box!\n")
        for x in range(0, len(self.TEST_STRING)):
            elem.send_keys(Keys.DELETE)
        # For some reason the control_key_down function doesn't exist even though it should
        # TODO: Use the below code instead of the above at some point
        #self.control_key_down()
        #elem.send_keys("a")
        #self.control_key_up()
        #stdout.write("Selected the text!\n")
        elem.send_keys(self.TEST_STRING)
        stdout.write("Entered the text!\n")
        elem.send_keys(Keys.TAB)

    def setUp(self):
        SeleniumTestCase.setUp(self)

        # Make our users
        self.admin_user, created = ESPUser.objects.get_or_create(username='admin', first_name='Harry', last_name='Alborez')
        self.admin_user.set_password(self.PASSWORD_STRING)
        make_user_admin(self.admin_user)
        self.qsd_user, created = ESPUser.objects.get_or_create(username='qsd', first_name='Aylik', last_name='Kewesd')
        self.qsd_user.set_password(self.PASSWORD_STRING)
        self.qsd_user.userbit_set.add(UserBit(verb = GetNode('V/Administer/Edit'), qsc = GetNode('Q'), recursive = True))
        self.qsd_user.save()

        # Check that a NavBarCategory exists
        if len(NavBarCategory.objects.all()) < 1:
            nbc = NavBarCategory()
            nbc.name = 'default'
            nbc.save()

        # Make our test page
        qsd_rec_new = QuasiStaticData()
        qsd_rec_new.path = GetNode('Q/Programs')
        qsd_rec_new.name = 'teach:test'
        qsd_rec_new.author = self.admin_user
        qsd_rec_new.nav_category = NavBarCategory.default()
        qsd_rec_new.content = "Testing"
        qsd_rec_new.title = "Test page"
        qsd_rec_new.description = ''
        qsd_rec_new.keywords    = ''
        qsd_rec_new.save()

    def test_qsd_cache_purging(self):
        self.driver.testserver_port = VARNISH_PORT
        self.open_url("/")
        try_login(self, self.admin_user.username, self.PASSWORD_STRING)
        self.open_url("/teach/test.html")
        self.editQSD()

        self.delete_all_cookies()
        self.open_url("/")
        try_login(self, self.admin_user.username, self.PASSWORD_STRING)
        self.open_url("/teach/test.html")
        self.failUnless(self.is_text_present(self.TEST_STRING))
        logout(self)

        try_login(self, self.qsd_user.username, self.PASSWORD_STRING)
        self.open_url("/teach/test.html")
        self.editQSD()

        self.delete_all_cookies()
        self.open_url("/")
        try_login(self, self.admin_user.username, self.PASSWORD_STRING)
        self.open_url("/teach/test.html")
        self.failUnless(self.is_text_present(self.TEST_STRING))

        self.driver.testserver_port = 8000 # Find where this number is actually stored

    def cleanUp(self):
        stdout.write("Cleaning up!\n")
        self.driver.testserver_port = 8000 # Find where this number is actually stored        
