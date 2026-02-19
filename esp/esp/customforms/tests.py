from __future__ import absolute_import
import six
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

from esp.customforms.models import Form, Field
from esp.customforms.DynamicModel import DynamicModelHandler
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
            self.assertRedirects(response, '/accounts/login/?next=%s' % url)

        self.client.login(username=self.student.username, password='password')
        for url in urls:
            response = self.client.get(url)
            self.assertRedirects(response, '/accounts/login/?next=%s' % url)

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
            'perms': six.u(''),
            'link_id': -1,
            'success_url': '/formsuccess.html',
            'success_message': 'Thank you!',
            'anonymous': False,
            'pages': [{
                'parent_id': -1,
                'sections': [{
                    'fields': [
                        {'data': {'field_type': 'textField', 'question_text': 'ShortText', 'seq': 0, 'required': True, 'parent_id': -1, 'attrs':{'correct_answer': 'Smart', 'charlimits': '0,100'}, 'help_text': 'Instructions'}},
                        {'data': {'field_type': 'phone', 'question_text': 'Your phone no.', 'seq': 1, 'required': True, 'parent_id': -1, 'attrs': {}, 'help_text': six.u('')}},
                        {'data': {'field_type': 'gender', 'question_text': 'Your gender', 'seq': 2, 'required': True, 'parent_id': -1, 'attrs': {}, 'help_text': six.u('')}},
                        {'data': {'field_type': 'radio', 'question_text': 'Choose an option', 'seq': 3, 'required': True, 'parent_id': -1, 'attrs': {'correct_answer': '1', 'options': 'A|B|C|'}, 'help_text': six.u('')}},
                        {'data': {'field_type': 'boolean', 'question_text': 'True/false', 'seq': 4, 'required': True, 'parent_id': -1, 'attrs': {}, 'help_text':six.u('')}},
                        {'data': {'field_type': 'textField', 'question_text': 'NonRequired', 'seq': 5, 'required': False, 'parent_id': -1, 'attrs': {'correct_answer': six.u(''), 'charlimits': ','}, 'help_text': six.u('')}}
                    ],
                'data': {'help_text': six.u(''), 'question_text': six.u(''), 'seq': 0}
                }],
                'seq': 0
            }],
            'link_type': '-1',
            'desc': 'Test'
        }

        response = self.client.post("/customforms/submit/", json.dumps(form_data), content_type='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(six.text_type(response.content, encoding='UTF-8'), "OK")

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
        response = self.client.get("/customforms/view/%d/" % form.id)
        self.assertEqual(response.status_code, 200)

        #   - Build an initial set of responses
        responses_initial = {}
        responses_initial['question_%d' % field_id_map['ShortText']] = 'Dumb'
        responses_initial['question_%d' % field_id_map['Your phone no.']] = '(201) 426-5797'
        responses_initial['question_%d' % field_id_map['Your gender']] = 'F'
        responses_initial['question_%d' % field_id_map['Choose an option']] = 'A'
        responses_initial['question_%d' % field_id_map['True/false']] = 'on'
        responses_initial['question_%d' % field_id_map['NonRequired']] = 'test'

        #   - Make sure validation catches incorrect response
        #     (for the question with a correct answer)
        post_dict = {'combo_form-current_step': '0'}
        post_dict.update(responses_initial)
        response = self.client.post("/customforms/view/%d/" % form.id, post_dict)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Incorrect answer')
        responses_corrected = responses_initial
        responses_corrected['question_%d' % field_id_map['ShortText']] = 'Smart'
        responses_initial['question_%d' % field_id_map['Choose an option']] = 'B'
        post_dict.update(responses_corrected)
        response = self.client.post("/customforms/view/%d/" % form.id, post_dict)
        self.assertRedirects(response, "/customforms/success/%s/" % form.id)
        response = self.client.get("/customforms/success/%d/" % form.id)
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
    """Tests for formBuilder() — context data and access control."""
    
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
