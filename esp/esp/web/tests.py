__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 by the individual contributors
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
  Email: web-team@lists.learningu.org
"""

from esp.web.models import NavBarEntry, NavBarCategory

from django.test.client import Client
from esp.tests.util import CacheFlushTestCase as TestCase

import re

# We don't want to do "from esp.twilltests.tests import AllFilesTest
# because then UnitTest sees AllFilesTest twice and tries to run it
# twice, which is unnecessary.
# Just using plain 'import' thwarts UnitTest's introspection magic.
import esp.twilltests.tests

# Define a new AllFilesTest subclass
class WebTest(esp.twilltests.tests.AllFilesTest):
    # This class will test all .twill files in the 'web' Django app
    test_module = 'web'

# Make sure that we can actually download the homepage
class PageTest(TestCase):
    """ Validate common hard-coded flatpages """

    # Util Functions
    def assertStringContains(self, string, contents):
        if not (contents in string):
            self.assert_(False, "'%s' not in '%s'" % (contents, string))

    def assertNotStringContains(self, string, contents):
        if contents in string:
            self.assert_(False, "'%s' are in '%s' and shouldn't be" % (contents, string))

    
    def testHomePage(self):
        """ Make sure that we can actually download the homepage """
        c = Client()
        
        response = c.get("/")

        # Make sure the page load/render was a success
        self.assertEqual(response.status_code, 200)

        # Make sure that we've gotten an HTML document, and not a Django error
        self.assertStringContains(response.content, "<html")
        self.assertNotStringContains(response.content, "You're seeing this error because you have <code>DEBUG = True</code>")

class NavbarTest(TestCase):
    
    def get_navbar_titles(self, path='/'):
        response = self.client.get(path)

        navbaritem_re = re.compile(r'<li class="divsecondarynavlink (?:indent)?">\s+(.*)\s+</li>')
        re_results = re.findall(navbaritem_re, response.content)
        return re_results

    def testNavbarBehavior(self):
        home_category, created = NavBarCategory.objects.get_or_create(name='home')

        #   Clear navbars and ensure we get nothing
        NavBarEntry.objects.all().delete()
        self.assertTrue(self.get_navbar_titles('/') == [], 'Non-existent navbars appearing: got %s, expected %s' % (self.get_navbar_titles('/'), []))

        #   Check that when you create a nav bar it shows up
        n1 = NavBarEntry(category=home_category, sort_rank=0, text='NavBar1', indent=False)
        n1.save()
        self.assertTrue(self.get_navbar_titles('/') == ['NavBar1'], 'New navbar not showing up: got %s, expected %s' % (self.get_navbar_titles('/'), ['NavBar1']))

        #   Check that when you edit a nav bar it changes
        n1.text = 'NavBar1A'
        n1.save()
        self.assertTrue(self.get_navbar_titles('/') == ['NavBar1A'], 'Changes to navbar not showing up: got %s, expected %s' % (self.get_navbar_titles('/'), ['NavBar1A']))

        #   Check that you can create a navbar and reorder them
        n2 = NavBarEntry(category=home_category, sort_rank=10, text='NavBar2', indent=False)
        n2.save()
        self.assertTrue(self.get_navbar_titles('/') == ['NavBar1A', 'NavBar2'], 'Additional navbar not showing up: got %s, expected %s' % (self.get_navbar_titles('/'), ['NavBar1A', 'NavBar2']))
        n1.sort_rank = 20
        n1.save()
        self.assertTrue(self.get_navbar_titles('/') == ['NavBar2', 'NavBar1A'], 'Altered navbar order not showing up: got %s, expected %s' % (self.get_navbar_titles('/'), ['NavBar2', 'NavBar1A']))
        

