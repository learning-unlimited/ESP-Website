__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""
from esp.qsd.models import QuasiStaticData
from esp.seltests.util import try_normal_login, logout, noActiveAjaxJQuery
from esp.tagdict.models import Tag
from esp.users.models import ESPUser
from esp.web.models import NavBarCategory, default_navbarcategory

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.unittest.case import skipUnless
from django_selenium.testcases import SeleniumTestCase
from selenium import selenium
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys

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

        # Make our users
        self.admin_user, created = ESPUser.objects.get_or_create(username='admin', first_name='Harry', last_name='Alborez')
        self.admin_user.set_password(self.PASSWORD_STRING)
        self.admin_user.makeAdmin()
        self.qsd_user, created = ESPUser.objects.get_or_create(username='qsd', first_name='Aylik', last_name='Kewesd')
        self.qsd_user.set_password(self.PASSWORD_STRING)
        self.qsd_user.save()

        # Check that a NavBarCategory exists
        if len(NavBarCategory.objects.all()) < 1:
            nbc = NavBarCategory()
            nbc.name = 'default'
            nbc.save()

        # Make our test page
        qsd_rec_new = QuasiStaticData()
        qsd_rec_new.url = 'test'
        qsd_rec_new.name = 'test'
        qsd_rec_new.author = self.admin_user
        qsd_rec_new.nav_category = default_navbarcategory()
        qsd_rec_new.content = ''
        qsd_rec_new.title = 'Test page'
        qsd_rec_new.description = ''
        qsd_rec_new.keywords    = ''
        qsd_rec_new.save()

        # Set the port that the webdriver will try to access
        self._old_port = self.driver.testserver_port
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
        self.assertTrue(self.is_text_present(self.TEST_STRING))
        logout(self)

        try_normal_login(self, self.qsd_user.username, self.PASSWORD_STRING)
        self.open_url(page)
        self.editQSD()

        self.delete_all_cookies()
        self.open_url(page)
        self.assertTrue(self.is_text_present(self.TEST_STRING))

    @skipUnless(hasattr(settings, 'VARNISH_HOST') and hasattr(settings, 'VARNISH_PORT'), "Varnish settings weren't set")
    def test_inline(self):
        self.check_page("/")

    @skipUnless(hasattr(settings, 'VARNISH_HOST') and hasattr(settings, 'VARNISH_PORT'), "Varnish settings weren't set")
    def test_regular(self):
        self.check_page("/test.html")

    def tearDown(self):
        super(TestQsdCachePurging, self).tearDown()
        self.driver.testserver_port = self._old_port
