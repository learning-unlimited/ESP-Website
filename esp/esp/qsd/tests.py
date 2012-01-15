
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
  Email: web-team@lists.learningu.org
"""

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.qsd.models import QuasiStaticData
from esp.web.models import NavBarCategory
from esp.datatree.models import GetNode
from esp.users.models import UserBit, ESPUser

from django.template import Template, Context

class QSDCorrectnessTest(TestCase):
    """ Tests to ensure that QSD-related caches are cleared appropriately. """

    def setUp(self):
        #   Determine URL for QSD page to be tested
        section = 'learn'
        pagename = 'foo'
        self.url = '/%s/%s.html' % (section, pagename)
        
        #   Create user to function as QSD author
        new_admin, created = ESPUser.objects.get_or_create(username='qsd_admin')
        new_admin.set_password('password')
        new_admin.save()
        role_bit, created = UserBit.objects.get_or_create(user=new_admin, verb=GetNode('V/Flags/UserRole/Administrator'), qsc=GetNode('Q'), recursive=False)
        self.author = new_admin
    
    def testInlineCorrectness(self):
        
        self.client.logout()
        
        #   Create an inline QSD
        qsd_rec_new = QuasiStaticData()
        qsd_rec_new.path = GetNode('Q/Programs')
        qsd_rec_new.name = "learn:bar"
        qsd_rec_new.author = self.author
        qsd_rec_new.nav_category = NavBarCategory.default()
        qsd_rec_new.content = "Inline Testing 123"
        qsd_rec_new.title = "Test QSD page"
        qsd_rec_new.description = ""
        qsd_rec_new.keywords = ""
        qsd_rec_new.save()
        
        #   Render a template that uses the inline_qsd template tag
        template_data = """
            {% load render_qsd %}
            {% render_inline_qsd "Q/Programs" "learn:bar" %}
        """
        template = Template(template_data)
        response_content = template.render(Context({}))
        self.assertTrue("Inline Testing 123" in response_content)
        
        #   Update the template and check again
        qsd_rec_new.content = "Inline Testing 456"
        qsd_rec_new.save()
        response_content = template.render(Context({}))
        self.assertTrue("Inline Testing 456" in response_content)
        
        response_content = template.render(Context({}))
        self.assertTrue("Inline Testing 456" in response_content)
        
    def testPageCorrectness(self):
        
        self.client.logout()
        
        #   Check that QSD with desired URL does not exist
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
        
        #   Create QSD with desired URL
        qsd_rec_new = QuasiStaticData()
        qsd_rec_new.path = GetNode('Q/Programs')
        qsd_rec_new.name = "learn:foo"
        qsd_rec_new.author = self.author
        qsd_rec_new.nav_category = NavBarCategory.default()
        qsd_rec_new.content = "Testing 123"
        qsd_rec_new.title = "Test QSD page"
        qsd_rec_new.description = ""
        qsd_rec_new.keywords = ""
        qsd_rec_new.save()
        
        #   Check that page now exists and has proper content
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Testing 123' in response.content)
        
        #   Edit QSD and check that page content has updated
        qsd_rec_new.content = "Testing 456"
        qsd_rec_new.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Testing 456' in response.content)
        
        
    
