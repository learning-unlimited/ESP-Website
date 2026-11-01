"""
Tests for viewing and exporting responses to anonymous custom forms (#6228).
"""

import io
import json

import openpyxl

from esp.customforms.models import Form
from esp.customforms.DynamicModel import DynamicModelHandler
from esp.users.models import ESPUser
from esp.tests.util import CacheFlushTestCase as TestCase


class AnonymousFormResponsesTest(TestCase):
    """The creator of an anonymous form can list and export its responses."""

    def setUp(self):
        super().setUp()
        self.admin, _ = ESPUser.objects.get_or_create(username='anonresp_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        form_data = {
            'title': 'Anonymous Responses Test Form',
            'desc': '',
            'perms': '',
            'link_type': '-1',
            'link_id': -1,
            'success_url': '/formsuccess.html',
            'success_message': 'Thank you!',
            'anonymous': True,
            'pages': [{
                'parent_id': -1,
                'seq': 0,
                'sections': [{
                    'data': {'question_text': '', 'help_text': '', 'seq': 0},
                    'fields': [
                        {'data': {'field_type': 'textField', 'question_text': 'Feedback',
                                  'required': True, 'attrs': {'charlimits': '0,100'},
                                  'seq': 0, 'parent_id': -1, 'help_text': ''}},
                    ],
                }],
            }],
        }
        self.client.login(username='anonresp_admin', password='password')
        response = self.client.post('/customforms/submit/', json.dumps(form_data),
                                    content_type='application/json',
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        self.form = Form.objects.get(title='Anonymous Responses Test Form')
        self.question_name = f'question_{self.form.field_set.get().id}'

        #   Respond while logged out
        response = self.client.post(f'/customforms/view/{self.form.id}/', {
            'combo_form-current_step': '0',
            self.question_name: 'Great program',
        })
        self.assertRedirects(response, f'/customforms/success/{self.form.id}/',
                             fetch_redirect_response=False)

        self.client.login(username='anonresp_admin', password='password')

    def tearDown(self):
        try:
            for form in Form.objects.all():
                DynamicModelHandler(form).purgeDynModel()
        finally:
            super().tearDown()

    def test_get_data_lists_responses_without_user_columns(self):
        response = self.client.get('/customforms/getData/', {'form_id': self.form.id},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['questions'], [[self.question_name, 'Feedback', 'textField']])
        self.assertEqual(len(data['answers']), 1)
        self.assertEqual(data['answers'][0][self.question_name], 'Great program')
        self.assertNotIn('user_id', data['answers'][0])

    def test_excel_export_includes_responses(self):
        response = self.client.get(f'/customforms/exceldata/{self.form.id}/')
        self.assertEqual(response.status_code, 200)
        sheet = openpyxl.load_workbook(io.BytesIO(response.content)).active
        self.assertEqual([list(row) for row in sheet.iter_rows(values_only=True)],
                         [['Feedback'], ['Great program']])
