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

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.qsd.models import QuasiStaticData
from esp.web.models import NavBarCategory, default_navbarcategory
from esp.users.models import ESPUser

from django.template import Template, Context
from reversion import revisions as reversion
from reversion.models import Version
import json

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
        new_admin.makeRole('Administrator')
        new_student, created = ESPUser.objects.get_or_create(username='qsd_student')
        new_student.set_password('password')
        new_student.save()
        self.users = [None, (new_admin, 'password'), (new_student, 'password')]
        self.author = new_admin

    def testInlineCorrectness(self):

        for user in self.users:
            if user is None:
                self.client.logout()
            else:
                self.client.logout()
                self.client.login(username=user[0], password=user[1])

            #   Create an inline QSD
            qsd_rec_new = QuasiStaticData()
            qsd_rec_new.url = 'learn/bar'
            qsd_rec_new.name = "learn:bar"
            qsd_rec_new.author = self.author
            qsd_rec_new.nav_category = default_navbarcategory()
            qsd_rec_new.content = "Inline Testing 123"
            qsd_rec_new.title = "Test QSD page"
            qsd_rec_new.description = ""
            qsd_rec_new.keywords = ""
            qsd_rec_new.save()

            #   Render a template that uses the inline_qsd template tag
            template_data = """
                {% load render_qsd %}
                {% render_inline_qsd "learn/bar" %}
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

            #   Delete it so we can start again
            qsd_rec_new.delete()

    def testPageCorrectness(self):

        for user in self.users:
            if user is None:
                self.client.logout()
            else:
                self.client.logout()
                self.client.login(username=user[0], password=user[1])

            #   Check that QSD with desired URL does not exist
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 404)

            #   Create QSD with desired URL
            qsd_rec_new = QuasiStaticData()
            qsd_rec_new.url = 'learn/foo'
            qsd_rec_new.name = "learn:foo"
            qsd_rec_new.author = self.author
            qsd_rec_new.nav_category = default_navbarcategory()
            qsd_rec_new.content = "Testing 123"
            qsd_rec_new.title = "Test QSD page"
            qsd_rec_new.description = ""
            qsd_rec_new.keywords = ""
            qsd_rec_new.save()

            #   Check that page now exists and has proper content
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue('Testing 123' in str(response.content, encoding='UTF-8'))

            #   Edit QSD and check that page content has updated
            qsd_rec_new.content = "Testing 456"
            qsd_rec_new.save()
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue('Testing 456' in str(response.content, encoding='UTF-8'))

            #   Delete the new QSD so we can start again.
            qsd_rec_new.delete()


class QSDVersionHistoryTest(TestCase):
    """ Tests for QSD version history endpoints. """

    def setUp(self):
        self.admin, created = ESPUser.objects.get_or_create(username='qsd_history_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.student, created = ESPUser.objects.get_or_create(username='qsd_history_student')
        self.student.set_password('password')
        self.student.save()

        # Create a QSD with two revisions
        with reversion.create_revision():
            self.qsd = QuasiStaticData()
            self.qsd.url = 'learn/historytest'
            self.qsd.name = ''
            self.qsd.author = self.admin
            self.qsd.nav_category = default_navbarcategory()
            self.qsd.content = 'Version One Content'
            self.qsd.title = 'History Test'
            self.qsd.description = ''
            self.qsd.keywords = ''
            self.qsd.save()
            reversion.set_user(self.admin)

        with reversion.create_revision():
            self.qsd.content = 'Version Two Content'
            self.qsd.save()
            reversion.set_user(self.admin)

    def test_history_requires_permission(self):
        """ Non-editors cannot see version history. """
        self.client.login(username='qsd_history_student', password='password')
        response = self.client.get('/admin/ajax_qsd_history', {'url': 'learn/historytest'})
        self.assertEqual(response.status_code, 403)

    def test_history_returns_versions(self):
        """ Admins can see version list in correct order. """
        self.client.login(username='qsd_history_admin', password='password')
        response = self.client.get('/admin/ajax_qsd_history', {'url': 'learn/historytest'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertGreaterEqual(len(data['versions']), 2)
        # Most recent first
        self.assertIn('Version Two', data['versions'][0]['snippet'])

    def test_history_empty_for_nonexistent(self):
        """ Returns empty list for QSD URL with no history. """
        self.client.login(username='qsd_history_admin', password='password')
        response = self.client.get('/admin/ajax_qsd_history', {'url': 'learn/doesnotexist'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['versions']), 0)

    def test_version_preview(self):
        """ Can preview a specific version's content. """
        self.client.login(username='qsd_history_admin', password='password')
        # Get version list to find version_id
        response = self.client.get('/admin/ajax_qsd_history', {'url': 'learn/historytest'})
        versions = json.loads(response.content)['versions']
        old_version_id = versions[-1]['version_id']

        response = self.client.get('/admin/ajax_qsd_version_preview', {'version_id': old_version_id})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('Version One', data['content_raw'])
        self.assertIn('Version One', data['content_html'])

    def test_version_preview_requires_permission(self):
        """ Non-editors cannot preview versions. """
        self.client.login(username='qsd_history_student', password='password')
        # Get a valid version_id using admin first
        self.client.login(username='qsd_history_admin', password='password')
        response = self.client.get('/admin/ajax_qsd_history', {'url': 'learn/historytest'})
        versions = json.loads(response.content)['versions']
        version_id = versions[0]['version_id']

        self.client.login(username='qsd_history_student', password='password')
        response = self.client.get('/admin/ajax_qsd_version_preview', {'version_id': version_id})
        self.assertEqual(response.status_code, 403)

    def test_restore_version(self):
        """ Restoring a version creates a new revision with old content. """
        self.client.login(username='qsd_history_admin', password='password')
        # Get version list
        response = self.client.get('/admin/ajax_qsd_history', {'url': 'learn/historytest'})
        versions = json.loads(response.content)['versions']
        old_version_id = versions[-1]['version_id']

        # Current content should be Version Two
        current = QuasiStaticData.objects.get_by_url('learn/historytest')
        self.assertIn('Version Two', current.content)

        # Restore to old version
        response = self.client.post('/admin/ajax_qsd_restore', {'version_id': old_version_id})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 1)

        # Verify content reverted
        updated = QuasiStaticData.objects.get_by_url('learn/historytest')
        self.assertIn('Version One', updated.content)

        # Verify a new revision was created (now 3 total)
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(QuasiStaticData)
        version_count = Version.objects.filter(
            content_type=ct,
            object_id=str(self.qsd.pk),
        ).count()
        self.assertGreaterEqual(version_count, 3)

    def test_restore_requires_post(self):
        """ Restore endpoint rejects GET. """
        self.client.login(username='qsd_history_admin', password='password')
        response = self.client.get('/admin/ajax_qsd_restore', {'version_id': 1})
        self.assertEqual(response.status_code, 405)

    def test_restore_requires_permission(self):
        """ Non-editors cannot restore versions. """
        self.client.login(username='qsd_history_admin', password='password')
        response = self.client.get('/admin/ajax_qsd_history', {'url': 'learn/historytest'})
        versions = json.loads(response.content)['versions']
        version_id = versions[0]['version_id']

        self.client.login(username='qsd_history_student', password='password')
        response = self.client.post('/admin/ajax_qsd_restore', {'version_id': version_id})
        self.assertEqual(response.status_code, 403)

    def test_history_includes_author(self):
        """ Version entries include the author username. """
        self.client.login(username='qsd_history_admin', password='password')
        response = self.client.get('/admin/ajax_qsd_history', {'url': 'learn/historytest'})
        data = json.loads(response.content)
        self.assertEqual(data['versions'][0]['author'], 'qsd_history_admin')

    def tearDown(self):
        QuasiStaticData.objects.filter(url='learn/historytest').delete()

