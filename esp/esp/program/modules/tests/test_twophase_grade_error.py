"""
Tests that the two-phase lottery endpoints surface grade-range violations as
user-visible warnings instead of silently dropping them.

Issue #1836 — "Two phase lottery needs better error handling"
"""
from __future__ import absolute_import

import json

from django.contrib.messages import get_messages

from esp.tests.util import CacheFlushTestCase
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import (
    ClassSubject, RegistrationProfile, StudentRegistration,
    StudentSubjectInterest, RegistrationType,
)
from esp.users.models import ESPUser, StudentInfo, Permission


class TwoPhaseGradeErrorTest(ProgramFrameworkTest, CacheFlushTestCase):
    """
    Verify that save_priorities and mark_classes_interested emit warnings when
    a student submits a class whose grade range excludes them, rather than
    silently ignoring the submission.
    """

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 1,
            'num_teachers': 1,
            'classes_per_teacher': 1,
            'sections_per_class': 1,
            'num_rooms': 1,
            'num_students': 1,
        })
        super().setUp(*args, **kwargs)

        self.schedule_randomly()

        # Make modules non-required so other modules don't gate the view.
        from esp.program.modules.base import ProgramModuleObj
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        # Open the lottery deadline for all users (null-user permission).
        Permission.objects.create(
            user=None,
            permission_type='Student/Classes/Lottery',
            program=self.program,
        )

        # Give the student a grade-8 profile.
        # Program grade range is 7–12 (set in ProgramFrameworkTest), so grade 8
        # passes @needs_student_in_grade but is below the class range we'll set.
        self.student = self.students[0]
        self.student.set_password('password')
        self.student.save()
        graduation_year = ESPUser.program_schoolyear(self.program) + 4  # grade 8
        si = StudentInfo(user=self.student, graduation_year=graduation_year)
        si.save()
        rp = RegistrationProfile(
            user=self.student,
            program=self.program,
            student_info=si,
            most_recent_profile=True,
        )
        rp.save()

        # Ensure the Priority/1 RegistrationType exists (required by save_priorities).
        RegistrationType.objects.get_or_create(name='Priority/1', category='student')

        # Restrict the class to grades 9–12 so the grade-8 student is excluded.
        cls = self.program.classes().first()
        cls.grade_min = 9
        cls.grade_max = 12
        cls.save()
        cls.accept()
        self.restricted_class = cls
        self.section = cls.get_sections().first()

    # ------------------------------------------------------------------
    # save_priorities — form POST path
    # ------------------------------------------------------------------

    def test_save_priorities_grade_error_creates_warning_message(self):
        """
        POSTing save_priorities for a class the student is below grade for
        must NOT create a StudentRegistration and must set a Django warning
        message explaining the grade restriction.
        """
        self.client.login(username=self.student.username, password='password')

        # Use the timeslot the section was actually scheduled to.
        timeslot = self.section.meeting_times.first()
        self.assertIsNotNone(timeslot, 'Section has no meeting times — schedule_randomly() may have failed.')
        json_data = {str(timeslot.id): {'1': str(self.restricted_class.id)}}

        url = '/learn/%s/save_priorities' % self.program.getUrlBase()
        response = self.client.post(
            url,
            {'json_data': json.dumps(json_data)},
            follow=True,
        )

        # No Priority/1 registration should have been created.
        priority_rel, _ = RegistrationType.objects.get_or_create(
            name='Priority/1', category='student',
        )
        self.assertFalse(
            StudentRegistration.objects.filter(
                user=self.student,
                section=self.section,
                relationship=priority_rel,
            ).exists(),
            'A Priority/1 StudentRegistration was created despite the grade '
            'restriction — the registration should have been refused.',
        )

        # A warning message should be present.
        msgs = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(
            any('grade' in m.lower() for m in msgs),
            'Expected a grade-range warning message, but got: %r' % msgs,
        )

    # ------------------------------------------------------------------
    # mark_classes_interested — AJAX path
    # ------------------------------------------------------------------

    def test_mark_classes_interested_ajax_returns_excluded_ids(self):
        """
        An AJAX POST to mark_classes_interested for a class the student is
        below grade for must return JSON with that class ID in excluded_ids
        and must NOT create a StudentSubjectInterest.
        """
        self.client.login(username=self.student.username, password='password')

        json_data = {
            'interested': [self.restricted_class.id],
            'not_interested': [],
        }

        url = '/learn/%s/mark_classes_interested' % self.program.getUrlBase()
        response = self.client.post(
            url,
            {'json_data': json.dumps(json_data)},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn(
            'excluded_ids', data,
            'Response JSON missing "excluded_ids" key.',
        )
        self.assertIn(
            self.restricted_class.id,
            data['excluded_ids'],
            'Restricted class ID not in excluded_ids.',
        )

        # No StudentSubjectInterest should have been created.
        self.assertFalse(
            StudentSubjectInterest.objects.filter(
                user=self.student,
                subject=self.restricted_class,
            ).exists(),
            'A StudentSubjectInterest was created despite the grade restriction.',
        )

    def test_mark_classes_interested_ajax_eligible_class_not_excluded(self):
        """
        A class that the student IS eligible for must not appear in excluded_ids
        and a StudentSubjectInterest must be created for it.
        """
        self.client.login(username=self.student.username, password='password')

        # Widen the class to cover grade 8 as well.
        self.restricted_class.grade_min = 7
        self.restricted_class.grade_max = 12
        self.restricted_class.save()

        json_data = {
            'interested': [self.restricted_class.id],
            'not_interested': [],
        }

        url = '/learn/%s/mark_classes_interested' % self.program.getUrlBase()
        response = self.client.post(
            url,
            {'json_data': json.dumps(json_data)},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(
            data.get('excluded_ids', []),
            [],
            'Eligible class should not appear in excluded_ids.',
        )
        self.assertTrue(
            StudentSubjectInterest.objects.filter(
                user=self.student,
                subject=self.restricted_class,
            ).exists(),
            'StudentSubjectInterest was not created for an eligible class.',
        )
