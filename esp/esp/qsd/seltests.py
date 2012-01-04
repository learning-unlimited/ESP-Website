from django.utils.unittest.case import skipIf
from django_selenium.testcases import SeleniumTestCase
from esp.users.views.make_admin import make_user_admin
from esp.users.models import ESPUser
from esp.users.models import UserBit
import esp.settings
from esp.datatree.models import GetNode
from esp.seltests import try_ajax_login, logout, noActiveAjaxJQuery
from esp.qsd.models import QuasiStaticData
from esp.web.models import NavBarCategory
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium import selenium
from sys import stdout, stderr, exc_info
import time

# Make sure our varnish settings exist
if hasattr(esp.settings, 'VARNISH_HOST') and hasattr(esp.settings, 'VARNISH_PORT'):
    from esp.settings import VARNISH_PORT
else:
    # Set this for now, but it shouldn't actually be used
    VARNISH_PORT = 8000

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
        elem = self.find_element_by_name("qsd_content")
        for x in range(0, len(elem.text)):
            elem.send_keys(Keys.DELETE)
        elem.send_keys(self.TEST_STRING)
        elem.send_keys(Keys.TAB)
        WebDriverWait(self, 10).until(noActiveAjaxJQuery)

    def setUp(self):
        SeleniumTestCase.setUp(self)

        # Make Q/Web public
        UserBit.objects.create(verb = GetNode('V/Flags/Public'), qsc = GetNode('Q/Web'))

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
        qsd_rec_new.path = GetNode('Q/Web')
        qsd_rec_new.name = 'test'
        qsd_rec_new.author = self.admin_user
        qsd_rec_new.nav_category = NavBarCategory.default()
        qsd_rec_new.content = ''
        qsd_rec_new.title = 'Test page'
        qsd_rec_new.description = ''
        qsd_rec_new.keywords    = ''
        qsd_rec_new.save()
        self.driver.testserver_port = VARNISH_PORT

    def check_page(self, page):
        self.open_url("/")
        try_ajax_login(self, self.admin_user.username, self.PASSWORD_STRING)
        self.open_url(page)
        self.editQSD()

        self.delete_all_cookies()
        self.open_url(page)
        self.failUnless(self.is_text_present(self.TEST_STRING))
        logout(self)

        try_ajax_login(self, self.qsd_user.username, self.PASSWORD_STRING)
        self.open_url(page)
        self.editQSD()

        self.delete_all_cookies()
        self.open_url(page)
        self.failUnless(self.is_text_present(self.TEST_STRING))

    @skipIf(not hasattr(esp.settings, 'VARNISH_HOST') or not hasattr(esp.settings, 'VARNISH_PORT'), "Varnish settings weren't set")
    def test_inline(self):
        self.check_page("/")

    @skipIf(not hasattr(esp.settings, 'VARNISH_HOST') or not hasattr(esp.settings, 'VARNISH_PORT'), "Varnish settings weren't set")
    def test_regular(self):
        self.check_page("/test.html")

    def cleanUp(self):
        self.driver.testserver_port = 8000 # Find where this number is actually stored        
