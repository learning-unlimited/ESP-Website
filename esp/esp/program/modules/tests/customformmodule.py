from __future__ import absolute_import

import json

from esp.customforms.DynamicModel import DynamicModelHandler
from esp.customforms.models import Form
from esp.program.models import ProgramModule
from esp.tests.factories import make_program, make_user
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import Record, RecordType


class StudentCustomFormRelinkTest(TestCase):
    """ Regression tests for issue #3868: a custom form that already has
        responses is re-linked from one program to another.

        The registration page has to keep working for a student who both has an
        earlier response to the form and has already been marked as having
        completed the custom form step of the program it is re-linked to. """

    QUESTION = 'Favorite color'

    def setUp(self):
        self.admin = make_user('Administrator', username='relink_admin')
        self.student = make_user('Student', username='relink_student')
        modules = ProgramModule.objects.filter(
            handler__in=['StudentClassRegModule', 'StudentCustomFormModule'])
        self.prog_a = make_program(program_type='RelinkA', instance_name='2222_Summer',
                                   admin=self.admin, modules=modules)
        self.prog_b = make_program(program_type='RelinkB', instance_name='2222_Summer',
                                   admin=self.admin, modules=modules)

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def _form_payload(self, prog):
        return {
            'title': 'Relink Form',
            'desc': 'Test',
            'link_type': 'Program',
            'link_id': str(prog.id),
            'link_tl': 'learn',
            'link_module': 'StudentCustomFormModule',
            'anonymous': False,
            'perms': '',
            'success_message': 'Thanks',
            'success_url': '/',
            'pages': [{
                'parent_id': -1,
                'seq': 0,
                'sections': [{
                    'data': {'help_text': '', 'question_text': '', 'seq': 0, 'parent_id': -1},
                    'fields': [
                        {'data': {'field_type': 'textField', 'question_text': self.QUESTION,
                                  'seq': 0, 'required': True, 'parent_id': -1,
                                  'attrs': {'charlimits': '0,100'}, 'help_text': ''}},
                    ],
                }],
            }],
        }

    def _create_form(self):
        self.client.login(username=self.admin.username, password='password')
        response = self.client.post('/customforms/submit/',
                                    json.dumps(self._form_payload(self.prog_a)),
                                    content_type='application/json',
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        form = Form.objects.get(title='Relink Form')
        return form, form.field_set.all()[0]

    def _relink(self, form, field, prog):
        self.client.login(username=self.admin.username, password='password')
        payload = self._form_payload(prog)
        page = form.page_set.all()[0]
        payload['form_id'] = form.id
        payload['pages'][0]['parent_id'] = page.id
        payload['pages'][0]['sections'][0]['data']['parent_id'] = page.section_set.all()[0].id
        payload['pages'][0]['sections'][0]['fields'][0]['data']['parent_id'] = field.id
        response = self.client.post('/customforms/modify/', json.dumps(payload),
                                    content_type='application/json',
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200, msg=response.content)

    def _extraform_url(self, prog):
        return '/learn/%s/extraform' % prog.getUrlBase()

    def _fill_out(self, prog, field, answer):
        self.client.login(username=self.student.username, password='password')
        response = self.client.post(self._extraform_url(prog), {
            'student_custom_combo_form-current_step': '0',
            'question_%d' % field.id: answer,
            'link_Program': str(prog.id),
        })
        self.assertRedirects(response, '/learn/%s/studentreg' % prog.getUrlBase(),
                             fetch_redirect_response=False)

    def _responses(self, form):
        DynamicModelHandler(form).purgeDynModel()
        model = DynamicModelHandler(form).createDynModel()
        return list(model.objects.all().values())

    def test_revisiting_a_completed_form(self):
        """ Loading the form again pre-fills the previous answers. """
        form, field = self._create_form()
        self._fill_out(self.prog_a, field, 'blue')
        response = self.client.get(self._extraform_url(self.prog_a))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="blue"')

    def test_relinked_form_is_usable_by_a_student_with_an_old_response(self):
        form, field = self._create_form()
        self._fill_out(self.prog_a, field, 'blue')

        #   The student has already completed some custom form for program B
        rt = RecordType.objects.get(name='student_extra_form_done')
        Record.objects.create(user=self.student, program=self.prog_b, event=rt)

        self._relink(form, field, self.prog_b)

        self.client.login(username=self.student.username, password='password')
        response = self.client.get(self._extraform_url(self.prog_b))
        self.assertEqual(response.status_code, 200)
        #   The hidden link field must name the program the form is linked to
        #   now, not the one the old response was saved under
        self.assertContains(response, 'name="link_Program" value="%d"' % self.prog_b.id)
        self.assertContains(response, 'value="blue"')

        self._fill_out(self.prog_b, field, 'green')
        responses = self._responses(form)
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0]['link_Program_id'], self.prog_b.id)

    def test_relinking_preserves_responses(self):
        form, field = self._create_form()
        self._fill_out(self.prog_a, field, 'blue')
        before = self._responses(form)

        self._relink(form, field, self.prog_b)
        self._relink(form, field, self.prog_a)

        self.assertEqual(self._responses(form), before)
