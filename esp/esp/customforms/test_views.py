"""
Tests for the custom forms views: the form builder's AJAX endpoints, linking
forms to programs and registration modules, editing existing forms, filling
in single- and multi-page forms, answer checking, file questions, and
exporting responses.
"""

import json
import os
import tempfile
import zipfile
from io import BytesIO

import openpyxl
from django.db import connection

from esp.customforms.DynamicModel import DynamicModelHandler
from esp.customforms.models import Attribute, Field, Form
from esp.tagdict.models import Tag
from esp.tests.factories import make_class, make_program, make_user
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ContactInfo


MODULE_TAGS = {
    'StudentCustomFormModule': 'learn_extraform_id',
    'TeacherCustomFormModule': 'teach_extraform_id',
    'TeacherQuizModule': 'quiz_form_id',
}


def field_spec(ftype, label=None, seq=0, required=False, attrs=None, parent_id=-1):
    """ One field as the form builder sends it. """
    return {'data': {
        'field_type': ftype, 'question_text': label or ftype, 'seq': seq,
        'required': required, 'parent_id': parent_id, 'attrs': attrs or {},
        'help_text': '',
    }}


def page_spec(fields, seq=0, parent_id=-1, section_id=-1):
    """ One page with a single section holding the given fields. """
    return {'parent_id': parent_id, 'seq': seq, 'sections': [{
        'data': {'question_text': '', 'help_text': '', 'seq': 0, 'parent_id': section_id},
        'fields': fields,
    }]}


def form_spec(pages, title='Coverage Form', **extra):
    """ The metadata the form builder POSTs to create or modify a form. """
    spec = {
        'title': title, 'desc': 'A form', 'perms': '',
        'link_type': '-1', 'link_id': -1,
        'success_url': '/formsuccess.html', 'success_message': 'Thank you!',
        'anonymous': False, 'pages': pages,
    }
    spec.update(extra)
    return spec


class CustomFormViewTestCase(TestCase):
    """ Users and helpers shared by the view tests below. """

    def setUp(self):
        super().setUp()
        self.admin = make_user('Administrator', username='cfv_admin')
        self.teacher = make_user('Teacher', username='cfv_teacher')
        self.student = make_user('Student', username='cfv_student')

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()
        super().tearDown()

    def login(self, user):
        self.assertTrue(self.client.login(username=user.username, password='password'))

    def ajax_get(self, url, data=None):
        return self.client.get(url, data or {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def ajax_post(self, url, spec):
        return self.client.post(url, json.dumps(spec), content_type='application/json',
                                HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def create_form(self, spec):
        """ Creates a form through the builder as whoever is logged in. """
        response = self.ajax_post('/customforms/submit/', spec)
        self.assertEqual(response.status_code, 200, response.content)
        return Form.objects.get(title=spec['title'])

    def fields(self, form):
        return {f.label: f for f in Field.objects.filter(form=form)}

    def submit(self, form, answers, step=0):
        data = {'combo_form-current_step': str(step)}
        data.update(answers)
        return self.client.post(f'/customforms/view/{form.id}/', data)

    def responses(self, form):
        return DynamicModelHandler(form).createDynModel().objects.all()

    def columns(self, form):
        with connection.cursor() as cursor:
            cursor.execute('SELECT column_name FROM information_schema.columns '
                           'WHERE table_schema = %s AND table_name = %s',
                           ['customforms', f'customforms_response_{form.id}'])
            return {row[0] for row in cursor.fetchall()}

    def error_message(self, response):
        return json.loads(response.content)['message']


class BuilderEndpointAccessTest(CustomFormViewTestCase):
    """ The form builder's AJAX endpoints are only for teachers and admins. """

    def test_students_are_sent_to_login(self):
        self.login(self.student)
        for url in ['/customforms/builddata/', '/customforms/getlinks/',
                    '/customforms/getmodules/', '/customforms/metadata/',
                    '/customforms/getData/', '/customforms/bulkdownloadfiles/',
                    '/customforms/exceldata/1/']:
            with self.subTest(url=url):
                response = self.ajax_get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith('/accounts/login/'))

    def test_students_cannot_create_forms(self):
        self.login(self.student)
        response = self.ajax_post('/customforms/submit/', form_spec([page_spec([field_spec('textField')])]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Form.objects.exists())

    def test_non_ajax_requests_are_rejected(self):
        self.login(self.teacher)
        for url in ['/customforms/builddata/', '/customforms/getlinks/',
                    '/customforms/getmodules/', '/customforms/metadata/',
                    '/customforms/getData/', '/customforms/getperms/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 400)

    def test_builder_data_lists_linkable_models_and_fields(self):
        self.login(self.teacher)
        response = self.ajax_get('/customforms/builddata/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('Program', data['only_fkey_models'])
        self.assertIn('ContactInfo_e_mail', data['link_fields']['ContactInfo'])
        self.assertIn('TeacherInfo_college', data['link_fields']['TeacherInfo'])

    def test_get_links_lists_instances_of_a_linked_model(self):
        contact = ContactInfo.objects.create(user=self.teacher, e_mail='t@example.com')
        self.login(self.teacher)
        response = self.ajax_get('/customforms/getlinks/', {'link_model': 'ContactInfo'})
        self.assertEqual(response.status_code, 200)
        self.assertIn({'id': contact.id, 'name': str(contact)}, json.loads(response.content))

    def test_get_links_rejects_unknown_model(self):
        self.login(self.teacher)
        response = self.ajax_get('/customforms/getlinks/', {'link_model': 'NotAModel'})
        self.assertEqual(response.status_code, 400)

    def test_get_perms_rejects_non_numeric_program(self):
        self.login(self.teacher)
        response = self.ajax_get('/customforms/getperms/', {'prog_id': 'abc'})
        self.assertEqual(response.status_code, 400)

    def test_get_modules_rejects_missing_program(self):
        self.login(self.teacher)
        self.assertEqual(self.ajax_get('/customforms/getmodules/').status_code, 400)
        self.assertEqual(self.ajax_get('/customforms/getmodules/', {'program': 999999}).status_code, 400)


class ProgramLinkedFormTest(CustomFormViewTestCase):
    """ Forms linked to a program, its user lists, and its registration modules. """

    def setUp(self):
        super().setUp()
        self.program = make_program(admin=self.admin)
        self.login(self.admin)

    def program_spec(self, title, link_id=None, **extra):
        return form_spec([page_spec([field_spec('textField', 'Q')])], title=title,
                         link_type='Program',
                         link_id=self.program.id if link_id is None else link_id, **extra)

    def tag_value(self, key):
        tag = Tag.objects.filter(key=key, object_id=self.program.id).first()
        return tag.value if tag else None

    def ajax_rebuild(self, form):
        """ Fetches the builder metadata and turns its pages back into a builder spec. """
        response = self.ajax_get('/customforms/metadata/', {'form_id': form.id})
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        pages = []
        for seq, page in enumerate(data['pages']):
            fields = [field_spec(f['field_type'], f['label'], f['seq'], f['required'], parent_id=f['id'])
                      for section in page for f in section]
            pages.append(page_spec(fields, seq=seq, parent_id=page[0][0]['section__page__id'],
                                   section_id=page[0][0]['section__id']))
        data['pages_spec'] = pages
        return data

    def test_get_links_lists_programs(self):
        response = self.ajax_get('/customforms/getlinks/', {'link_model': 'Program'})
        self.assertEqual(response.status_code, 200)
        self.assertIn({'id': self.program.id, 'name': str(self.program)}, json.loads(response.content))

    def test_get_modules_lists_only_custom_form_modules(self):
        response = self.ajax_get('/customforms/getmodules/', {'program': self.program.id})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual([h for h, _ in data['learn']], ['StudentCustomFormModule'])
        self.assertEqual(sorted(h for h, _ in data['teach']), ['TeacherCustomFormModule', 'TeacherQuizModule'])

    def test_get_perms_lists_the_programs_user_lists(self):
        response = self.ajax_get('/customforms/getperms/', {'prog_id': self.program.id})
        self.assertEqual(response.status_code, 200)
        perms = json.loads(response.content)
        self.assertIn('class_submitted', [name for name, _ in perms['teachers']])
        self.assertTrue(perms['students'])

    def test_creating_a_form_links_it_to_a_registration_module(self):
        for module, key in MODULE_TAGS.items():
            with self.subTest(module=module):
                form = self.create_form(self.program_spec(f'{module} form', link_module=module))
                self.assertEqual(self.tag_value(key), str(form.id))

    def test_creating_a_form_rejects_a_module_that_does_not_use_forms(self):
        response = self.ajax_post('/customforms/submit/',
                                  self.program_spec('Bad module', link_module='AvailabilityModule'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('does not use a custom form', self.error_message(response))
        self.assertFalse(Form.objects.filter(title='Bad module').exists())

    def test_creating_a_form_rejects_a_module_the_program_lacks(self):
        self.program.program_modules.remove(*self.program.program_modules.filter(handler='TeacherQuizModule'))
        response = self.ajax_post('/customforms/submit/',
                                  self.program_spec('Missing module', link_module='TeacherQuizModule'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('does not have TeacherQuizModule enabled', self.error_message(response))
        self.assertFalse(Form.objects.filter(title='Missing module').exists())

    def test_creating_a_form_rejects_a_missing_program(self):
        response = self.ajax_post('/customforms/submit/',
                                  self.program_spec('No program', link_id=999999,
                                                    link_module='StudentCustomFormModule'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('No program with ID 999999', self.error_message(response))
        self.assertFalse(Form.objects.filter(title='No program').exists())

    def test_editing_a_form_moves_its_module_link(self):
        spec = self.program_spec('Moving form', link_module='StudentCustomFormModule')
        form = self.create_form(spec)
        spec.update(form_id=form.id, link_module='TeacherCustomFormModule',
                    pages=self.ajax_rebuild(form)['pages_spec'])
        response = self.ajax_post('/customforms/modify/', spec)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(self.tag_value('learn_extraform_id'))
        self.assertEqual(self.tag_value('teach_extraform_id'), str(form.id))

    def test_editing_a_form_rejects_a_module_that_does_not_use_forms(self):
        spec = self.program_spec('Edited form')
        form = self.create_form(spec)
        spec.update(form_id=form.id, link_module='AvailabilityModule', title='Renamed')
        response = self.ajax_post('/customforms/modify/', spec)
        self.assertEqual(response.status_code, 400)
        self.assertIn('does not use a custom form', self.error_message(response))
        self.assertEqual(Form.objects.get(id=form.id).title, 'Edited form')

    def test_rebuild_data_reports_the_linked_module(self):
        form = self.create_form(self.program_spec('Quiz', link_module='TeacherQuizModule'))
        data = self.ajax_rebuild(form)
        self.assertEqual(data['title'], 'Quiz')
        self.assertEqual(data['link_type'], 'Program')
        self.assertEqual(data['link_id'], self.program.id)
        self.assertEqual((data['link_tl'], data['link_module']), ('teach', 'TeacherQuizModule'))
        self.assertEqual(data['pages'][0][0][0]['label'], 'Q')

    def test_rebuild_data_without_a_module_link(self):
        form = self.create_form(self.program_spec('Plain'))
        data = self.ajax_rebuild(form)
        self.assertEqual((data['link_tl'], data['link_module']), ('', ''))

    def test_rebuild_data_rejects_a_form_linked_to_two_modules(self):
        form = self.create_form(self.program_spec('Twice', link_module='StudentCustomFormModule'))
        Tag.setTag('teach_extraform_id', target=self.program, value=form.id)
        response = self.ajax_get('/customforms/metadata/', {'form_id': form.id})
        self.assertEqual(response.status_code, 400)
        self.assertIn('linked to multiple registration modules', self.error_message(response))

    def test_rebuild_data_rejects_non_numeric_form_id(self):
        response = self.ajax_get('/customforms/metadata/', {'form_id': 'abc'})
        self.assertEqual(response.status_code, 400)

    def test_landing_page_describes_program_links(self):
        chosen = self.create_form(self.program_spec('Chosen'))
        choice = self.create_form(self.program_spec('Choice', link_id=-1))
        deleted = self.create_form(self.program_spec('Deleted', link_id=999999))
        response = self.client.get('/customforms/')
        self.assertEqual(response.status_code, 200)
        link_objs = {f.id: f.link_obj for f in response.context['form_list']}
        self.assertEqual(link_objs[chosen.id], self.program)
        self.assertEqual(link_objs[choice.id], "User's choice")
        self.assertEqual(link_objs[deleted.id], '(deleted)')

    def test_responses_to_a_program_form_record_the_program(self):
        form = self.create_form(self.program_spec('Program form'))
        question = self.fields(form)['Q']
        self.login(self.student)
        response = self.client.get(f'/customforms/view/{form.id}/')
        self.assertContains(response, 'name="link_Program"')
        response = self.submit(form, {'link_Program': self.program.id, f'question_{question.id}': 'Hi'})
        self.assertRedirects(response, f'/customforms/success/{form.id}/')
        self.assertEqual(self.responses(form).get(user=self.student).link_Program_id, self.program.id)

        self.login(self.admin)
        data = json.loads(self.ajax_get('/customforms/getData/', {'form_id': form.id}).content)
        self.assertIn(['link_Program_id', 'Program', 'fk'], data['questions'])
        self.assertEqual(data['answers'][0]['link_Program_id'], str(self.program))

    def test_users_pick_the_program_when_the_form_lets_them(self):
        form = self.create_form(self.program_spec('Pick a program', link_id=-1))
        self.login(self.student)
        response = self.client.get(f'/customforms/view/{form.id}/')
        self.assertContains(response, 'Please pick the Program you want to fill the form for')
        self.assertContains(response, f'<option value="{self.program.id}"')

    def test_editing_a_form_changes_what_it_is_linked_to(self):
        spec = form_spec([page_spec([field_spec('textField', 'Q')])], title='Relinked')
        form = self.create_form(spec)
        self.assertNotIn('link_Program_id', self.columns(form))

        spec.update(form_id=form.id, link_type='Program', link_id=self.program.id,
                    pages=self.ajax_rebuild(form)['pages_spec'])
        self.assertEqual(self.ajax_post('/customforms/modify/', spec).status_code, 200)
        form.refresh_from_db()
        self.assertEqual((form.link_type, form.link_id), ('Program', self.program.id))
        self.assertIn('link_Program_id', self.columns(form))

        spec.update(link_type='-1', link_id=-1)
        self.assertEqual(self.ajax_post('/customforms/modify/', spec).status_code, 200)
        form.refresh_from_db()
        self.assertEqual(form.link_type, '-1')
        self.assertNotIn('link_Program_id', self.columns(form))

    def test_form_restricted_to_a_program_user_list(self):
        form = self.create_form(form_spec([page_spec([field_spec('textField', 'Q')])],
                                          title='Teachers of this program',
                                          perms=f'Teacher,{self.program.id},class_submitted'))
        other_teacher = make_user('Teacher', username='cfv_other_teacher')
        make_class(self.program, self.teacher)

        self.login(self.teacher)
        response = self.client.get(f'/customforms/view/{form.id}/')
        self.assertContains(response, 'name="question_')

        self.login(other_teacher)
        response = self.client.get(f'/customforms/view/{form.id}/')
        self.assertContains(response, 'You are not permitted to view this form.')


class ViewFormAccessTest(CustomFormViewTestCase):
    """ Who can open a form to fill it in. """

    def test_missing_form_is_not_found(self):
        self.login(self.student)
        self.assertEqual(self.client.get('/customforms/view/999999/').status_code, 404)

    def test_logged_out_user_is_asked_to_log_in(self):
        self.login(self.admin)
        form = self.create_form(form_spec([page_spec([field_spec('textField')])]))
        self.client.logout()
        response = self.client.get(f'/customforms/view/{form.id}/')
        self.assertContains(response, 'You need to be logged in to view this form.')
        self.assertNotContains(response, 'name="question_')

    def test_user_without_the_required_role_is_refused(self):
        self.login(self.admin)
        form = self.create_form(form_spec([page_spec([field_spec('textField')])], perms='Teacher'))
        self.login(self.student)
        response = self.client.get(f'/customforms/view/{form.id}/')
        self.assertContains(response, 'You are not permitted to view this form.')

    def test_anonymous_form_accepts_logged_out_responses(self):
        self.login(self.admin)
        form = self.create_form(form_spec([page_spec([field_spec('textField', 'Q')])], anonymous=True))
        question = f'question_{self.fields(form)["Q"].id}'
        self.client.logout()
        for answer in ['first', 'second']:
            response = self.submit(form, {question: answer})
            self.assertRedirects(response, f'/customforms/success/{form.id}/')
        #   Anonymous responses are never replaced, since they aren't tied to a user
        self.assertEqual(sorted(r[question] for r in self.responses(form).values()), ['first', 'second'])


class MultiPageFormTest(CustomFormViewTestCase):
    """ Moving between the pages of a multi-page form. """

    def setUp(self):
        super().setUp()
        self.login(self.admin)
        self.form = self.create_form(form_spec([
            page_spec([field_spec('textField', 'Page one', required=True)], seq=0),
            page_spec([field_spec('numeric', 'Page two', required=True)], seq=1),
        ]))
        fields = self.fields(self.form)
        self.q1 = f'question_{fields["Page one"].id}'
        self.q2 = f'question_{fields["Page two"].id}'
        self.login(self.student)

    def test_form_opens_on_the_first_page(self):
        response = self.client.get(f'/customforms/view/{self.form.id}/')
        self.assertContains(response, 'Step 1 of 2')
        self.assertContains(response, f'name="{self.q1}"')
        self.assertNotContains(response, f'name="{self.q2}"')

    def test_valid_first_page_moves_on_without_saving(self):
        response = self.submit(self.form, {self.q1: 'hello'})
        self.assertContains(response, 'Step 2 of 2')
        self.assertContains(response, f'name="{self.q2}"')
        self.assertFalse(self.responses(self.form).exists())

    def test_invalid_first_page_is_shown_again(self):
        response = self.submit(self.form, {self.q1: ''})
        self.assertContains(response, 'Step 1 of 2')
        self.assertIn(self.q1, response.context['form'].errors)

    def test_invalid_last_page_is_shown_again(self):
        self.submit(self.form, {self.q1: 'hello'})
        response = self.submit(self.form, {self.q2: 'not a number'}, step=1)
        self.assertContains(response, 'Step 2 of 2')
        self.assertIn(self.q2, response.context['form'].errors)
        self.assertFalse(self.responses(self.form).exists())

    def test_going_back_keeps_earlier_answers(self):
        self.submit(self.form, {self.q1: 'hello'})
        response = self.submit(self.form, {'wizard_goto_step': '0'}, step=1)
        self.assertContains(response, 'Step 1 of 2')
        self.assertContains(response, 'value="hello"')

    def test_finishing_saves_answers_from_every_page(self):
        self.submit(self.form, {self.q1: 'hello'})
        response = self.submit(self.form, {self.q2: '7'}, step=1)
        self.assertRedirects(response, f'/customforms/success/{self.form.id}/')
        answer = self.responses(self.form).get(user=self.student)
        self.assertEqual((getattr(answer, self.q1), getattr(answer, self.q2)), ('hello', 7))

    def test_resubmitting_replaces_the_users_earlier_response(self):
        for text in ['first', 'second']:
            self.submit(self.form, {self.q1: text})
            self.submit(self.form, {self.q2: '7'}, step=1)
        self.assertEqual([getattr(r, self.q1) for r in self.responses(self.form)], ['second'])


class CorrectAnswerValidationTest(CustomFormViewTestCase):
    """ Questions with a correct answer set by the form author reject other answers. """

    def setUp(self):
        super().setUp()
        self.login(self.admin)
        specs = [
            ('checkboxes', {'options': 'A|B|C', 'correct_answer': '0|2'}),
            ('multiselect', {'options': 'A|B|C', 'correct_answer': '1'}),
            ('numeric', {'correct_answer': '42', 'limits': ','}),
            ('date', {'correct_answer': '2024-01-15'}),
            ('time', {'correct_answer': '13:30'}),
        ]
        self.form = self.create_form(form_spec([page_spec([
            field_spec(ftype, ftype, seq, attrs=attrs) for seq, (ftype, attrs) in enumerate(specs)])]))
        self.q = {label: f'question_{f.id}' for label, f in self.fields(self.form).items()}
        self.login(self.student)

    def answers(self, **values):
        return {self.q[ftype]: value for ftype, value in values.items()}

    def test_wrong_answers_are_rejected(self):
        response = self.submit(self.form, self.answers(
            checkboxes=['A'], multiselect=['A'], numeric='41', date='2024-01-16',
            time='13:31'))
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors
        for name in self.q.values():
            self.assertEqual(errors[name], ['Incorrect answer.'])
        self.assertFalse(self.responses(self.form).exists())

    def test_correct_answers_are_accepted(self):
        response = self.submit(self.form, self.answers(
            checkboxes=['A', 'C'], multiselect=['B'], numeric='42', date='2024-01-15',
            time='13:30'))
        self.assertRedirects(response, f'/customforms/success/{self.form.id}/')
        answer = self.responses(self.form).get(user=self.student)
        self.assertEqual(getattr(answer, self.q['checkboxes']), 'A;C')
        self.assertEqual(getattr(answer, self.q['numeric']), 42)


class NumericLimitsTest(CustomFormViewTestCase):
    """ Number questions enforce the author's minimum and maximum. """

    def setUp(self):
        super().setUp()
        self.login(self.admin)
        self.form = self.create_form(form_spec([page_spec([
            field_spec('numeric', 'Score', attrs={'limits': '1,10'})])]))
        self.q = f'question_{self.fields(self.form)["Score"].id}'
        self.login(self.student)

    def test_limits_are_rendered_for_the_browser(self):
        response = self.client.get(f'/customforms/view/{self.form.id}/')
        self.assertContains(response, 'min="1"')
        self.assertContains(response, 'max="10"')

    def test_values_outside_the_limits_are_rejected(self):
        for value in ['0', '11']:
            with self.subTest(value=value):
                response = self.submit(self.form, {self.q: value})
                self.assertIn(self.q, response.context['form'].errors)
        self.assertFalse(self.responses(self.form).exists())

    def test_values_inside_the_limits_are_accepted(self):
        response = self.submit(self.form, {self.q: '10'})
        self.assertRedirects(response, f'/customforms/success/{self.form.id}/')


class FileQuestionTest(CustomFormViewTestCase):
    """ File-upload questions, and downloading the uploaded files. """

    def setUp(self):
        super().setUp()
        self.login(self.teacher)
        self.form = self.create_form(form_spec([page_spec([
            field_spec('file', 'Upload', required=True)])]))
        self.q = f'question_{self.fields(self.form)["Upload"].id}'

    def test_file_question_renders_an_upload_input(self):
        self.login(self.student)
        response = self.client.get(f'/customforms/view/{self.form.id}/')
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, f'type="file" name="{self.q}"')

    def test_required_file_question_rejects_a_missing_upload(self):
        self.login(self.student)
        response = self.submit(self.form, {})
        self.assertEqual(response.context['form'].errors[self.q], ['This field is required.'])
        self.assertFalse(self.responses(self.form).exists())

    def test_bulk_download_zips_every_uploaded_file(self):
        upload_dir = tempfile.TemporaryDirectory()
        self.addCleanup(upload_dir.cleanup)
        paths = []
        for name in ['essay.txt', 'photo.txt']:
            path = os.path.join(upload_dir.name, name)
            with open(path, 'w') as f:
                f.write(f'contents of {name}')
            paths.append(path)
        model = DynamicModelHandler(self.form).createDynModel()
        model.objects.create(user=self.student, **{self.q: paths[0]})
        model.objects.create(user=self.admin, **{self.q: paths[1]})
        model.objects.create(user=self.teacher, **{self.q: ''})

        response = self.client.get('/customforms/bulkdownloadfiles/',
                                   {'form_id': self.form.id, 'question_name': self.q})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            self.assertEqual(sorted(archive.namelist()), ['essay.txt', 'photo.txt'])
            self.assertEqual(archive.read('essay.txt'), b'contents of essay.txt')

    def test_bulk_download_rejects_bad_requests(self):
        url = '/customforms/bulkdownloadfiles/'
        self.assertEqual(self.client.get(url, {'form_id': self.form.id}).status_code, 400)
        self.assertEqual(self.client.get(url, {'form_id': 'abc', 'question_name': self.q}).status_code, 400)
        self.assertEqual(self.client.post(url, {'form_id': self.form.id, 'question_name': self.q}).status_code, 400)


class ResponseExportTest(CustomFormViewTestCase):
    """ Downloading responses as a spreadsheet and fetching them for the results page. """

    def setUp(self):
        super().setUp()
        self.student.first_name, self.student.last_name = 'Stu', 'Dent'
        self.student.save()
        self.login(self.teacher)
        self.form = self.create_form(form_spec([page_spec([
            field_spec('textField', 'Text', 0),
            field_spec('instructions', 'Just read this', 1),
            field_spec('checkboxes', 'Pick', 2, attrs={'options': 'A|B|C'}),
            field_spec('numeric', 'Number', 3),
            field_spec('ContactInfo_name', 'Name', 4),
        ])], title='Export Form'))
        self.q = {label: f'question_{f.id}' for label, f in self.fields(self.form).items()}
        self.login(self.student)
        response = self.submit(self.form, {
            self.q['Text']: 'hello', self.q['Pick']: ['A', 'C'], self.q['Number']: '7',
            self.q['Name'] + '_0': 'Ada', self.q['Name'] + '_1': 'Lovelace',
        })
        self.assertRedirects(response, f'/customforms/success/{self.form.id}/')
        self.login(self.teacher)

    def test_linked_name_answer_updates_the_users_contact_info(self):
        contact = ContactInfo.objects.get(user=self.student)
        self.assertEqual((contact.first_name, contact.last_name), ('Ada', 'Lovelace'))

    def test_spreadsheet_has_a_header_row_and_one_row_per_response(self):
        response = self.client.get(f'/customforms/exceldata/{self.form.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=Export Form.xlsx')
        sheet = openpyxl.load_workbook(BytesIO(response.content)).active
        rows = list(sheet.iter_rows(values_only=True))
        #   Instructions aren't questions, so they get no column
        self.assertEqual(rows[0], ('User ID', 'User', 'User email', 'Username',
                                   'Text', 'Pick', 'Number', 'Name'))
        self.assertEqual(rows[1], (str(self.student.id), 'Stu Dent', self.student.email,
                                   self.student.username, 'hello', 'A;C', 7, 'Ada Lovelace'))
        self.assertEqual(len(rows), 2)

    def test_results_data_includes_every_answer(self):
        response = self.ajax_get('/customforms/getData/', {'form_id': self.form.id})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertNotIn(self.q['Just read this'], [q[0] for q in data['questions']])
        [answer] = data['answers']
        self.assertEqual(answer['username'], self.student.username)
        self.assertEqual(answer[self.q['Pick']], 'A;C')
        self.assertEqual(answer[self.q['Name']], ['Ada', 'Lovelace'])

    def test_results_data_needs_a_form_id(self):
        self.assertEqual(self.ajax_get('/customforms/getData/').status_code, 404)
        self.assertEqual(self.ajax_get('/customforms/getData/', {'form_id': 'abc'}).status_code, 404)


class FormEditingTest(CustomFormViewTestCase):
    """ Editing an existing form's questions keeps its response table in step. """

    def setUp(self):
        super().setUp()
        self.login(self.teacher)
        self.spec = form_spec([page_spec([
            field_spec('textField', 'Keep', 0),
            field_spec('textField', 'Retype', 1),
            field_spec('textField', 'Remove', 2),
            field_spec('dropdown', 'Choose', 3, attrs={'options': 'A|B', 'correct_answer': '0'}),
            field_spec('ContactInfo_e_mail', 'Email', 4),
            field_spec('ContactInfo_phone_day', 'Phone', 5),
        ])], title='Editable')
        self.form = self.create_form(self.spec)
        self.old = self.fields(self.form)
        self.page = self.old['Keep'].section.page
        self.section = self.old['Keep'].section

    def modify(self, fields, **extra):
        spec = dict(self.spec, form_id=self.form.id, **extra)
        spec['pages'] = [page_spec(fields, parent_id=self.page.id, section_id=self.section.id)]
        return self.ajax_post('/customforms/modify/', spec)

    def existing(self, label, seq, ftype=None, **kwargs):
        field = self.old[label]
        return field_spec(ftype or field.field_type, label, seq, parent_id=field.id, **kwargs)

    def test_questions_can_be_added_changed_and_removed(self):
        #   A response from before the edit
        DynamicModelHandler(self.form).createDynModel().objects.create(
            user=self.student, **{f'question_{self.old["Keep"].id}': 'kept'})
        #   Flush deferred FK checks, as committing the response would
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')

        response = self.modify([
            self.existing('Keep', 0),
            self.existing('Retype', 1, ftype='longAns'),
            self.existing('Choose', 2, attrs={'options': 'X|Y|Z'}),
            self.existing('Email', 3),
            self.existing('Phone', 4),
            field_spec('numeric', 'New', 5),
        ])
        self.assertEqual(response.status_code, 200, response.content)

        fields = self.fields(self.form)
        self.assertNotIn('Remove', fields)
        self.assertEqual(fields['Retype'].field_type, 'longAns')
        self.assertEqual(dict(Attribute.objects.filter(field=fields['Choose']).values_list('attr_type', 'value')),
                         {'options': 'X|Y|Z'})

        columns = self.columns(self.form)
        self.assertNotIn(f'question_{self.old["Remove"].id}', columns)
        self.assertIn(f'question_{fields["New"].id}', columns)
        self.assertIn('link_ContactInfo_id', columns)

        #   The old response survives, and the edited form takes new ones
        self.assertEqual(getattr(self.responses(self.form).get(user=self.student),
                                 f'question_{self.old["Keep"].id}'), 'kept')
        self.assertIsNone(getattr(self.responses(self.form).get(user=self.student),
                                  f'question_{fields["New"].id}'))
        self.login(self.admin)
        response = self.submit(self.form, {
            f'question_{fields["Keep"].id}': 'a', f'question_{fields["Retype"].id}': 'long ' * 20,
            f'question_{fields["Choose"].id}': 'Z', f'question_{fields["New"].id}': '5',
        })
        self.assertRedirects(response, f'/customforms/success/{self.form.id}/')
        self.assertEqual(getattr(self.responses(self.form).get(user=self.admin),
                                 f'question_{fields["New"].id}'), 5)

    def test_linked_column_is_dropped_with_the_last_linked_question(self):
        response = self.modify([self.existing('Keep', 0), self.existing('Email', 1)])
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotIn('Phone', self.fields(self.form))
        self.assertIn('link_ContactInfo_id', self.columns(self.form))

        response = self.modify([self.existing('Keep', 0)])
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(list(self.fields(self.form)), ['Keep'])
        self.assertNotIn('link_ContactInfo_id', self.columns(self.form))

    def test_editing_a_missing_form_fails(self):
        for form_id in [999999, 'abc']:
            with self.subTest(form_id=form_id):
                response = self.ajax_post('/customforms/modify/', dict(self.spec, form_id=form_id))
                self.assertEqual(response.status_code, 400)
                self.assertIn(f'Form {form_id} not found', self.error_message(response))


class MalformedBuilderRequestTest(CustomFormViewTestCase):
    """ Bad requests from the form builder fail cleanly without creating anything. """

    def setUp(self):
        super().setUp()
        self.login(self.teacher)

    def test_invalid_json_is_rejected(self):
        response = self.client.post('/customforms/submit/', 'not json', content_type='application/json',
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        self.assertIn('message', json.loads(response.content))
        self.assertFalse(Form.objects.exists())

    def test_missing_metadata_is_rejected(self):
        spec = form_spec([page_spec([field_spec('textField')])])
        del spec['pages']
        response = self.ajax_post('/customforms/submit/', spec)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Form.objects.exists())
