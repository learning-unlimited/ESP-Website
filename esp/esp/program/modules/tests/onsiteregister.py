"""
Unit tests for OnSiteRegister (onsiteregister.py).
"""
from unittest.mock import patch

from django.contrib.auth.models import Group

from esp.program.models import RegistrationProfile
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, Record, RecordType


class OnSiteRegisterTest(ModuleHandlerTestMixin, ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 2, 'num_teachers': 1, 'num_admins': 1})
        super().setUp(*args, **kwargs)
        self.module = self.get_module_obj('OnSiteRegister')
        # Built-in RecordTypes come from migrations; only ensure Student group exists.
        Group.objects.get_or_create(name='Student')
        for name in ('attended', 'med', 'liab', 'onsite'):
            if not RecordType.objects.filter(name=name).exists():
                RecordType.objects.create(
                    name=name,
                    description='Test record type %s' % name,
                )

    def _url(self):
        return self.get_module_url('onsite', 'onsite_create')

    def _valid_data(self, **overrides):
        data = {
            'first_name': 'Onsite',
            'last_name': 'Newbie',
            'email': 'onsite.newbie@example.com',
            'grade': '9',
            'school': 'Test High',
            'k12school': '',
            'paid': 'on',
            'medical': 'on',
            'liability': 'on',
        }
        data.update(overrides)
        return data

    def test_form_renders_for_admin(self):
        self.login_as('admin')
        response = self.assert_view_ok(self._url())
        self.assertIn('form', response.context)

    def test_student_cannot_access(self):
        self.login_as('student')
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'errors/program/notonsite.html')

    @patch.object(ESPUser, 'recoverPassword')
    def test_successful_registration(self, mock_recover):
        mock_recover.return_value = None
        self.login_as('admin')
        before = ESPUser.objects.count()
        response = self.client.post(self._url(), self._valid_data())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/onsiteregister/reg_success.html')
        self.assertEqual(ESPUser.objects.count(), before + 1)
        new_user = ESPUser.objects.get(email='onsite.newbie@example.com')
        self.assertTrue(new_user.groups.filter(name='Student').exists())
        self.assertTrue(
            RegistrationProfile.objects.filter(user=new_user, program=self.program).exists()
        )
        self.assertTrue(
            Record.objects.filter(user=new_user, program=self.program, event__name='onsite').exists()
        )
        self.assertTrue(
            Record.objects.filter(user=new_user, program=self.program, event__name='attended').exists()
        )
        self.assertTrue(
            Record.objects.filter(user=new_user, program=self.program, event__name='med').exists()
        )
        self.assertTrue(
            Record.objects.filter(user=new_user, program=self.program, event__name='liab').exists()
        )
        mock_recover.assert_called_once()

    @patch.object(ESPUser, 'recoverPassword')
    def test_invalid_form_stays_on_page(self, mock_recover):
        self.login_as('admin')
        response = self.client.post(self._url(), {
            'first_name': '',
            'last_name': '',
            'email': 'not-an-email',
            'grade': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/onsiteregister/reg_info.html')
        self.assertFalse(ESPUser.objects.filter(email='not-an-email').exists())
        mock_recover.assert_not_called()

    @patch.object(ESPUser, 'recoverPassword')
    def test_username_generated_from_name(self, mock_recover):
        mock_recover.return_value = None
        self.login_as('admin')
        self.client.post(self._url(), self._valid_data(
            first_name='Alice', last_name='Wonder', email='alice.w@example.com'
        ))
        new_user = ESPUser.objects.get(email='alice.w@example.com')
        # get_unused_username uses first initial + last name (e.g. "awonder").
        self.assertTrue(new_user.username)
        self.assertTrue(new_user.username.lower().startswith('a'))
        self.assertIn('wonder', new_user.username.lower())

    @patch.object(ESPUser, 'recoverPassword')
    def test_registration_without_optional_bits(self, mock_recover):
        mock_recover.return_value = None
        self.login_as('admin')
        response = self.client.post(self._url(), self._valid_data(
            email='minimal@example.com',
            paid='',
            medical='',
            liability='',
        ))
        self.assertEqual(response.status_code, 200)
        new_user = ESPUser.objects.get(email='minimal@example.com')
        self.assertFalse(
            Record.objects.filter(user=new_user, program=self.program, event__name='med').exists()
        )
        self.assertFalse(
            Record.objects.filter(user=new_user, program=self.program, event__name='liab').exists()
        )
        self.assertTrue(
            Record.objects.filter(user=new_user, program=self.program, event__name='onsite').exists()
        )
