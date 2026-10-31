"""
Tests that the custom forms views answer missing, malformed or unknown ids
with a 400 or 404 rather than a server error (#6229).
"""

from esp.customforms.models import Form, Field, Page, Section
from esp.customforms.DynamicModel import DynamicModelHandler
from esp.users.models import ESPUser
from esp.tests.util import CacheFlushTestCase as TestCase

AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}


class CustomFormsViewErrorsTest(TestCase):

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='viewerr_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.student, _ = ESPUser.objects.get_or_create(username='viewerr_student')
        self.student.set_password('password')
        self.student.save()
        self.student.makeRole('Student')

        self.form = Form.objects.create(
            title='View Errors Test Form', description='', created_by=self.admin,
            link_type='-1', link_id=-1, anonymous=False, perms='',
            success_message='OK', success_url='/')
        page = Page.objects.create(form=self.form, seq=0)
        section = Section.objects.create(page=page, title='', seq=0)
        self.field = Field.objects.create(form=self.form, section=section,
                                          field_type='textField', seq=0, label='Q1',
                                          required=False)
        DynamicModelHandler(self.form).createTable()

        self.client.login(username='viewerr_admin', password='password')

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def test_submit_and_modify_reject_get_and_non_ajax_requests(self):
        for url in ('/customforms/submit/', '/customforms/modify/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, **AJAX).status_code, 400)
                self.assertEqual(self.client.post(url, '{}', content_type='application/json').status_code, 400)

    def test_success_page_for_unknown_form_is_not_found(self):
        self.assertEqual(self.client.get('/customforms/success/999999/').status_code, 404)

    def test_getperms_without_prog_id_is_bad_request(self):
        response = self.client.get('/customforms/getperms/', **AJAX)
        self.assertEqual(response.status_code, 400)

    def test_getperms_for_unknown_program_is_not_found(self):
        response = self.client.get('/customforms/getperms/', {'prog_id': 999999}, **AJAX)
        self.assertEqual(response.status_code, 404)

    def test_getperms_requires_a_form_builder_user(self):
        for username in (None, 'viewerr_student'):
            with self.subTest(username=username):
                self.client.logout()
                if username:
                    self.client.login(username=username, password='password')
                response = self.client.get('/customforms/getperms/', {'prog_id': 999999}, **AJAX)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith('/accounts/login/'))

    def test_getmodules_with_non_numeric_program_is_bad_request(self):
        response = self.client.get('/customforms/getmodules/', {'program': 'abc'}, **AJAX)
        self.assertEqual(response.status_code, 400)

    def test_bulk_download_of_unknown_question_is_not_found(self):
        DynamicModelHandler(self.form).createDynModel().objects.create(
            user=self.student, **{f'question_{self.field.id}': 'an answer'})
        response = self.client.get('/customforms/bulkdownloadfiles/', {
            'form_id': self.form.id, 'question_name': 'question_999999'})
        self.assertEqual(response.status_code, 404)
