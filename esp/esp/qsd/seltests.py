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
from esp.users.models import ESPUser
from esp.web.models import NavBarCategory, default_navbarcategory

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys

class TestQsdCachePurging(StaticLiveServerTestCase):
    """
       This test requires Varnish (or some proxy caching server that accepts
       PURGE requests) to be set up on the port and host specified in
       local_settings.py as VARNISH_HOST (a string) and VARNISH_PORT (an int).
    """

    PASSWORD_STRING = 'password'
    TEST_STRING = 'Hello there from a django test!'

    def editQSD(self):
        elem = self.selenium.find_element_by_class_name("qsd_header")
        elem.click()
        elem = self.selenium.find_element_by_class_name("jodit_wysiwyg")
        for x in range(0, len(elem.text)):
            elem.send_keys(Keys.DELETE)
        elem.send_keys(self.TEST_STRING)
        elem = self.selenium.find_element_by_class_name("btn-success")
        elem.click()
        WebDriverWait(self.selenium, 10).until(noActiveAjaxJQuery)

    def setUp(self):
        super(TestQsdCachePurging, self).setUp()

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

        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        self.selenium = webdriver.Firefox(firefox_options=options)
        self.selenium.implicitly_wait(10)

    def test_qsd_editing(self):
        for page in ["/", "/test.html"]:
            self.selenium.get('%s%s' % (self.live_server_url, "/"))
            try_normal_login(self.selenium, self.live_server_url, self.admin_user.username, self.PASSWORD_STRING)
            self.selenium.get('%s%s' % (self.live_server_url, page))
            self.assertTrue(self.selenium.find_element_by_class_name("qsd_header").is_displayed(), "Admin should be able to see the QSD header on " + page)
            self.editQSD()

            self.selenium.delete_all_cookies()
            self.selenium.get('%s%s' % (self.live_server_url, page))
            self.assertTrue(self.TEST_STRING in self.selenium.page_source)
            logout(self.selenium, self.live_server_url)

            self.selenium.get('%s%s' % (self.live_server_url, "/"))
            try_normal_login(self.selenium, self.live_server_url, self.qsd_user.username, self.PASSWORD_STRING)
            self.selenium.get('%s%s' % (self.live_server_url, page))
            self.assertFalse(self.selenium.find_element_by_class_name("qsd_header").is_displayed(), "Non-admin shouldn't be able to see the QSD header on " + page)

            self.selenium.delete_all_cookies()
            self.selenium.get('%s%s' % (self.live_server_url, page))
            self.assertTrue(self.TEST_STRING in self.selenium.page_source)

    def tearDown(self):
        self.selenium.quit()
        super(TestQsdCachePurging, self).tearDown()
