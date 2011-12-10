from django_selenium.testcases import SeleniumTestCase
from esp.users.views.make_admin import make_user_admin
from esp.users.models import ESPUser
from esp.users.models import UserBit
from esp.settings import VARNISH_PORT
from esp.datatree.models import GetNode
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from sys import stderr, exc_info


def noActiveAjax(driver):
    return driver.execute_script("return numAjaxConnections == 0")

class TestQsdCachePurging(SeleniumTestCase):
    PASSWORD_STRING = 'password'

    def loginUser(self, user):
        self.open_url("/")
        elem = self.find_element_by_name("username")
        elem.send_keys(user.username)
        elem = self.find_element_by_name("password")
        elem.send_keys(self.PASSWORD_STRING)
        elem.submit()
        try:
            WebDriverWait(self, 10).until(noActiveAjax)
        except:
            stderr.write(str(exc_info()[0]) + "\n")
            stderr.write("Wait for ajax login timed out.\n")
        self.open_url("/")

    def editQSD(self):
        elem = self.find_element_by_class_name("qsd_header")
        elem.click()
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
        self.unpriv_user, created = ESPUser.objects.get_or_create(username='unpriv', first_name='Angry', last_name='Parent')
        self.unpriv_user.set_password(self.PASSWORD_STRING)
        self.unpriv_user.save()

    def test_qsd_cache_purging(self):
        self.driver.testserver_port = VARNISH_PORT
        self.loginUser(self.admin_user)
        self.editQSD()
        # Somehow test this?
        # Perhaps we don't need to even check the QSD, just the purging really...

        import time
        time.sleep(10)
        self.driver.testserver_port = 8000 # Find where this number is actually stored
