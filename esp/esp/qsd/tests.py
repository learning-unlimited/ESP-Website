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
from django.urls import reverse

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


class QSDImageUploadTest(TestCase):
    """Tests for the ajax_qsd_image_upload endpoint (#2679)."""

    UPLOAD_URL = '/admin/ajax_qsd_image_upload/'

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='upload_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.student, _ = ESPUser.objects.get_or_create(username='upload_student')
        self.student.set_password('password')
        self.student.save()

        # Track files created during tests for cleanup
        self._created_files = []

    def tearDown(self):
        import os
        for path in self._created_files:
            if os.path.exists(path):
                os.remove(path)

    def _make_image_file(self, name='test.png', size=100, content_type='image/png'):
        """Create a minimal in-memory image file for upload testing."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        # Minimal valid 1x1 PNG (67 bytes)
        png_header = (
            b'\x89PNG\r\n\x1a\n'  # PNG signature
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde'
            b'\x00\x00\x00\x0cIDATx'
            b'\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05'
            b'\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        content = png_header
        if size > len(png_header):
            # Pad to desired size (file won't be valid PNG but extension check is what matters)
            content = png_header + b'\x00' * (size - len(png_header))
        return SimpleUploadedFile(name, content, content_type=content_type)

    def _track_response_files(self, response):
        """Extract file paths from successful upload response for cleanup."""
        import json
        import os
        from django.conf import settings
        if response.status_code == 200:
            data = json.loads(response.content)
            if data.get('success') and data.get('data', {}).get('files'):
                for url in data['data']['files']:
                    # Convert URL to filesystem path
                    rel_path = url.lstrip('/')
                    if rel_path.startswith('media/'):
                        rel_path = rel_path[len('media/'):]
                    full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
                    self._created_files.append(full_path)

    def test_upload_requires_authentication(self):
        """Anonymous users get 401."""
        self.client.logout()
        f = self._make_image_file()
        response = self.client.post(self.UPLOAD_URL, {'files[0]': f})
        self.assertEqual(response.status_code, 401)

    def test_upload_requires_admin(self):
        """Non-admin users get 403."""
        self.client.login(username='upload_student', password='password')
        f = self._make_image_file()
        response = self.client.post(self.UPLOAD_URL, {'files[0]': f})
        self.assertEqual(response.status_code, 403)

    def test_upload_rejects_get(self):
        """GET requests get 405."""
        self.client.login(username='upload_admin', password='password')
        response = self.client.get(self.UPLOAD_URL)
        self.assertEqual(response.status_code, 405)

    def test_upload_rejects_no_files(self):
        """POST with no files gets 400."""
        self.client.login(username='upload_admin', password='password')
        response = self.client.post(self.UPLOAD_URL, {})
        self.assertEqual(response.status_code, 400)

    def test_upload_rejects_invalid_extension(self):
        """Files with disallowed extensions are rejected."""
        self.client.login(username='upload_admin', password='password')
        f = self._make_image_file(name='malicious.exe', content_type='application/x-executable')
        response = self.client.post(self.UPLOAD_URL, {'files[0]': f})
        self.assertEqual(response.status_code, 400)
        import json
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('.exe', data['data']['messages'][0])

    def test_upload_rejects_non_image_content_type(self):
        """Files with non-image content type are rejected."""
        self.client.login(username='upload_admin', password='password')
        f = self._make_image_file(name='script.png', content_type='text/html')
        response = self.client.post(self.UPLOAD_URL, {'files[0]': f})
        self.assertEqual(response.status_code, 400)
        import json
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('does not appear to be an image', data['data']['messages'][0])

    def test_upload_rejects_oversized_file(self):
        """Files exceeding 5MB are rejected."""
        self.client.login(username='upload_admin', password='password')
        f = self._make_image_file(size=6 * 1024 * 1024)  # 6 MB
        response = self.client.post(self.UPLOAD_URL, {'files[0]': f})
        self.assertEqual(response.status_code, 400)
        import json
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('size limit', data['data']['messages'][0])

    def test_upload_valid_png(self):
        """A valid PNG upload succeeds and returns correct JSON."""
        import json
        import os
        from django.conf import settings

        self.client.login(username='upload_admin', password='password')
        f = self._make_image_file(name='photo.png')
        response = self.client.post(self.UPLOAD_URL, {'files[0]': f})
        self._track_response_files(response)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['files']), 1)
        self.assertEqual(data['data']['isImages'], [True])

        # Verify the URL looks correct
        image_url = data['data']['files'][0]
        self.assertTrue(image_url.startswith('/media/uploaded/qsd_images/'))
        self.assertTrue(image_url.endswith('.png'))

        # Verify file actually exists on disk
        rel_path = image_url.lstrip('/')[len('media/'):]  # strip /media/
        full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        self.assertTrue(os.path.exists(full_path))

    def test_upload_valid_jpg(self):
        """A valid JPG upload succeeds."""
        import json
        self.client.login(username='upload_admin', password='password')
        f = self._make_image_file(name='photo.jpg', content_type='image/jpeg')
        response = self.client.post(self.UPLOAD_URL, {'files[0]': f})
        self._track_response_files(response)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(data['data']['files'][0].endswith('.jpg'))

    def test_upload_valid_gif(self):
        """A valid GIF upload succeeds."""
        import json
        self.client.login(username='upload_admin', password='password')
        f = self._make_image_file(name='animated.gif', content_type='image/gif')
        response = self.client.post(self.UPLOAD_URL, {'files[0]': f})
        self._track_response_files(response)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(data['data']['files'][0].endswith('.gif'))

    def test_upload_valid_webp(self):
        """A valid WebP upload succeeds."""
        import json
        self.client.login(username='upload_admin', password='password')
        f = self._make_image_file(name='modern.webp', content_type='image/webp')
        response = self.client.post(self.UPLOAD_URL, {'files[0]': f})
        self._track_response_files(response)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(data['data']['files'][0].endswith('.webp'))

    def test_upload_generates_uuid_filename(self):
        """Uploaded files get UUID filenames, not the original name."""
        import json
        self.client.login(username='upload_admin', password='password')
        f = self._make_image_file(name='../../etc/passwd.png')
        response = self.client.post(self.UPLOAD_URL, {'files[0]': f})
        self._track_response_files(response)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        image_url = data['data']['files'][0]
        filename = image_url.split('/')[-1]
        # UUID hex is 32 chars + .png = should not contain original name
        self.assertNotIn('passwd', filename)
        self.assertNotIn('..', filename)
        self.assertEqual(len(filename), 32 + 4)  # uuid hex + .png

    def test_upload_rejects_no_extension(self):
        """Files without extensions are rejected."""
        self.client.login(username='upload_admin', password='password')
        f = self._make_image_file(name='noextension')
        response = self.client.post(self.UPLOAD_URL, {'files[0]': f})
        self.assertEqual(response.status_code, 400)

    def test_multi_file_bad_second_no_orphan(self):
        """When one file in a batch fails validation, no files are saved.

        Uses non-'files[0]' keys to trigger the fallback collection path
        that gathers files from all request.FILES keys.
        """
        import os
        from django.conf import settings

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploaded/qsd_images')
        # Snapshot existing files before the request
        before = set(os.listdir(upload_dir)) if os.path.exists(upload_dir) else set()

        self.client.login(username='upload_admin', password='password')
        good = self._make_image_file(name='valid.png')
        bad = self._make_image_file(name='evil.exe', content_type='application/x-executable')
        # Use keys other than 'files[0]' so the fallback loop collects both
        response = self.client.post(self.UPLOAD_URL, {
            'upload_a': good,
            'upload_b': bad,
        })
        self.assertEqual(response.status_code, 400)

        # Verify no NEW files were created on disk
        after = set(os.listdir(upload_dir)) if os.path.exists(upload_dir) else set()
        new_files = after - before
        self.assertEqual(new_files, set(), "Orphaned files found after failed batch upload: %s" % new_files)
class QSDAdminAuthorTest(TestCase):

    def setUp(self):
        # Create two superusers
        self.user1 = ESPUser.objects.create_superuser(
            username="user1",
            email="user1@test.com",
            password="password123"
        )
        self.user2 = ESPUser.objects.create_superuser(
            username="user2",
            email="user2@test.com",
            password="password123"
        )

        self.nav_category = NavBarCategory.objects.create(
            name="default"
        )

        # Create initial QSD object with all required fields
        self.qsd = QuasiStaticData.objects.create(
            title="Test QSD",
            name="test_qsd",
            url="test-url",
            content="Test content",
            author=self.user1,
            nav_category=self.nav_category,
        )

    def test_admin_updates_author_on_edit(self):
        self.client.login(username="user2", password="password123")

        url = reverse(
                "admin:qsd_quasistaticdata_change",
                args=[self.qsd.pk]
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Build clean POST data manually
        form_data = {
            "title": "Updated Title",
            "name": self.qsd.name,
            "url": self.qsd.url,
            "content": self.qsd.content,
            "nav_category": self.nav_category.pk,
            "disabled": self.qsd.disabled,
            "_save": "Save",
        }

        response = self.client.post(url, form_data)

        # Must redirect on success
        self.assertEqual(response.status_code, 302)

        self.qsd.refresh_from_db()
        self.assertEqual(self.qsd.author, self.user2)
