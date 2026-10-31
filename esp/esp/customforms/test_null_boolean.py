"""
Tests for Yes/No/Unknown (null_boolean) questions on custom forms (#6227).
"""

import json

from esp.customforms.models import Form
from esp.customforms.DynamicModel import DynamicModelHandler
from esp.users.models import ESPUser
from esp.tests.util import CacheFlushTestCase as TestCase


class NullBooleanQuestionTest(TestCase):
    """Yes, No and Unknown answers are accepted or rejected as `required` says."""

    #   (label, required, attrs)
    FIELD_SPECS = [
        ('Optional', False, {}),
        ('Required', True, {}),
        ('Quiz', False, {'correct_answer': 'Yes'}),
    ]

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='nullbool_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.student, _ = ESPUser.objects.get_or_create(username='nullbool_student')
        self.student.set_password('password')
        self.student.save()
        self.student.makeRole('Student')

        form_data = {
            'title': 'Null Boolean Test Form',
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
                        {'data': {'field_type': 'null_boolean', 'question_text': label,
                                  'required': required, 'attrs': attrs, 'seq': seq,
                                  'parent_id': -1, 'help_text': ''}}
                        for seq, (label, required, attrs) in enumerate(self.FIELD_SPECS)
                    ],
                }],
            }],
        }
        self.client.login(username='nullbool_admin', password='password')
        response = self.client.post('/customforms/submit/', json.dumps(form_data),
                                    content_type='application/json',
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        self.form = Form.objects.get(title='Null Boolean Test Form')
        self.field_ids = {field.label: field.id for field in self.form.field_set.all()}
        self.client.login(username='nullbool_student', password='password')

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def question(self, label):
        return f'question_{self.field_ids[label]}'

    def submit(self, **answers):
        """POST the form with these answers (by label) on top of valid defaults."""
        values = {'Required': 'true', 'Quiz': 'true'}
        values.update(answers)
        post_data = {'combo_form-current_step': '0'}
        post_data.update({self.question(label): value for label, value in values.items()})
        return self.client.post(f'/customforms/view/{self.form.id}/', post_data)

    def assertSaved(self, response, **expected):
        self.assertRedirects(response, f'/customforms/success/{self.form.id}/',
                             fetch_redirect_response=False)
        row = DynamicModelHandler(self.form).createDynModel().objects.get(user=self.student)
        for label, value in expected.items():
            self.assertIs(getattr(row, self.question(label)), value)

    def assertFieldError(self, response, label, message):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].errors.get(self.question(label)), [message])

    def test_form_offers_yes_no_and_unknown(self):
        response = self.client.get(f'/customforms/view/{self.form.id}/')
        self.assertEqual(response.status_code, 200)
        #   Every question offers the values that NullBooleanSelect understands.
        self.assertContains(response, '<option value="unknown" selected>Unknown</option>',
                            count=len(self.FIELD_SPECS))
        self.assertContains(response, '<option value="true">Yes</option>', count=len(self.FIELD_SPECS))
        self.assertContains(response, '<option value="false">No</option>', count=len(self.FIELD_SPECS))

    def test_optional_question_saves_yes_no_and_unknown(self):
        for value, expected in (('true', True), ('false', False), ('unknown', None), ('', None)):
            with self.subTest(value=value):
                self.assertSaved(self.submit(Optional=value), Optional=expected)

    def test_required_question_saves_yes_and_no(self):
        for value, expected in (('true', True), ('false', False)):
            with self.subTest(value=value):
                self.assertSaved(self.submit(Required=value), Required=expected)

    def test_required_question_rejects_unknown_and_blank(self):
        for value in ('unknown', ''):
            with self.subTest(value=value):
                self.assertFieldError(self.submit(Required=value), 'Required',
                                      'This field is required.')

    def test_correct_answer_is_checked(self):
        self.assertFieldError(self.submit(Quiz='false'), 'Quiz', 'Incorrect answer.')
        self.assertSaved(self.submit(Quiz='true'), Quiz=True)
