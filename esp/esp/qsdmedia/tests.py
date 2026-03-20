__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2013 by the individual contributors
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

from esp.qsdmedia.models import Media
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser

from django.core.files.uploadhandler import MemoryFileUploadHandler, StopFutureHandlers
from django.core.files.uploadedfile import SimpleUploadedFile

class QSDMediaTest(TestCase):
    def test_upload(self):
        #   Pretend to upload a file
        file_data = "here is some test data"
        file_size = len(file_data)
        handler = MemoryFileUploadHandler()
        handler.handle_raw_input(file_data, None, file_size, None)
        try:
            handler.new_file('test', 'test_file.txt', 'text/plain', file_size)
        except StopFutureHandlers:
            pass
        file = handler.file_complete(file_size)
        media = Media(friendly_name = 'Test QSD Media')
        media.handle_file(file, file.name)
        media.save()

        #   Check that the file can be downloaded from the proper link
        url = f'/download/{media.hashed_name}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        #   Delete the QSD Media object
        media.delete()

        #   Check that the file can no longer be downloaded
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

class SiteMediaTest(TestCase):
    def setUp(self):
        super().setUp()
        self.admin_user, _ = ESPUser.objects.get_or_create(username='admin_user')
        self.admin_user.set_password('password')
        self.admin_user.save()
        self.admin_user.makeAdmin()

        self.student_user, _ = ESPUser.objects.get_or_create(username='student_user')
        self.student_user.set_password('password')
        self.student_user.save()
        self.student_user.makeRole('Student')

    def test_admin_access_required(self):
        # Unauthenticated: should redirect to login
        response = self.client.get('/manage/site_media/')
        self.assertRedirects(response, '/accounts/login/?next=/manage/site_media/')

        # Student: should not have access
        self.client.login(username='student_user', password='password')
        response = self.client.get('/manage/site_media/')
        self.assertEqual(response.status_code, 403)

        # Admin: should be able to access
        self.client.login(username='admin_user', password='password')
        response = self.client.get('/manage/site_media/')
        self.assertEqual(response.status_code, 200)

    def test_add_site_media(self):
        self.client.login(username='admin_user', password='password')

        test_file = SimpleUploadedFile("test_add.txt", b"site media content")
        response = self.client.post('/manage/site_media/', {
            'command': 'add',
            'title': 'New Site Media',
            'uploadedfile': test_file
        }, follow=False)
        self.assertRedirects(response, '/manage/site_media/')

        # Verify it was created as site media
        media = Media.objects.get(friendly_name='New Site Media')
        self.assertIsNone(media.owner_type)
        self.assertIsNone(media.owner_id)

    def test_rename_site_media(self):
        self.client.login(username='admin_user', password='password')

        media = Media(friendly_name='Old Title')
        media.save()

        response = self.client.post('/manage/site_media/', {
            'command': 'rename',
            'docid': media.id,
            'title': 'Renamed Title'
        }, follow=False)
        self.assertRedirects(response, '/manage/site_media/')

        media.refresh_from_db()
        self.assertEqual(media.friendly_name, 'Renamed Title')

    def test_delete_site_media(self):
        self.client.login(username='admin_user', password='password')

        media = Media(friendly_name='To Delete')
        media.save()

        self.assertEqual(Media.objects.count(), 1)
        response = self.client.post('/manage/site_media/', {
            'command': 'delete',
            'docid': media.id
        }, follow=False)
        self.assertRedirects(response, '/manage/site_media/')

        self.assertEqual(Media.objects.count(), 0)

    def test_only_operates_on_site_media(self):
        self.client.login(username='admin_user', password='password')

        # Create a non-site media object
        non_site_media = Media(
            friendly_name='Not Site Media',
            owner_type_id=1,
            owner_id=1
        )
        non_site_media.save()

        # Try to rename — should fail silently (not site media)
        self.client.post('/manage/site_media/', {
            'command': 'rename',
            'docid': non_site_media.id,
            'title': 'Trying to Rename'
        }, follow=False)

        non_site_media.refresh_from_db()
        self.assertEqual(non_site_media.friendly_name, 'Not Site Media')

        # Try to delete — should fail silently (not site media)
        self.client.post('/manage/site_media/', {
            'command': 'delete',
            'docid': non_site_media.id
        }, follow=False)

        self.assertEqual(Media.objects.filter(id=non_site_media.id).count(), 1)
