"""
Behavioral tests for LotteryStudentRegModule
(esp/program/modules/handlers/lotterystudentregmodule.py).

LotteryStudentRegTest (studentregmodules.py) already covers students() and
isCompleted(). This file adds tests for the HTTP-layer views: timeslots_json()
and viewlotteryprefs().

Refs: #3780, #3773
"""

import json

from esp.program.models import StudentRegistration, RegistrationType
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest


class LotteryTimeslotsJsonTest(ModuleHandlerTestMixin, ProgramFrameworkTest):
    """Tests for timeslots_json() — the JSON endpoint serving the lottery UI."""

    def _url(self):
        return self.get_module_url('learn', 'timeslots_json')

    def test_timeslots_json_returns_200(self):
        """timeslots_json() is publicly accessible and returns 200."""
        # no_auth decorator — no login required
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)

    def test_timeslots_json_content_type(self):
        """Response is JSON."""
        response = self.client.get(self._url())
        self.assertIn('application/json', response.get('Content-Type', ''))

    def test_timeslots_json_returns_list_of_id_name_pairs(self):
        """Response body is a JSON array of [id, short_description] pairs."""
        response = self.client.get(self._url())
        data = json.loads(response.content)
        self.assertIsInstance(data, list)
        for item in data:
            self.assertEqual(len(item), 2, 'Each timeslot entry should be [id, short_description]')
            self.assertIsInstance(item[0], int)
            self.assertIsInstance(item[1], str)

    def test_timeslots_json_matches_program_timeslots(self):
        """Returned timeslot IDs match the program's getTimeSlotList()."""
        response = self.client.get(self._url())
        data = json.loads(response.content)
        returned_ids = [item[0] for item in data]
        # Sort timeslots by start time, then extract IDs
        timeslots = sorted(self.program.getTimeSlotList(), key=lambda ts: ts.start)
        expected_ids = [ts.id for ts in timeslots]
        self.assertEqual(returned_ids, expected_ids)


class LotteryViewPrefsTest(ModuleHandlerTestMixin, ProgramFrameworkTest):
    """Tests for viewlotteryprefs() — shows a student's priority/interested SRs."""

    def setUp(self):
        super().setUp()
        self.add_user_profiles()
        self.schedule_randomly()
        self.student = self.students[0]
        self.priority_rt, _ = RegistrationType.objects.get_or_create(
            name='Priority/1', defaults={'category': 'student'}
        )

    def _url(self):
        return self.get_module_url('learn', 'viewlotteryprefs')

    def test_unauthenticated_redirects(self):
        """Unauthenticated GET redirects to login (302)."""
        self.client.logout()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 302)

    def test_student_with_priority_sees_registration(self):
        """Student with a Priority/1 SR sees it in viewlotteryprefs context."""
        section = self.program.sections().filter(
            meeting_times__isnull=False
        ).first()
        if section is None:
            self.skipTest('No scheduled section available')

        StudentRegistration.objects.create(
            user=self.student,
            section=section,
            relationship=self.priority_rt,
        )
        self.client.login(username=self.student.username, password='password')
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            response.context.get('pempty', True),
            'pempty should be False when student has Priority/1 registrations'
        )
