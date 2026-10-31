"""
Tests for file-upload questions on custom forms (#6226).
"""

import io
import json
import os
import shutil
import tempfile
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from esp.customforms.models import Form
from esp.customforms.DynamicModel import DynamicModelHandler
from esp.users.models import ESPUser
from esp.tests.util import CacheFlushTestCase as TestCase


class FileUploadQuestionTest(TestCase):
    """A file question can be answered, and the uploads can be downloaded."""

    def setUp(self):
        #   Keep everything the form wizard and the response table write out of
        #   the repository's public/media directory.
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        media_override = override_settings(MEDIA_ROOT=self.media_root)
        media_override.enable()
        self.addCleanup(media_override.disable)

        self.admin, _ = ESPUser.objects.get_or_create(username='upload_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.student, _ = ESPUser.objects.get_or_create(username='upload_student')
        self.student.set_password('password')
        self.student.save()
        self.student.makeRole('Student')

        form_data = {
            'title': 'File Upload Test Form',
            'desc': '',
            'perms': '',
            'link_type': '-1',
            'link_id': -1,
            'success_url': '/formsuccess.html',
            'success_message': 'Thank you!',
            'anonymous': False,
            'pages': [{
                'parent_id': -1,
                'seq': 0,
                'sections': [{
                    'data': {'question_text': '', 'help_text': '', 'seq': 0},
                    'fields': [
                        {'data': {'field_type': 'file', 'question_text': 'Upload',
                                  'required': False, 'attrs': {}, 'seq': 0,
                                  'parent_id': -1, 'help_text': ''}},
                    ],
                }],
            }],
        }
        self.client.login(username='upload_admin', password='password')
        response = self.client.post('/customforms/submit/', json.dumps(form_data),
                                    content_type='application/json',
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        self.form = Form.objects.get(title='File Upload Test Form')
        self.question_name = f'question_{self.form.field_set.get().id}'
        self.upload_dir = os.path.join(self.media_root, 'uploaded', f'Response_{self.form.id}')

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def responses(self):
        return DynamicModelHandler(self.form).createDynModel().objects.all()

    def submit_file(self, name='notes.txt', content=b'hello'):
        self.client.login(username='upload_student', password='password')
        response = self.client.post(f'/customforms/view/{self.form.id}/', {
            'combo_form-current_step': '0',
            self.question_name: SimpleUploadedFile(name, content, content_type='text/plain'),
        })
        self.client.logout()
        return response

    def bulk_download(self):
        self.client.login(username='upload_admin', password='password')
        response = self.client.get('/customforms/bulkdownloadfiles/', {
            'form_id': self.form.id, 'question_name': self.question_name})
        self.client.logout()
        self.assertEqual(response.status_code, 200)
        return zipfile.ZipFile(io.BytesIO(response.content))

    def test_submission_saves_file_under_media_root(self):
        response = self.submit_file()
        self.assertRedirects(response, f'/customforms/success/{self.form.id}/',
                             fetch_redirect_response=False)

        response_row = self.responses().get(user=self.student)
        stored_name = getattr(response_row, self.question_name).name
        self.assertEqual(stored_name, f'uploaded/Response_{self.form.id}/notes.txt')
        with open(os.path.join(self.upload_dir, 'notes.txt'), 'rb') as stored_file:
            self.assertEqual(stored_file.read(), b'hello')

        #   The wizard's temporary copy is cleaned up once the response is saved.
        self.assertEqual(os.listdir(self.media_root), ['uploaded'])

    def test_bulk_download_includes_submitted_file(self):
        self.submit_file()
        archive = self.bulk_download()
        self.assertEqual(archive.namelist(), ['notes.txt'])
        self.assertEqual(archive.read('notes.txt'), b'hello')

    def test_bulk_download_includes_legacy_absolute_paths(self):
        """Responses saved by older versions stored an absolute path."""
        os.makedirs(self.upload_dir)
        legacy_path = os.path.join(self.upload_dir, 'legacy.txt')
        with open(legacy_path, 'wb') as legacy_file:
            legacy_file.write(b'old')
        self.responses().create(user=self.admin, **{self.question_name: legacy_path})
        self.submit_file()

        archive = self.bulk_download()
        self.assertEqual(sorted(archive.namelist()), ['legacy.txt', 'notes.txt'])
        self.assertEqual(archive.read('legacy.txt'), b'old')

    def test_bulk_download_skips_responses_without_a_file(self):
        self.responses().create(user=self.admin, **{self.question_name: ''})
        self.assertEqual(self.bulk_download().namelist(), [])
