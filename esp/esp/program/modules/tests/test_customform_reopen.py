import json

from esp.customforms.DynamicModel import DynamicModelHandler
from esp.customforms.models import Form
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.users.models import ESPUser, Record, RecordType


class CustomFormReopenTest(ProgramFrameworkTest):
    """Reopening a completed module custom form pre-fills the saved answers."""

    def setUp(self):
        super().setUp()
        self.add_user_profiles()
        admin, _ = ESPUser.objects.get_or_create(username='cfadmin')
        admin.set_password('password')
        admin.save()
        admin.makeAdmin()
        self.client.login(username='cfadmin', password='password')
        field = {'field_type': 'textField', 'seq': 0, 'required': True, 'parent_id': -1, 'help_text': '',
                 'attrs': {'correct_answer': '', 'charlimits': ','}}
        form_data = {
            'title': 'Reopen Test Form', 'perms': '', 'link_id': -1, 'link_type': '-1',
            'success_url': '/formsuccess.html', 'success_message': 'Thank you!',
            'anonymous': False, 'desc': 'Test',
            # Two pages, so every wizard step gets pre-filled.
            'pages': [{'parent_id': -1, 'seq': seq, 'sections': [{
                'data': {'help_text': '', 'question_text': '', 'seq': 0},
                'fields': [{'data': dict(field, question_text=label)}],
            }]} for seq, label in enumerate(['Nickname', 'Hometown'])],
        }
        self.client.post('/customforms/submit/', json.dumps(form_data), content_type='application/json',
                         HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.client.logout()
        self.form = Form.objects.get(title='Reopen Test Form')
        self.fields = {f.label: f for f in self.form.field_set.all()}
        self.response_model = DynamicModelHandler(self.form).createDynModel()

    def tearDown(self):
        DynamicModelHandler(self.form).purgeDynModel()
        super().tearDown()

    def _complete_form(self, user, event):
        self.response_model.objects.create(**{
            'user': user,
            'question_%d' % self.fields['Nickname'].id: 'Tay',
            'question_%d' % self.fields['Hometown'].id: 'Boston',
        })
        Record.objects.create(user=user, program=self.program, event=RecordType.objects.get(name=event))

    def test_teacher_custom_form(self):
        Tag.setTag(key='teach_extraform_id', value=self.form.id, target=self.program)
        teacher = self.teachers[0]
        self._complete_form(teacher, 'teacher_extra_form_done')
        self.client.login(username=teacher.username, password='password')
        response = self.client.get('/teach/%s/extraform' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Tay"')

    def test_student_custom_form(self):
        Tag.setTag(key='learn_extraform_id', value=self.form.id, target=self.program)
        student = self.students[0]
        self._complete_form(student, 'student_extra_form_done')
        self.client.login(username=student.username, password='password')
        response = self.client.get('/learn/%s/extraform' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Tay"')

    def test_teacher_quiz(self):
        Tag.setTag(key='quiz_form_id', value=self.form.id, target=self.program)
        teacher = self.teachers[0]
        self._complete_form(teacher, 'teacher_quiz_done')
        self.client.login(username=teacher.username, password='password')
        response = self.client.get('/teach/%s/quiz' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Tay"')
