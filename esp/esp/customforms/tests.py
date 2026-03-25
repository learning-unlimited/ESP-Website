__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2014 by the individual contributors
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

import json
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from esp.customforms.models import Form, Field
from esp.customforms.DynamicModel import DynamicModelHandler
from esp.customforms.DynamicForm import matches_answer, BaseCustomForm
from esp.customforms.views import hasPerm
from esp.users.models import ESPUser, AnonymousESPUser
from esp.tests.util import CacheFlushTestCase as TestCase

class CustomFormsTest(TestCase):
    """ Tests for the backend views/models provided by the custom forms app. """

    def setUp(self):
        """ Create a test non-admin account and a test admin account. """

        new_admin, created = ESPUser.objects.get_or_create(username='forms_admin')
        new_admin.set_password('password')
        new_admin.save()
        new_admin.makeRole('Administrator')
        self.admin = new_admin

        new_student, created = ESPUser.objects.get_or_create(username='forms_student')
        new_student.set_password('password')
        new_student.save()
        new_student.makeRole('Student')
        self.student = new_student

    def tearDown(self):
        for form in Form.objects.all():
            dmh = DynamicModelHandler(form)
            dmh.purgeDynModel()

    def testAuthentication(self):
        """ Make sure custom forms pages are not viewable to unprivileged users,
            but are viewable to admins. """

        urls = ['/customforms/', '/customforms/create/']

        self.client.logout()
        for url in urls:
            response = self.client.get(url)
            self.assertRedirects(response, f'/accounts/login/?next={url}')

        self.client.login(username=self.student.username, password='password')
        for url in urls:
            response = self.client.get(url)
            self.assertRedirects(response, f'/accounts/login/?next={url}')

        self.client.login(username=self.admin.username, password='password')
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

        self.client.logout()

    def map_form_value(self, val):
        """ Converts POSTed form values to Python values.
            Within the scope of this test case, only needs to handle
            checkbox conversion to Boolean. """

        if val == 'on':
            return True
        else:
            return val

    def testForms(self):
        """ Test the basic processes of the custom forms app.
            All in a single test function to preserve state.    """

        self.client.login(username=self.admin.username, password='password')

        #   - Make sure you can get /customforms/create/
        response = self.client.get("/customforms/create/")
        self.assertEqual(response.status_code, 200)

        #   - Submit an example form
        #     (Note that this bypasses a *lot* of front-end stuff, that will
        #      need separate tests.)
        form_data = {
            'title': 'Test Form',
            'perms': '',
            'link_id': -1,
            'success_url': '/formsuccess.html',
            'success_message': 'Thank you!',
            'anonymous': False,
            'pages': [{
                'parent_id': -1,
                'sections': [{
                    'fields': [
                        {'data': {'field_type': 'textField', 'question_text': 'ShortText', 'seq': 0, 'required': True, 'parent_id': -1, 'attrs':{'correct_answer': 'Smart', 'charlimits': '0,100'}, 'help_text': 'Instructions'}},
                        {'data': {'field_type': 'phone', 'question_text': 'Your phone no.', 'seq': 1, 'required': True, 'parent_id': -1, 'attrs': {}, 'help_text': ''}},
                        {'data': {'field_type': 'gender', 'question_text': 'Your gender', 'seq': 2, 'required': True, 'parent_id': -1, 'attrs': {}, 'help_text': ''}},
                        {'data': {'field_type': 'radio', 'question_text': 'Choose an option', 'seq': 3, 'required': True, 'parent_id': -1, 'attrs': {'correct_answer': '1', 'options': 'A|B|C|'}, 'help_text': ''}},
                        {'data': {'field_type': 'boolean', 'question_text': 'True/false', 'seq': 4, 'required': True, 'parent_id': -1, 'attrs': {}, 'help_text':''}},
                        {'data': {'field_type': 'textField', 'question_text': 'NonRequired', 'seq': 5, 'required': False, 'parent_id': -1, 'attrs': {'correct_answer': '', 'charlimits': ','}, 'help_text': ''}}
                    ],
                'data': {'help_text': '', 'question_text': '', 'seq': 0}
                }],
                'seq': 0
            }],
            'link_type': '-1',
            'desc': 'Test'
        }

        response = self.client.post("/customforms/submit/", json.dumps(form_data), content_type='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.content, encoding='UTF-8'), "OK")

        #   - Make sure the form and its fields exist and match what was specified
        forms = Form.objects.filter(title='Test Form')
        self.assertTrue(forms.exists())
        form = forms[0]
        fields = form.field_set.all()
        field_id_map = {}
        for target_field in form_data['pages'][0]['sections'][0]['fields']:
            stored_field = fields.get(label=target_field['data']['question_text'])
            field_id_map[target_field['data']['question_text']] = stored_field.id
            self.assertEqual(target_field['data']['field_type'], stored_field.field_type)
            self.assertEqual(target_field['data']['help_text'], stored_field.help_text)
            self.assertEqual(target_field['data']['seq'], stored_field.seq)
            self.assertEqual((target_field['data']['required']), stored_field.required)

        #   - Make sure you can view the form as a student
        self.client.login(username=self.student.username, password='password')
        response = self.client.get(f"/customforms/view/{form.id}/")
        self.assertEqual(response.status_code, 200)

        #   - Build an initial set of responses
        responses_initial = {}
        responses_initial[f'question_{field_id_map["ShortText"]}'] = 'Dumb'
        responses_initial[f'question_{field_id_map["Your phone no."]}'] = '(201) 426-5797'
        responses_initial[f'question_{field_id_map["Your gender"]}'] = 'F'
        responses_initial[f'question_{field_id_map["Choose an option"]}'] = 'A'
        responses_initial[f'question_{field_id_map["True/false"]}'] = 'on'
        responses_initial[f'question_{field_id_map["NonRequired"]}'] = 'test'

        #   - Make sure validation catches incorrect response
        #     (for the question with a correct answer)
        post_dict = {'combo_form-current_step': '0'}
        post_dict.update(responses_initial)
        response = self.client.post(f"/customforms/view/{form.id}/", post_dict)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Incorrect answer')
        responses_corrected = responses_initial
        responses_corrected[f'question_{field_id_map["ShortText"]}'] = 'Smart'
        responses_initial[f'question_{field_id_map["Choose an option"]}'] = 'B'
        post_dict.update(responses_corrected)
        response = self.client.post(f"/customforms/view/{form.id}/", post_dict)
        self.assertRedirects(response, f"/customforms/success/{form.id}/")
        response = self.client.get(f"/customforms/success/{form.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, form_data['success_message'])

        #   - Make sure the form response is saved correctly
        dmh = DynamicModelHandler(form)
        model = dmh.createDynModel()
        form_responses = model.objects.filter(user=self.student)
        self.assertEqual(form_responses.count(), 1)
        form_response = form_responses[0]
        for key in responses_corrected:
            self.assertEqual(self.map_form_value(responses_corrected[key]), getattr(form_response, key))

        #   - Make sure the response can be viewed by an admin and is correct
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get("/customforms/getData/", {'form_id': form.id}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content.decode('UTF-8'))
        self.assertTrue('answers' in list(response_data.keys()))
        self.assertEqual(len(response_data['answers']), 1)
        indiv_response = response_data['answers'][0]
        self.assertEqual(int(indiv_response['user_id']), self.student.id)
        for field_spec in indiv_response:
            self.assertEqual(self.map_form_value(responses_corrected[key]), indiv_response[key])
        self.assertTrue('questions' in response_data)
        self.assertEqual(len(response_data['questions']), len(responses_initial) + 4)   #   provided fields plus user_id, user_display, user_email, username
        for entry in response_data['questions']:
            if entry[0] in ['user_id', 'user_display', 'user_email', 'username']:
                continue
            self.assertTrue(entry[0] in responses_corrected)


class LandingViewTest(TestCase):
    """Tests for the landing() view admin vs teacher form visibility."""

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='landing_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.teacher, _ = ESPUser.objects.get_or_create(username='landing_teacher')
        self.teacher.set_password('password')
        self.teacher.save()
        self.teacher.makeRole('Teacher')

        self.student, _ = ESPUser.objects.get_or_create(username='landing_student')
        self.student.set_password('password')
        self.student.save()
        self.student.makeRole('Student')

        self.admin_form = Form.objects.create(
            title='Admin Form', description='Test', created_by=self.admin,
            link_type='-1', link_id=-1, anonymous=False, perms='',
            success_message='OK', success_url='/'
        )
        self.teacher_form = Form.objects.create(
            title='Teacher Form', description='Test', created_by=self.teacher,
            link_type='-1', link_id=-1, anonymous=False, perms='',
            success_message='OK', success_url='/'
        )

    def tearDown(self):
        for form in Form.objects.all():
            dmh = DynamicModelHandler(form)
            dmh.purgeDynModel()

    def test_admin_sees_all_forms(self):
        """Admin should see all forms regardless of creator."""
        self.client.login(username='landing_admin', password='password')
        response = self.client.get('/customforms/')
        self.assertEqual(response.status_code, 200)
        form_ids = [f.id for f in response.context['form_list']]
        self.assertIn(self.admin_form.id, form_ids)
        self.assertIn(self.teacher_form.id, form_ids)

    def test_teacher_sees_only_own_forms(self):
        """Teacher should only see forms they created."""
        self.client.login(username='landing_teacher', password='password')
        response = self.client.get('/customforms/')
        self.assertEqual(response.status_code, 200)
        form_ids = [f.id for f in response.context['form_list']]
        self.assertIn(self.teacher_form.id, form_ids)
        self.assertNotIn(self.admin_form.id, form_ids)

    def test_student_cannot_access(self):
        """Student should be redirected (no teacher/admin/morphed role)."""
        self.client.login(username='landing_student', password='password')
        response = self.client.get('/customforms/')
        self.assertRedirects(response, '/accounts/login/?next=/customforms/')

    def test_unauthenticated_redirected(self):
        """Unauthenticated user should be redirected to login."""
        self.client.logout()
        response = self.client.get('/customforms/')
        self.assertRedirects(response, '/accounts/login/?next=/customforms/')


class HasPermTest(TestCase):
    """Tests for hasPerm() access control logic."""

    def setUp(self):
        self.user, _ = ESPUser.objects.get_or_create(username='perm_user')
        self.user.set_password('password')
        self.user.save()
        self.anon_user = AnonymousESPUser()

    def tearDown(self):
        for form in Form.objects.all():
            dmh = DynamicModelHandler(form)
            dmh.purgeDynModel()

    def test_anon_user_non_anon_form_denied(self):
        """Anonymous user should be denied access to non-anonymous form."""
        form = Form.objects.create(
            title='Test Form', created_by=self.user,
            anonymous=False, perms='',
            success_message='OK', success_url='/'
        )
        allowed, msg = hasPerm(self.anon_user, form)
        self.assertFalse(allowed)
        self.assertEqual(msg, "You need to be logged in to view this form.")

    def test_anon_user_anon_form_no_perms_allowed(self):
        """Anonymous user should be allowed if form is anonymous and has no perms."""
        form = Form.objects.create(
            title='Test Form', created_by=self.user,
            anonymous=True, perms='',
            success_message='OK', success_url='/'
        )
        allowed, msg = hasPerm(self.anon_user, form)
        self.assertTrue(allowed)
        self.assertEqual(msg, "")

    def test_authenticated_no_perms_allowed(self):
        """Authenticated user should be allowed if form has no perms."""
        form = Form.objects.create(
            title='Test Form', created_by=self.user,
            anonymous=False, perms='',
            success_message='OK', success_url='/'
        )
        allowed, msg = hasPerm(self.user, form)
        self.assertTrue(allowed)
        self.assertEqual(msg, "")

    def test_anon_user_anon_form_with_perms_denied(self):
        """Anonymous user should be denied if form has perms, even if anonymous=True."""
        form = Form.objects.create(
            title='Test Form', created_by=self.user,
            anonymous=True, perms='Teacher',
            success_message='OK', success_url='/'
        )
        allowed, msg = hasPerm(self.anon_user, form)
        self.assertFalse(allowed)
        self.assertEqual(msg, "You need to be logged in to view this form.")

    def test_user_with_matching_perm_allowed(self):
        """User with matching role should be allowed."""
        self.user.makeRole('Teacher')
        form = Form.objects.create(
            title='Test Form', created_by=self.user,
            anonymous=False, perms='Teacher',
            success_message='OK', success_url='/'
        )
        allowed, msg = hasPerm(self.user, form)
        self.assertTrue(allowed)
        self.assertEqual(msg, "")

    def test_user_without_matching_perm_denied(self):
        """User without matching role should be denied."""
        self.user.makeRole('Student')
        form = Form.objects.create(
            title='Test Form', created_by=self.user,
            anonymous=False, perms='Teacher',
            success_message='OK', success_url='/'
        )
        allowed, msg = hasPerm(self.user, form)
        self.assertFalse(allowed)
        self.assertEqual(msg, "You are not permitted to view this form.")


class ViewResponseTest(TestCase):
    """Tests for viewResponse() — permission check."""

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='resp_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.teacher, _ = ESPUser.objects.get_or_create(username='resp_teacher')
        self.teacher.set_password('password')
        self.teacher.save()
        self.teacher.makeRole('Teacher')

        self.student, _ = ESPUser.objects.get_or_create(username='resp_student')
        self.student.set_password('password')
        self.student.save()
        self.student.makeRole('Student')

        self.form = Form.objects.create(
            title='Test Form', created_by=self.admin,
            link_type='-1', link_id=-1,
            success_message='OK', success_url='/'
        )
        # Create dynamic model table so view doesn't crash on query
        dmh = DynamicModelHandler(self.form)
        dmh.createTable()

    def tearDown(self):
        for form in Form.objects.all():
            dmh = DynamicModelHandler(form)
            dmh.purgeDynModel()

    def test_admin_can_view_responses(self):
        """Admin should be able to view responses page."""
        self.client.login(username='resp_admin', password='password')
        response = self.client.get('/customforms/responses/%d/' % self.form.id)
        self.assertEqual(response.status_code, 200)

    def test_teacher_can_view_responses(self):
        """Teacher should be able to view responses page."""
        self.client.login(username='resp_teacher', password='password')
        response = self.client.get('/customforms/responses/%d/' % self.form.id)
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_access(self):
        """Student should not be able to view responses."""
        self.client.login(username='resp_student', password='password')
        response = self.client.get('/customforms/responses/%d/' % self.form.id)
        # Should redirect to home page, which is '/'
        self.assertRedirects(response, '/')

    def test_unauthenticated_redirected(self):
        """Unauthenticated user should be redirected to login (by decorator)."""
        self.client.logout()
        response = self.client.get('/customforms/responses/%d/' % self.form.id)
        self.assertRedirects(response, '/accounts/login/?next=/customforms/responses/%d/' % self.form.id)


class FormBuilderViewTest(TestCase):
    """Tests for formBuilder() - context data and access control."""
    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='builder_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.teacher, _ = ESPUser.objects.get_or_create(username='builder_teacher')
        self.teacher.set_password('password')
        self.teacher.save()
        self.teacher.makeRole('Teacher')
        self.student, _ = ESPUser.objects.get_or_create(username='builder_student')
        self.student.set_password('password')
        self.student.save()
        self.student.makeRole('Student')

        self.admin_form = Form.objects.create(
            title='Admin Form', description='Test', created_by=self.admin,
            link_type='-1', link_id=-1, anonymous=False, perms='',
            success_message='OK', success_url='/'
        )
        self.teacher_form = Form.objects.create(
            title='Teacher Form', description='Test', created_by=self.teacher,
            link_type='-1', link_id=-1, anonymous=False, perms='',
            success_message='OK', success_url='/'
        )

    def tearDown(self):
        for form in Form.objects.all():
            dmh = DynamicModelHandler(form)
            dmh.purgeDynModel()

    def test_admin_sees_all_forms_in_context(self):
        """Admin context should include all forms."""
        self.client.login(username='builder_admin', password='password')
        response = self.client.get('/customforms/create')
        self.assertEqual(response.status_code, 200)
        # 'form_list' in context is a QuerySet
        form_ids = [f.id for f in response.context['form_list']]
        self.assertIn(self.admin_form.id, form_ids)
        self.assertIn(self.teacher_form.id, form_ids)

    def test_teacher_sees_only_own_forms(self):
        """Teacher context should only include their own forms."""
        self.client.login(username='builder_teacher', password='password')
        response = self.client.get('/customforms/create')
        self.assertEqual(response.status_code, 200)
        form_ids = [f.id for f in response.context['form_list']]
        self.assertIn(self.teacher_form.id, form_ids)
        self.assertNotIn(self.admin_form.id, form_ids)
    def test_edit_param_in_context(self):
        """If ?edit=ID is passed, it should be in the context."""
        # Note: edit param is a string in context
        self.client.login(username='builder_teacher', password='password')
        response = self.client.get('/customforms/create?edit=%d' % self.teacher_form.id)
        self.assertEqual(response.context['edit'], str(self.teacher_form.id))
    def test_student_cannot_access(self):
        """Student should be redirected."""
        self.client.login(username='builder_student', password='password')
        response = self.client.get('/customforms/create')
        self.assertRedirects(response, '/accounts/login/?next=/customforms/create')


# ===========================================================================
# Helper: quickly create a single-page form via admin POST
# ===========================================================================

def _create_simple_form(client, admin, title='Helper Form', fields=None, anonymous=False, perms=''):
    """POST to /customforms/submit/ to create a form. Returns the Form object."""
    if fields is None:
        fields = [{
            'data': {
                'field_type': 'textField',
                'question_text': 'Name',
                'seq': 0,
                'required': True,
                'parent_id': -1,
                'attrs': {'charlimits': '0,100'},
                'help_text': ''
            }
        }]
    form_data = {
        'title': title,
        'perms': perms,
        'link_id': -1,
        'success_url': '/done/',
        'success_message': 'Thanks!',
        'anonymous': anonymous,
        'pages': [{
            'parent_id': -1,
            'sections': [{
                'fields': fields,
                'data': {'help_text': '', 'question_text': '', 'seq': 0},
            }],
            'seq': 0,
        }],
        'link_type': '-1',
        'desc': 'Auto-created for test'
    }
    client.login(username=admin.username, password='password')
    client.post(
        '/customforms/submit/',
        json.dumps(form_data),
        content_type='application/json',
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    return Form.objects.get(title=title)


# ===========================================================================
# 1. matches_answer validator
# ===========================================================================

class MatchesAnswerValidatorTest(TestCase):
    """Unit tests for the matches_answer() validator factory."""

    def test_correct_answer_passes(self):
        """Validator should not raise when the value matches the target."""
        validator = matches_answer('Cambridge')
        try:
            validator('Cambridge')
        except ValidationError:
            self.fail('matches_answer raised ValidationError on correct answer')

    def test_wrong_answer_raises(self):
        """Validator should raise ValidationError when the value is wrong."""
        validator = matches_answer('Cambridge')
        with self.assertRaises(ValidationError) as ctx:
            validator('Boston')
        self.assertIn('Incorrect answer', str(ctx.exception))

    def test_empty_string_wrong_answer_raises(self):
        """Empty string is not correct when target is non-empty."""
        validator = matches_answer('correct')
        with self.assertRaises(ValidationError):
            validator('')

    def test_case_sensitive(self):
        """Validator is case-sensitive."""
        validator = matches_answer('Correct')
        with self.assertRaises(ValidationError):
            validator('correct')


# ===========================================================================
# 2. BaseCustomForm.clean()
# ===========================================================================

class BaseCustomFormCleanTest(TestCase):
    """Tests for BaseCustomForm.clean() data transformation."""

    def _make_form_with_data(self, data):
        """Build a minimal BaseCustomForm-based form instance with pre-set cleaned_data."""
        from django import forms

        class _TempForm(BaseCustomForm):
            dummy = forms.CharField(required=False)

        f = _TempForm(data={'dummy': 'x'})
        f.is_valid()
        f.cleaned_data = data
        return f

    def test_list_values_joined_with_semicolon(self):
        """List values in cleaned_data should be joined into a semicolon-separated string."""
        form = self._make_form_with_data({'question_1': ['A', 'B', 'C']})
        result = form.clean()
        self.assertEqual(result['question_1'], 'A;B;C')

    def test_dict_values_expanded_into_parent(self):
        """
        Dict values in cleaned_data should be flattened into the parent dict,
        and the original key removed.
        """
        form = self._make_form_with_data({
            'question_2': {'first_name': 'Alice', 'last_name': 'Smith'}
        })
        result = form.clean()
        self.assertNotIn('question_2', result)
        self.assertEqual(result['first_name'], 'Alice')
        self.assertEqual(result['last_name'], 'Smith')

    def test_plain_string_value_unchanged(self):
        """Plain string values should pass through unchanged."""
        form = self._make_form_with_data({'question_3': 'hello'})
        result = form.clean()
        self.assertEqual(result['question_3'], 'hello')

    def test_mixed_data_handled_correctly(self):
        """Mixed list + dict + string fields all handled in one clean() call."""
        form = self._make_form_with_data({
            'q_list': ['X', 'Y'],
            'q_dict': {'city': 'Boston'},
            'q_str': 'plain',
        })
        result = form.clean()
        self.assertEqual(result['q_list'], 'X;Y')
        self.assertNotIn('q_dict', result)
        self.assertEqual(result['city'], 'Boston')
        self.assertEqual(result['q_str'], 'plain')


# ===========================================================================
# 3. onModify view
# ===========================================================================

class OnModifyViewTest(TestCase):
    """Tests for the onModify view (/customforms/modify/)."""

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='mod_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.student, _ = ESPUser.objects.get_or_create(username='mod_student')
        self.student.set_password('password')
        self.student.save()
        self.student.makeRole('Student')

        self.form = _create_simple_form(self.client, self.admin, title='Modify Target')

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def _modify_payload(self, form, **overrides):
        return {
            'form_id': form.id,
            'title': overrides.get('title', form.title),
            'desc': overrides.get('desc', form.description),
            'perms': overrides.get('perms', form.perms),
            'success_message': overrides.get('success_message', form.success_message),
            'success_url': overrides.get('success_url', form.success_url),
            'link_type': overrides.get('link_type', form.link_type),
            'link_id': overrides.get('link_id', form.link_id),
            'pages': overrides.get('pages', [{'parent_id': -1, 'seq': 0, 'sections': []}]),
        }

    def test_modify_form_title(self):
        """Admin can modify a form's title via AJAX POST."""
        self.client.login(username=self.admin.username, password='password')
        payload = self._modify_payload(self.form, title='Updated Title')
        response = self.client.post(
            '/customforms/modify/',
            json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.form.refresh_from_db()
        self.assertEqual(self.form.title, 'Updated Title')

    def test_modify_form_not_found_returns_400(self):
        """Returns 400 JSON error when form_id doesn't exist."""
        self.client.login(username=self.admin.username, password='password')
        payload = self._modify_payload(self.form)
        payload['form_id'] = 999999
        response = self.client.post(
            '/customforms/modify/',
            json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)

    def test_modify_requires_ajax(self):
        """Non-AJAX POST to /customforms/modify/ returns HTTP 400."""
        self.client.login(username=self.admin.username, password='password')
        payload = self._modify_payload(self.form)
        response = self.client.post(
            '/customforms/modify/',
            json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_modify_get_request_returns_400(self):
        """GET to /customforms/modify/ returns HTTP 400."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(
            '/customforms/modify/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)

    def test_modify_requires_auth(self):
        """Unauthenticated user is redirected."""
        self.client.logout()
        payload = self._modify_payload(self.form)
        response = self.client.post(
            '/customforms/modify/',
            json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertRedirects(response, '/accounts/login/?next=/customforms/modify/')

    def test_student_cannot_modify(self):
        """Student role is redirected from /customforms/modify/."""
        self.client.login(username=self.student.username, password='password')
        payload = self._modify_payload(self.form)
        response = self.client.post(
            '/customforms/modify/',
            json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertRedirects(response, '/accounts/login/?next=/customforms/modify/')

    def test_add_field_via_modify(self):
        """A new field added in a modify payload appears in the DB."""
        self.client.login(username=self.admin.username, password='password')
        payload = self._modify_payload(self.form, pages=[{
            'parent_id': -1,
            'seq': 0,
            'sections': [{
                'data': {'question_text': '', 'help_text': '', 'seq': 0},
                'parent_id': -1,
                'fields': [{
                    'data': {
                        'field_type': 'textField',
                        'question_text': 'New Field via Modify',
                        'seq': 0,
                        'required': False,
                        'parent_id': -1,
                        'attrs': {'charlimits': '0,50'},
                        'help_text': ''
                    }
                }]
            }]
        }])
        response = self.client.post(
            '/customforms/modify/',
            json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Field.objects.filter(form=self.form, label='New Field via Modify').exists()
        )

    def test_remove_field_via_modify(self):
        """Sending an empty fields list removes all existing fields."""
        self.client.login(username=self.admin.username, password='password')
        self.assertTrue(Field.objects.filter(form=self.form).exists())
        payload = self._modify_payload(self.form, pages=[{
            'parent_id': -1,
            'seq': 0,
            'sections': [{
                'data': {'question_text': '', 'help_text': '', 'seq': 0},
                'parent_id': -1,
                'fields': []
            }]
        }])
        response = self.client.post(
            '/customforms/modify/',
            json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Field.objects.filter(form=self.form).exists())


# ===========================================================================
# 4. formBuilderData view
# ===========================================================================

class FormBuilderDataViewTest(TestCase):
    """Tests for the formBuilderData view (/customforms/builddata/)."""

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='builddata_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def test_returns_json_for_ajax_get(self):
        """Authenticated admin receives JSON containing only_fkey_models and link_fields."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(
            '/customforms/builddata/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('only_fkey_models', data)
        self.assertIn('link_fields', data)

    def test_non_ajax_returns_400(self):
        """Non-AJAX GET returns HTTP 400."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get('/customforms/builddata/')
        self.assertEqual(response.status_code, 400)

    def test_requires_auth(self):
        """Unauthenticated user is redirected to login."""
        self.client.logout()
        response = self.client.get(
            '/customforms/builddata/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertRedirects(response, '/accounts/login/?next=/customforms/builddata/')


# ===========================================================================
# 5. getRebuildData view
# ===========================================================================

class GetRebuildDataViewTest(TestCase):
    """Tests for the getRebuildData view (/customforms/metadata/)."""

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='rebuild_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')
        self.form = _create_simple_form(self.client, self.admin, title='Rebuild Me')

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def test_returns_form_metadata(self):
        """Returns JSON with title, desc, pages, anonymous, and link_type."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(
            '/customforms/metadata/',
            {'form_id': self.form.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['title'], 'Rebuild Me')
        self.assertIn('pages', data)
        self.assertIn('anonymous', data)
        self.assertIn('link_type', data)

    def test_invalid_form_id_returns_400(self):
        """Non-integer form_id returns HTTP 400."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(
            '/customforms/metadata/',
            {'form_id': 'not_an_int'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)

    def test_non_ajax_returns_400(self):
        """Non-AJAX GET returns HTTP 400."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(
            '/customforms/metadata/',
            {'form_id': self.form.id}
        )
        self.assertEqual(response.status_code, 400)


# ===========================================================================
# 6. getData view edge cases
# ===========================================================================

class GetDataEdgeCasesTest(TestCase):
    """Edge-case tests for the getData view (/customforms/getData/)."""

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='getdata_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')
        self.form = _create_simple_form(self.client, self.admin, title='GetData Form')

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def test_no_responses_returns_empty_answers(self):
        """Form with no submissions returns an empty answers list."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(
            '/customforms/getData/',
            {'form_id': self.form.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('answers', data)
        self.assertEqual(data['answers'], [])

    def test_questions_key_present(self):
        """Response JSON has a 'questions' key."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(
            '/customforms/getData/',
            {'form_id': self.form.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('questions', data)

    def test_non_ajax_returns_400(self):
        """Non-AJAX GET returns HTTP 400."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get('/customforms/getData/', {'form_id': self.form.id})
        self.assertEqual(response.status_code, 400)

    def test_invalid_form_id_returns_400(self):
        """Non-integer form_id returns HTTP 400."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(
            '/customforms/getData/',
            {'form_id': 'not_int'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)


# ===========================================================================
# 7. getExcelData view
# ===========================================================================

class GetExcelDataViewTest(TestCase):
    """Tests for the getExcelData view (/customforms/exceldata/<id>/)."""

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='excel_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.student, _ = ESPUser.objects.get_or_create(username='excel_student')
        self.student.set_password('password')
        self.student.save()
        self.student.makeRole('Student')

        self.form = _create_simple_form(self.client, self.admin, title='Excel Form')

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def test_returns_xlsx_for_admin(self):
        """Admin receives a valid XLSX file response."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(f'/customforms/exceldata/{self.form.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertIn('Content-Disposition', response)
        self.assertIn('Excel Form', response['Content-Disposition'])

    def test_student_cannot_access_excel(self):
        """Student is redirected away from excel export."""
        self.client.login(username=self.student.username, password='password')
        response = self.client.get(f'/customforms/exceldata/{self.form.id}/')
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/customforms/exceldata/{self.form.id}/'
        )

    def test_unauthenticated_redirected(self):
        """Unauthenticated user is redirected to login."""
        self.client.logout()
        response = self.client.get(f'/customforms/exceldata/{self.form.id}/')
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/customforms/exceldata/{self.form.id}/'
        )


# ===========================================================================
# 8. Multi-page form navigation
# ===========================================================================

class MultiPageFormTest(TestCase):
    """Tests for multi-page form navigation via SessionWizardView."""

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='mp_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.student, _ = ESPUser.objects.get_or_create(username='mp_student')
        self.student.set_password('password')
        self.student.save()
        self.student.makeRole('Student')

        form_data = {
            'title': 'Multi Page Form',
            'perms': '',
            'link_id': -1,
            'success_url': '/done/',
            'success_message': 'All done!',
            'anonymous': False,
            'pages': [
                {
                    'parent_id': -1,
                    'seq': 0,
                    'sections': [{
                        'data': {'help_text': '', 'question_text': '', 'seq': 0},
                        'fields': [{
                            'data': {
                                'field_type': 'textField',
                                'question_text': 'Step1 Field',
                                'seq': 0,
                                'required': True,
                                'parent_id': -1,
                                'attrs': {'charlimits': '0,100'},
                                'help_text': ''
                            }
                        }]
                    }]
                },
                {
                    'parent_id': -1,
                    'seq': 1,
                    'sections': [{
                        'data': {'help_text': '', 'question_text': '', 'seq': 0},
                        'fields': [{
                            'data': {
                                'field_type': 'textField',
                                'question_text': 'Step2 Field',
                                'seq': 0,
                                'required': True,
                                'parent_id': -1,
                                'attrs': {'charlimits': '0,100'},
                                'help_text': ''
                            }
                        }]
                    }]
                }
            ],
            'link_type': '-1',
            'desc': 'Multi-page test'
        }
        self.client.login(username=self.admin.username, password='password')
        r = self.client.post(
            '/customforms/submit/',
            json.dumps(form_data),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(r.status_code, 200)
        self.form = Form.objects.get(title='Multi Page Form')
        self.fields = {f.label: f for f in self.form.field_set.all()}

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def test_get_renders_step0(self):
        """GET to the form view renders step 0 field."""
        self.client.login(username=self.student.username, password='password')
        response = self.client.get(f'/customforms/view/{self.form.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Step1 Field')

    def test_valid_step0_advances_to_step1(self):
        """Posting valid step 0 data shows step 1 fields."""
        self.client.login(username=self.student.username, password='password')
        step1_field_id = self.fields['Step1 Field'].id
        response = self.client.post(f'/customforms/view/{self.form.id}/', {
            'combo_form-current_step': '0',
            f'question_{step1_field_id}': 'Hello',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Step2 Field')

    def test_invalid_step0_stays_on_step0(self):
        """Posting invalid step 0 data (empty required field) stays on step 0 with error."""
        self.client.login(username=self.student.username, password='password')
        step1_field_id = self.fields['Step1 Field'].id
        response = self.client.post(f'/customforms/view/{self.form.id}/', {
            'combo_form-current_step': '0',
            f'question_{step1_field_id}': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Step1 Field')
        self.assertNotContains(response, 'Step2 Field')

    def test_completing_all_steps_redirects_to_success(self):
        """Completing all wizard steps redirects to /customforms/success/<id>/."""
        self.client.login(username=self.student.username, password='password')
        step1_id = self.fields['Step1 Field'].id
        step2_id = self.fields['Step2 Field'].id

        self.client.post(f'/customforms/view/{self.form.id}/', {
            'combo_form-current_step': '0',
            f'question_{step1_id}': 'Answer 1',
        })
        response = self.client.post(f'/customforms/view/{self.form.id}/', {
            'combo_form-current_step': '1',
            f'question_{step2_id}': 'Answer 2',
        })
        self.assertRedirects(response, f'/customforms/success/{self.form.id}/')

    def test_response_stored_after_all_steps(self):
        """After completing all steps, the response is stored in the DB."""
        self.client.login(username=self.student.username, password='password')
        step1_id = self.fields['Step1 Field'].id
        step2_id = self.fields['Step2 Field'].id

        self.client.post(f'/customforms/view/{self.form.id}/', {
            'combo_form-current_step': '0',
            f'question_{step1_id}': 'My Answer 1',
        })
        self.client.post(f'/customforms/view/{self.form.id}/', {
            'combo_form-current_step': '1',
            f'question_{step2_id}': 'My Answer 2',
        })

        dmh = DynamicModelHandler(self.form)
        model = dmh.createDynModel()
        self.assertEqual(model.objects.filter(user=self.student).count(), 1)
        record = model.objects.get(user=self.student)
        self.assertEqual(getattr(record, f'question_{step1_id}'), 'My Answer 1')
        self.assertEqual(getattr(record, f'question_{step2_id}'), 'My Answer 2')


# ===========================================================================
# 9. viewForm permission edge cases
# ===========================================================================

class ViewFormPermissionTest(TestCase):
    """Tests for viewForm() permission handling."""

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='vfp_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.non_anon_form = _create_simple_form(
            self.client, self.admin, title='Non Anon Form'
        )
        # Create an anonymous form with table so view doesn't crash
        self.anon_form = Form.objects.create(
            title='Anon Form', description='', created_by=self.admin,
            link_type='-1', link_id=-1, anonymous=True, perms='',
            success_message='Done', success_url='/'
        )
        DynamicModelHandler(self.anon_form).createTable()

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def test_anon_user_denied_non_anon_form(self):
        """Anonymous (unauthenticated) user sees error page for non-anonymous form."""
        self.client.logout()
        response = self.client.get(f'/customforms/view/{self.non_anon_form.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'need to be logged in')

    def test_anon_user_allowed_anon_form(self):
        """Anonymous (unauthenticated) user can access anonymous forms with no perms."""
        self.client.logout()
        response = self.client.get(f'/customforms/view/{self.anon_form.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'need to be logged in')

    def test_nonexistent_form_returns_404(self):
        """Accessing a non-existent form ID returns HTTP 404."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get('/customforms/view/999999/')
        self.assertEqual(response.status_code, 404)


# ===========================================================================
# 10. success view
# ===========================================================================

class SuccessViewTest(TestCase):
    """Tests for the success() view."""

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='succ_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')
        self.form = _create_simple_form(self.client, self.admin, title='Success Form')
        self.form.success_message = 'Thank you very much!'
        self.form.save()

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def test_success_displays_message(self):
        """Success page renders the form's configured success message."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(f'/customforms/success/{self.form.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Thank you very much!')

    def test_success_page_accessible_to_student(self):
        """Students can access the success page (no permission guard)."""
        student, _ = ESPUser.objects.get_or_create(username='succ_student')
        student.set_password('password')
        student.save()
        student.makeRole('Student')
        self.client.login(username='succ_student', password='password')
        response = self.client.get(f'/customforms/success/{self.form.id}/')
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# 11. onSubmit edge cases
# ===========================================================================

class OnSubmitEdgeCasesTest(TestCase):
    """Edge-case tests for the onSubmit view (/customforms/submit/)."""

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='submit_edge_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def test_non_ajax_post_returns_error(self):
        """Non-AJAX POST to /customforms/submit/ does not return 200 OK."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.post(
            '/customforms/submit/',
            json.dumps({'title': 'X'}),
            content_type='application/json'
        )
        self.assertNotEqual(response.status_code, 200)

    def test_ajax_get_request_returns_error(self):
        """AJAX GET to /customforms/submit/ returns an error (not 200)."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(
            '/customforms/submit/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertNotEqual(response.status_code, 200)

    def test_malformed_json_returns_400(self):
        """Sending malformed JSON body returns HTTP 400."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.post(
            '/customforms/submit/',
            'THIS IS NOT JSON!!!',
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_redirected(self):
        """Unauthenticated user is redirected to login."""
        self.client.logout()
        response = self.client.post(
            '/customforms/submit/',
            json.dumps({'title': 'X'}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertRedirects(response, '/accounts/login/?next=/customforms/submit/')


# ===========================================================================
# 12. Anonymous form submission by an unauthenticated user
# ===========================================================================

class ViewFormAnonymousSubmissionTest(TestCase):
    """Tests for anonymous form submission by an unauthenticated user."""

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='anon_sub_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        form_data = {
            'title': 'Anon Submit Form',
            'perms': '',
            'link_id': -1,
            'success_url': '/done/',
            'success_message': 'Submitted!',
            'anonymous': True,
            'pages': [{
                'parent_id': -1,
                'seq': 0,
                'sections': [{
                    'data': {'help_text': '', 'question_text': '', 'seq': 0},
                    'fields': [{
                        'data': {
                            'field_type': 'textField',
                            'question_text': 'Feedback',
                            'seq': 0,
                            'required': False,
                            'parent_id': -1,
                            'attrs': {'charlimits': '0,200'},
                            'help_text': ''
                        }
                    }]
                }]
            }],
            'link_type': '-1',
            'desc': 'Anonymous submission test'
        }
        self.client.login(username=self.admin.username, password='password')
        self.client.post(
            '/customforms/submit/',
            json.dumps(form_data),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.form = Form.objects.get(title='Anon Submit Form')
        self.feedback_field_id = self.form.field_set.get(label='Feedback').id

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def test_anon_user_can_view_anonymous_form(self):
        """Unauthenticated user can GET an anonymous form."""
        self.client.logout()
        response = self.client.get(f'/customforms/view/{self.form.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Feedback')

    def test_anon_user_can_submit_anonymous_form(self):
        """Unauthenticated user can POST to an anonymous form and is redirected to success."""
        self.client.logout()
        response = self.client.post(f'/customforms/view/{self.form.id}/', {
            'combo_form-current_step': '0',
            f'question_{self.feedback_field_id}': 'Great event!',
        })
        self.assertRedirects(response, f'/customforms/success/{self.form.id}/')

    def test_anon_submission_stored_without_user(self):
        """Response from anonymous submission is stored with no user_id column."""
        self.client.logout()
        self.client.post(f'/customforms/view/{self.form.id}/', {
            'combo_form-current_step': '0',
            f'question_{self.feedback_field_id}': 'Nice!',
        })
        dmh = DynamicModelHandler(self.form)
        model = dmh.createDynModel()
        self.assertEqual(model.objects.count(), 1)
        record = model.objects.first()
        # Anonymous forms do not store a user_id column
        self.assertFalse(hasattr(record, 'user_id'))


# ===========================================================================
# 13. Correct-answer validator integration via form view
# ===========================================================================

class CorrectAnswerValidatorIntegrationTest(TestCase):
    """Integration tests: correct_answer attribute triggers validation in the live view."""

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='ca_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.student, _ = ESPUser.objects.get_or_create(username='ca_student')
        self.student.set_password('password')
        self.student.save()
        self.student.makeRole('Student')

        form_data = {
            'title': 'Quiz Form',
            'perms': '',
            'link_id': -1,
            'success_url': '/done/',
            'success_message': 'Correct!',
            'anonymous': False,
            'pages': [{
                'parent_id': -1,
                'seq': 0,
                'sections': [{
                    'data': {'help_text': '', 'question_text': '', 'seq': 0},
                    'fields': [{
                        'data': {
                            'field_type': 'textField',
                            'question_text': 'Capital of France',
                            'seq': 0,
                            'required': True,
                            'parent_id': -1,
                            'attrs': {'correct_answer': 'Paris', 'charlimits': '0,50'},
                            'help_text': ''
                        }
                    }]
                }]
            }],
            'link_type': '-1',
            'desc': 'Quiz'
        }
        self.client.login(username=self.admin.username, password='password')
        self.client.post(
            '/customforms/submit/',
            json.dumps(form_data),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.form = Form.objects.get(title='Quiz Form')
        self.q_id = self.form.field_set.get(label='Capital of France').id

    def tearDown(self):
        for form in Form.objects.all():
            DynamicModelHandler(form).purgeDynModel()

    def test_wrong_answer_shows_error(self):
        """Posting the wrong answer shows an 'Incorrect answer' error."""
        self.client.login(username=self.student.username, password='password')
        response = self.client.post(f'/customforms/view/{self.form.id}/', {
            'combo_form-current_step': '0',
            f'question_{self.q_id}': 'London',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Incorrect answer')

    def test_correct_answer_redirects_to_success(self):
        """Posting the correct answer redirects to success."""
        self.client.login(username=self.student.username, password='password')
        response = self.client.post(f'/customforms/view/{self.form.id}/', {
            'combo_form-current_step': '0',
            f'question_{self.q_id}': 'Paris',
        })
        self.assertRedirects(response, f'/customforms/success/{self.form.id}/')
