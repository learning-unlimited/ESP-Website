__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2024 by the individual contributors
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
"""

from django.core.files.uploadedfile import SimpleUploadedFile

from esp.program.modules.base import ProgramModule
from esp.program.tests import ProgramFrameworkTest
from esp.qsdmedia.models import Media


def _make_uploaded_file(name='fixture.pdf'):
    """Return a fresh SimpleUploadedFile suitable for Media.handle_file()."""
    return SimpleUploadedFile(name, b'%PDF-1.4 content', content_type='application/pdf')


def _create_media_with_file(friendly_name, filename='fixture.pdf'):
    """Create and save a Media instance that has a real target_file attached.

    Media.delete() calls get_uploaded_filename() -> target_file.url, which
    raises ValueError when target_file is empty.  Using handle_file() here
    mirrors what the production code does and avoids that error in tests.
    """
    media = Media(friendly_name=friendly_name)
    media.handle_file(_make_uploaded_file(filename), filename)
    media.format = ''
    media.save()
    return media


class AdminMaterialsModuleTest(ProgramFrameworkTest):
    """Unit tests for AdminMaterials.get_materials (add / rename / delete)."""

    def setUp(self):
        super().setUp(
            modules=ProgramModule.objects.filter(handler='AdminMaterials'),
        )
        admin = self.admins[0]
        self.assertTrue(
            self.client.login(username=admin.username, password='password'),
            'Could not log in as admin %s' % admin.username,
        )
        self.url = '/manage/%s/get_materials' % self.program.getUrlBase()

    # ------------------------------------------------------------------
    # Upload (command='add')
    # ------------------------------------------------------------------

    def test_upload_creates_media_with_class_prefix(self):
        """Uploading a file for a class creates a Media object whose
        file_name is prefixed with the class emailcode."""
        cls = self.program.classes()[0]
        uploaded = SimpleUploadedFile('notes.pdf', b'%PDF-1.4 content', content_type='application/pdf')

        response = self.client.post(self.url, {
            'command': 'add',
            'title': 'Class Notes',
            'target_obj': cls.id,
            'uploadedfile': uploaded,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Media.objects.count(), 1)

        media = Media.objects.get()
        self.assertEqual(media.friendly_name, 'Class Notes')
        # file_name stores the desired_filename passed to handle_file
        self.assertTrue(
            media.file_name.startswith(cls.emailcode() + '_'),
            'Expected file_name to start with "%s_", got "%s"' % (cls.emailcode(), media.file_name),
        )

    def test_upload_program_level_file_has_no_class_prefix(self):
        """Uploading a program-level file (target_obj=0) does not prepend
        any class emailcode to the stored file_name."""
        uploaded = SimpleUploadedFile('waiver.pdf', b'%PDF-1.4 content', content_type='application/pdf')

        response = self.client.post(self.url, {
            'command': 'add',
            'title': 'Liability Waiver',
            'target_obj': 0,
            'uploadedfile': uploaded,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Media.objects.count(), 1)

        media = Media.objects.get()
        self.assertEqual(media.file_name, 'waiver.pdf')
        self.assertEqual(media.owner, self.program)

    # ------------------------------------------------------------------
    # Rename (command='rename')
    # ------------------------------------------------------------------

    def test_rename_updates_friendly_name(self):
        """POSTing command='rename' with a new title updates friendly_name."""
        media = _create_media_with_file('old_name')

        response = self.client.post(self.url, {
            'command': 'rename',
            'docid': media.id,
            'title': 'new_name',
        })

        self.assertEqual(response.status_code, 200)
        media.refresh_from_db()
        self.assertEqual(media.friendly_name, 'new_name')

    # ------------------------------------------------------------------
    # Delete (command='delete')
    # ------------------------------------------------------------------

    def test_delete_removes_media_from_database(self):
        """POSTing command='delete' removes the Media record.

        The fixture must be created via handle_file() so that target_file
        is populated; Media.delete() calls target_file.url internally and
        raises ValueError when the field has no file associated with it.
        """
        media = _create_media_with_file('to_be_deleted')

        response = self.client.post(self.url, {
            'command': 'delete',
            'docid': media.id,
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Media.objects.filter(id=media.id).exists())
