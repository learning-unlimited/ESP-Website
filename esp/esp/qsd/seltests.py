from django_selenium.testcases import SeleniumTestCase
from esp.users.views.make_admin import make_user_admin
from esp.users.models import ESPUser
from esp.users.models import UserBit
from esp.settings import VARNISH_PORT
from esp.datatree.models import GetNode
from esp.seltests import try_login, logout
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium import selenium
from sys import stdout, stderr, exc_info


def noActiveAjax(driver):
    return driver.execute_script("return numAjaxConnections == 0")

class TestQsdCachePurging(SeleniumTestCase):
    PASSWORD_STRING = 'password'
    TEST_STRING = 'Hello there from a django test!'

    def editQSD(self):
        elem = self.find_element_by_class_name("qsd_header")
        elem.click()
        stdout.write("Clicked the qsd header!\n")
        elem = self.find_element_by_name("qsd_content")
        stdout.write("Found the text box!\n")
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
        self.qsd_user.userbit_set.add(UserBit(verb = GetNode('V/Administer/Edit/QSD'), qsc = GetNode('Q'), recursive = True))
        self.qsd_user.save()

    def test_qsd_cache_purging(self):
        self.driver.testserver_port = VARNISH_PORT
        self.open_url("/")
        try_login(self, self.admin_user.username, self.PASSWORD_STRING)
        self.editQSD()

        self.delete_all_cookies()
        self.open_url("/")
        self.failUnless(self.is_text_present(self.TEST_STRING))
        logout(self)

        try_login(self, self.qsd_user.username, self.PASSWORD_STRING)
        self.editQSD()

        self.delete_all_cookies()
        self.open_url("/")
        self.failUnless(self.is_text_present(self.TEST_STRING))

        self.driver.testserver_port = 8000 # Find where this number is actually stored

    def cleanUp(self):
        stdout.write("Cleaning up!\n")
        self.driver.testserver_port = 8000 # Find where this number is actually stored        
