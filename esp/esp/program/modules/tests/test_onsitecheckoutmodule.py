"""
Unit tests for OnSiteCheckoutModule (onsitecheckoutmodule.py).

"""
from unittest.mock import patch

from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import Record, RecordType


class OnSiteCheckoutModuleTest(ModuleHandlerTestMixin, ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 4, 'num_teachers': 1, 'num_admins': 1})
        super().setUp(*args, **kwargs)
        self.add_user_profiles()
        self.module = self.get_module_obj('OnSiteCheckoutModule')
        self.checkout_rt, _ = RecordType.objects.get_or_create(name='checked_out')
        self.attended_rt, _ = RecordType.objects.get_or_create(name='attended')

    def _url(self):
        return self.get_module_url('onsite', 'checkout')

    def _check_in(self, user):
        Record.objects.create(user=user, event=self.attended_rt, program=self.program)

    def test_checkout_page_renders_for_admin(self):
        self.login_as('admin')
        response = self.assert_view_ok(self._url())
        self.assertIn('form', response.context)

    def test_student_cannot_access_checkout(self):
        self.login_as('student')
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'errors/program/notonsite.html')

    def test_single_user_checkout_creates_record(self):
        student = self.students[0]
        self._check_in(student)
        self.login_as('admin')
        response = self.client.post(self._url(), {
            'user': str(student.id),
            'checkout_student': '1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Record.objects.filter(
                user=student, event=self.checkout_rt, program=self.program
            ).exists()
        )
        self.assertIn('checkout_message_success', response.context)

    def test_checkout_warns_when_not_checked_in(self):
        student = self.students[1]
        self.login_as('admin')
        response = self.client.get(self._url() + '?user=%s' % student.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn('checkout_message_warning', response.context)

    def test_checkout_all_with_confirm(self):
        for student in self.students[:2]:
            self._check_in(student)
        self.login_as('admin')
        response = self.client.post(self._url(), {
            'checkoutall': '1',
            'confirm': '1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('checkout_all_message', response.context)
        self.assertEqual(
            response.context['checkout_all_message'],
            'Successfully checked out 2 students',
        )
        self.assertEqual(
            Record.objects.filter(event=self.checkout_rt, program=self.program).count(),
            2,
        )
        for student in self.students[:2]:
            self.assertEqual(
                Record.objects.filter(
                    user=student, event=self.checkout_rt, program=self.program
                ).count(),
                1,
            )
        for student in self.students[2:]:
            self.assertFalse(
                Record.objects.filter(
                    user=student, event=self.checkout_rt, program=self.program
                ).exists()
            )

    def test_checkout_all_zero_students(self):
        self.login_as('admin')
        response = self.client.post(self._url(), {
            'checkoutall': '1',
            'confirm': '1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('checkout_all_message', response.context)
        self.assertEqual(
            response.context['checkout_all_message'],
            'Successfully checked out 0 students',
        )
        self.assertEqual(
            Record.objects.filter(event=self.checkout_rt, program=self.program).count(),
            0,
        )

    def test_checkout_all_single_student(self):
        self._check_in(self.students[0])
        self.login_as('admin')
        response = self.client.post(self._url(), {
            'checkoutall': '1',
            'confirm': '1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('checkout_all_message', response.context)
        self.assertEqual(
            response.context['checkout_all_message'],
            'Successfully checked out 1 student',
        )
        self.assertEqual(
            Record.objects.filter(event=self.checkout_rt, program=self.program).count(),
            1,
        )

    def test_checkout_all_excludes_already_checked_out(self):
        self._check_in(self.students[0])
        self._check_in(self.students[1])
        # Student 1 is already checked out beforehand
        Record.objects.create(
            user=self.students[1], event=self.checkout_rt, program=self.program
        )
        self.login_as('admin')
        response = self.client.post(self._url(), {
            'checkoutall': '1',
            'confirm': '1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['checkout_all_message'],
            'Successfully checked out 1 student',
        )
        # Student 0 received exactly 1 checkout record
        self.assertEqual(
            Record.objects.filter(
                user=self.students[0], event=self.checkout_rt, program=self.program
            ).count(),
            1,
        )
        # Student 1 was already checked out; no duplicate record was created
        self.assertEqual(
            Record.objects.filter(
                user=self.students[1], event=self.checkout_rt, program=self.program
            ).count(),
            1,
        )

    def test_checkout_all_atomic_rollback_on_error(self):
        for student in self.students[:2]:
            self._check_in(student)
        self.login_as('admin')

        original_create = Record.objects.create
        call_count = 0

        def failing_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Simulated DB error during checkout")
            return original_create(*args, **kwargs)

        with patch.object(Record.objects, 'create', side_effect=failing_create):
            with self.assertRaises(RuntimeError):
                self.client.post(self._url(), {
                    'checkoutall': '1',
                    'confirm': '1',
                })

        # Due to transaction.atomic, no checkout records should remain from the failed batch
        self.assertEqual(
            Record.objects.filter(event=self.checkout_rt, program=self.program).count(),
            0,
        )

    def test_invalid_user_raises_error(self):
        self.login_as('admin')
        response = self.client.get(self._url() + '?user=not-a-real-user-xyz')
        self.assertEqual(response.status_code, 500)
        self.assertTemplateUsed(response, 'error.html')
        self.assertEqual(response.context['error_type'], 'ESPError_NoLog')
        self.assertIn('does not appear to exist', str(response.context['error']))

    def test_lookup_by_username(self):
        student = self.students[2]
        self.login_as('admin')
        response = self.client.get(self._url() + '?user=%s' % student.username)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['student'].id, student.id)

    def test_lookup_via_search_form(self):
        student = self.students[3]
        self.login_as('admin')
        response = self.client.post(self._url(), {
            'target_user': str(student.id),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['student'].id, student.id)
