"""
Unit tests for ListGenModule (listgenmodule.py).

"""
from django.db.models import Q
from django.http import QueryDict

from esp.program.modules.handlers.listgenmodule import ListGenModule, ListGenForm, UserAttributeGetter
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, PersistentQueryFilter


class ListGenModuleTest(ModuleHandlerTestMixin, ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 3, 'num_teachers': 1, 'num_admins': 1})
        super().setUp(*args, **kwargs)
        self.add_user_profiles()
        self.module = self.get_module_obj('ListGenModule')

    def _make_filter(self, users):
        q = Q(id__in=[u.id for u in users])
        return PersistentQueryFilter.create_from_Q(ESPUser, q)

    def test_select_list_page_renders_for_admin(self):
        self.login_as('admin')
        response = self.assert_view_ok(self.get_module_url('manage', 'selectList'))
        self.assertTemplateUsed(response, 'program/modules/listgenmodule/search.html')

    def test_student_cannot_access_select_list(self):
        self.login_as('student')
        response = self.client.get(self.get_module_url('manage', 'selectList'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'errors/program/notanadmin.html')

    def test_generate_list_html_output(self):
        self.login_as('admin')
        filter_obj = self._make_filter(self.students[:2])
        url = self.get_module_url('manage', 'generateList') + '?filterid=%s' % filter_obj.id
        response = self.client.post(url, {
            'fields': ['02_username', '04_firstname', '05_lastname', '06_email'],
            'output_type': 'html',
            'recipient_type': 'student',
        })
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        for student in self.students[:2]:
            self.assertIn(student.username, content)

    def test_generate_list_csv_output(self):
        self.login_as('admin')
        filter_obj = self._make_filter([self.students[0]])
        url = self.get_module_url('manage', 'generateList') + '?filterid=%s' % filter_obj.id
        response = self.client.post(url, {
            'fields': ['02_username', '04_firstname', '05_lastname'],
            'output_type': 'csv',
            'recipient_type': 'student',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('attachment', response.get('Content-Disposition', ''))
        self.assertIn(self.students[0].username, response.content.decode('utf-8'))

    def test_generate_list_missing_filterid_errors(self):
        self.login_as('admin')
        response = self.client.get(self.get_module_url('manage', 'generateList'))
        self.assertEqual(response.status_code, 500)
        self.assertTemplateUsed(response, 'error.html')

    def test_user_attribute_getter_basic_fields(self):
        student = self.students[0]
        ua = UserAttributeGetter(student, self.program)
        self.assertEqual(ua.get('02_username'), student.username)
        self.assertEqual(ua.get('04_firstname'), student.first_name)
        self.assertEqual(ua.get('05_lastname'), student.last_name)
        self.assertEqual(ua.get('06_email'), student.email)
        self.assertEqual(ua.get('01_id'), student.id)

    def test_user_attribute_getter_missing_value_returns_na(self):
        student = self.students[1]
        ua = UserAttributeGetter(student, self.program)
        self.assertEqual(ua.get('24_sibling_name'), 'N/A')

    def test_list_gen_form_filters_fields_by_usertype(self):
        student_form = ListGenForm(usertype='student')
        teacher_form = ListGenForm(usertype='teacher')
        student_labels = [c[1] for c in student_form.fields['fields'].choices]
        teacher_labels = [c[1] for c in teacher_form.fields['fields'].choices]
        self.assertIn('Date of Birth', student_labels)
        self.assertNotIn('Date of Birth', teacher_labels)
        self.assertIn('Major', teacher_labels)

    def test_get_functions_returns_callable_fields(self):
        funcs = UserAttributeGetter.getFunctions()
        self.assertIn('02_username', funcs)
        self.assertEqual(funcs['02_username']['label'], 'Username')
        self.assertIn('any', funcs['02_username']['usertype'])

    def test_process_post_preserves_list_keys(self):
        qd = QueryDict(mutable=True)
        qd.setlist('regtypes', ['Enrolled', 'Applied'])
        qd['simple_key'] = 'x'
        qd['target_user'] = ''
        qd['target_user_raw'] = ''

        class R:
            POST = qd

        data = ListGenModule.processPost(R())
        self.assertEqual(data['regtypes'], ['Enrolled', 'Applied'])
        self.assertEqual(data['simple_key'], 'x')
