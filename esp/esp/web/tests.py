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
  Email: web-team@learningu.org
"""

from esp.web.models import NavBarEntry, NavBarCategory, default_navbarcategory
from esp.program.tests import ProgramFrameworkTest  ## Really should find somewhere else to put this...
from django.test.client import Client
from django.conf import settings
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.utils.models import TemplateOverride

import difflib
import logging
logger = logging.getLogger(__name__)
import re
import os
import tempfile

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

    def navbars_enabled(self):
        #   Check that the main template uses navbars
        qs = TemplateOverride.objects.filter(name='main.html').order_by('-id')
        if qs.exists():
            if qs[0].content.find('{% navbar_gen') < 0:
                return False
        return True

    def testNavbarBehavior(self):
        home_category, created = NavBarCategory.objects.get_or_create(name='home')

        #   Don't bother testing this if the site doesn't have navbars showing.
        if not self.navbars_enabled():
            return

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


class NoVaryOnCookieTest(ProgramFrameworkTest):
    """
    The "Vary: Cookie" header should not ever be set on certain views.
    Test that it is in fact not set on these views.
    Further, test that it is safe to have it not-set on these views,
    because the content of the views is the same when logged out as when
    logged in as anyone.
    """

    url = "/learn/TestProgram/2222_Summer/"

    def testQSD(self):
        c = Client()
        res = c.get(self.url + "index.html")

        self.assertEqual(res.status_code, 200)
        self.assertTrue('Vary' not in res or 'Cookie' not in res['Vary'])
        logged_out_content = res.content

        c.login(username=self.admins[0], password='password')
        res = c.get(self.url + "index.html")

        self.assertEqual(res.status_code, 200)
        self.assertTrue('Vary' not in res or 'Cookie' not in res['Vary'])
        logged_in_content = res.content

        self.assertEqual("\n".join(difflib.context_diff(logged_out_content.split("\n"), logged_in_content.split("\n"))), "")

    def testCatalog(self):
        c = Client()
        res = c.get(self.url + "catalog")

        self.assertEqual(res.status_code, 200)
        self.assertTrue('Vary' not in res or 'Cookie' not in res['Vary'])
        logged_out_content = res.content

        c.login(username=self.admins[0], password='password')
        res = c.get(self.url + "catalog")

        self.assertEqual(res.status_code, 200)
        self.assertTrue('Vary' not in res or 'Cookie' not in res['Vary'])
        logged_in_content = res.content

        self.assertEqual("\n".join(difflib.context_diff(logged_out_content.split("\n"), logged_in_content.split("\n"))), "")

    def setUp(self):
        super(NoVaryOnCookieTest, self).setUp()

        #   Create a QSD page associated with the program
        from esp.qsd.models import QuasiStaticData
        from esp.web.models import NavBarCategory

        qsd_rec_new = QuasiStaticData()
        qsd_rec_new.name = "learn:index"
        qsd_rec_new.author = self.admins[0]
        qsd_rec_new.nav_category = default_navbarcategory()
        qsd_rec_new.content = "This is the content of the test QSD page"
        qsd_rec_new.title = "Test QSD page"
        qsd_rec_new.description = ""
        qsd_rec_new.keywords = ""
        qsd_rec_new.save()


class JavascriptSyntaxTest(TestCase):

    def runTest(self, display=False):

        #   Determine if the Closure compiler is installed and give up if it isn't
        if hasattr(settings, 'CLOSURE_COMPILER_PATH'):
            closure_path = settings.CLOSURE_COMPILER_PATH.rstrip('/') + '/'
        else:
            closure_path = ''
        if not os.path.exists('%scompiler.jar' % closure_path):
            if display: logger.info('Closure compiler not found.  Checked CLOSURE_COMPILER_PATH ="%s"', closure_path)
            return

        closure_output_code = tempfile.gettempdir() + '/closure_output.js'
        closure_output_file = tempfile.gettempdir() + 'closure.out'

        base_path = settings.MEDIA_ROOT + 'scripts/'
        exclude_names = ['yui', 'extjs', 'jquery', 'showdown']

        #   Walk the directory tree and try compiling
        path_gen = os.walk(base_path)
        num_files = 0
        file_list = []

        for path_tup in path_gen:
            dirpath = path_tup[0]
            dirnames = path_tup[1]
            filenames = path_tup[2]
            exclude = False
            for name in exclude_names:
                if name in dirpath:
                    exclude = True
                    break
            if not exclude:
                if display:
                    logger.info('Entering directory %s', dirpath)
                for file in filenames:
                    if not file.endswith('.js'):
                        continue
                    exclude = False
                    for name in exclude_names:
                        if name in file:
                            exclude = True
                            break
                    if exclude:
                        continue

                    file_list.append('%s/%s' % (dirpath, file))
                    num_files += 1

        file_args = ' '.join([('--js %s' % file) for file in file_list])
        os.system('java -jar %s/compiler.jar %s --js_output_file %s 2> %s' % (closure_path, file_args, closure_output_code, closure_output_file))
        checkfile = open(closure_output_file)

        results = [line.rstrip('\n') for line in checkfile.readlines() if len(line.strip()) > 0]

        if len(results) > 0:
            closure_result = results[-1].split(',')
            num_errors = int(closure_result[0].split()[0])
            num_warnings = int(closure_result[1].split()[0])

            logger.info('-- Displaying Closure results: %d Javascript syntax errors, %d warnings', num_errors, num_warnings)
            for line in results:
                logger.info(line)

            self.assertEqual(num_errors, 0, 'Closure compiler detected Javascript syntax errors')


