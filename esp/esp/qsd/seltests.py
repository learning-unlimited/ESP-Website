from django.utils.unittest.case import skipUnless
from django_selenium.testcases import SeleniumTestCase
from esp.users.views.make_admin import make_user_admin
from esp.users.models import ESPUser
from esp.users.models import UserBit
# Can't do "from django.conf import settings", because this uses
# the settings from django_selenium
from django.conf import settings
import django_selenium.settings as selenium_settings
from django.contrib.sites.models import Site
from esp.datatree.models import GetNode
from esp.seltests import try_normal_login, logout, noActiveAjaxJQuery
from esp.qsd.models import QuasiStaticData
from esp.web.models import NavBarCategory
from esp.tagdict.models import Tag
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium import selenium
from sys import stdout, stderr, exc_info

class TestQsdCachePurging(SeleniumTestCase):
    """
       This test requires Varnish (or some proxy caching server that accepts
       PURGE requests) to be set up on the port and host specified in
       local_settings.py as VARNISH_HOST (a string) and VARNISH_PORT (an int).
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

        # Set the port that the webdriver will try to access
        self.driver.testserver_port = settings.VARNISH_PORT

        # Add the varnish_purge tag
        Tag.objects.get_or_create(key='varnish_purge', value='true')

        # Set up the correct site
        site = Site.objects.get_current()
        site.domain = settings.VARNISH_HOST+":"+str(settings.VARNISH_PORT)
        site.save()

    def check_page(self, page):
        self.open_url("/")
        try_normal_login(self, self.admin_user.username, self.PASSWORD_STRING)
        self.open_url(page)
        self.editQSD()

        self.delete_all_cookies()
        self.open_url(page)
        self.failUnless(self.is_text_present(self.TEST_STRING))
        logout(self)

        try_normal_login(self, self.qsd_user.username, self.PASSWORD_STRING)
        self.open_url(page)
        self.editQSD()

        self.delete_all_cookies()
        self.open_url(page)
        self.failUnless(self.is_text_present(self.TEST_STRING))

    @skipUnless(hasattr(settings, 'VARNISH_HOST') and hasattr(settings, 'VARNISH_PORT'), "Varnish settings weren't set")
    def test_inline(self):
        self.check_page("/")

    @skipUnless(hasattr(settings, 'VARNISH_HOST') and hasattr(settings, 'VARNISH_PORT'), "Varnish settings weren't set")
    def test_regular(self):
        self.check_page("/test.html")

    def tearDown(self):
        super(TestQsdCachePurging, self).tearDown()
        self.driver.testserver_port = getattr(selenium_settings, 'SELENIUM_TESTSERVER_PORT')
