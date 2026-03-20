__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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

from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import override_settings

from esp.program.models import PhaseZeroRecord
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.users.models import Permission


@override_settings(
    STRIPE_PUBLISHABLE_KEY='pk_test_123456789',
    STRIPE_SECRET_KEY='sk_test_123456789',
)
class StudentRegPhaseZeroTestCase(ProgramFrameworkTest):
    """Test the StudentRegPhaseZero handler.

    These tests focus on the lottery entry workflow for students, including
    permission gating, lottery open/closed behavior, and the creation of
    PhaseZeroRecord objects.
    """

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.student = self.students[0]
        self.url = f"{self.program.get_learn_url()}studentregphasezero"
        self.add_student_profiles()

    def _login_student(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
            "Failed to log in as student"
        )

    def _grant_student_phasezero_permission(self):
        student_group = Group.objects.get(name='Student')
        Permission.objects.get_or_create(
            role=student_group,
            permission_type='Student/PhaseZero',
            program=self.program,
        )

    def _grant_override_phasezero_permission(self):
        student_group = Group.objects.get(name='Student')
        Permission.objects.get_or_create(
            role=student_group,
            permission_type='OverridePhaseZero',
            program=self.program,
        )

    def test_skip_phase_zero_redirects_to_studentreg(self):
        """Students with OverridePhaseZero should be redirected to studentreg."""
        self._grant_override_phasezero_permission()
        self._login_student()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f"{self.program.get_learn_url()}studentreg",
            response.url,
            "Expected a redirect to the main student registration page",
        )

    def test_get_before_opening_requires_student_phasezero_permission(self):
        """Without Student/PhaseZero permission, the lottery page should be closed."""
        Tag.setTag('student_lottery_run', target=self.program, value='False')
        self._login_student()

        # Ensure the student does not already have broad student permissions (e.g. Student/All)
        Permission.objects.filter(
            role__name='Student',
            permission_type='Student/All',
            program=self.program,
        ).delete()

        self.assertFalse(
            Permission.user_has_perm(self.student, 'Student/PhaseZero', program=self.program),
            "Expected student not to have Student/PhaseZero permission before granting it",
        )

        response = self.client.get(self.url)
        self.assertContains(response, "Student Registration Closed")

        # With the permission, the page should show the phase zero sign-up form.
        self._grant_student_phasezero_permission()
        response = self.client.get(self.url)
        self.assertContains(response, "id=\"submit_form\"")

    def test_get_after_lottery_run_shows_closed_message(self):
        """Once the lottery has been run, students who didn't enter get a closed message."""
        Tag.setTag('student_lottery_run', target=self.program, value='True')
        self._login_student()

        response = self.client.get(self.url)
        self.assertContains(response, "Program Lottery Closed")

    def test_get_already_entered_shows_confirmation_and_group_size(self):
        """Students who already entered should see a confirmation page."""
        # Ensure the user has permission to enter the lottery
        self._grant_student_phasezero_permission()
        Tag.setTag('student_lottery_group_max', target=self.program, value='2')

        record = PhaseZeroRecord.objects.create(program=self.program)
        record.user.add(self.student)
        record.save()

        self._login_student()
        response = self.client.get(self.url)

        self.assertContains(response, "This is confirmation that you are entered into our student lottery.")
        self.assertContains(response, "maximum lottery group size is 2")

    def test_get_after_lottery_run_for_entered_student_shows_not_selected_message(self):
        """If the lottery has been run, an entered-but-unselected student sees the not-selected message."""
        # Student has entered the lottery
        record = PhaseZeroRecord.objects.create(program=self.program)
        record.user.add(self.student)
        record.save()
        # Lottery has been run
        Tag.setTag('student_lottery_run', target=self.program, value='True')
        self._login_student()
        response = self.client.get(self.url)
        # The confirmation template branch for "lottery run, not selected" should be rendered.
        self.assertContains(response, "lottery has been run")
        self.assertContains(response, "not selected")

    def test_get_after_lottery_closed_before_run_for_entered_student_shows_closed_message(self):
        """If the lottery is closed (permission false) before it is run, entered students see the closed message."""
        # Student has entered the lottery
        record = PhaseZeroRecord.objects.create(program=self.program)
        record.user.add(self.student)
        record.save()
        # Lottery has not yet been run
        Tag.setTag('student_lottery_run', target=self.program, value='False')
        # Simulate lottery permission being closed/disabled for the student
        Permission.objects.filter(
            permission_type='Student/PhaseZero',
            program=self.program,
        ).delete()
        # Ensure student doesn't skip phase zero
        Permission.objects.filter(
            role__name='Student',
            permission_type='Student/All',
            program=self.program,
        ).delete()
        self._login_student()
        response = self.client.get(self.url)
        # The confirmation template branch for "entered but lottery closed/not started" should be rendered.
        self.assertContains(response, "The student lottery is now closed")
        self.assertContains(response, "This page will be updated once the lottery has been run")

    @patch('esp.program.modules.handlers.studentregphasezero.send_mail')
    def test_post_creates_phasezero_record_and_sends_confirmation_email(self, mock_send_mail):
        """Posting should create a PhaseZeroRecord and send a confirmation email."""
        self._grant_student_phasezero_permission()
        Tag.setTag('student_lottery_group_max', target=self.program, value='2')

        self._login_student()

        self.assertEqual(PhaseZeroRecord.objects.filter(program=self.program).count(), 0)

        response = self.client.post(self.url, data={})

        self.assertEqual(PhaseZeroRecord.objects.filter(program=self.program).count(), 1)
        record = PhaseZeroRecord.objects.get(program=self.program)
        self.assertIn(self.student, list(record.user.all()))

        mock_send_mail.assert_called_once()
        self.assertContains(response, "This is confirmation that you are entered into our student lottery.")
