__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2026 by the individual contributors
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

"""
Tests for esp.program.controllers.studentregsanity (StudentRegSanityController).

These tests verify the sanity-check controller that detects and optionally
removes invalid StudentRegistration records (walk-ins registered in regular
classes, students enrolled in lunch blocks, etc.).

Design principles:
- Tests assert *behaviour*, not just coverage — each test verifies a
  meaningful contract so that future regressions are caught.
- Tests run in dry-run / fake mode by default so no DB state is mutated
  unintentionally; mutation tests explicitly flip fake=False and verify
  the side-effects.
- Fixtures use ProgramFrameworkTest where a full program environment is
  needed, and minimal manual fixtures otherwise.
"""

import datetime

from django.test import TestCase

from esp.program.tests import ProgramFrameworkTest
from esp.program.models import StudentRegistration, RegistrationType
from esp.program.models.class_ import ClassCategories, ClassSubject, ClassSection
from esp.program.controllers.studentregsanity import StudentRegSanityController
from esp.tests.util import CacheFlushTestCase, user_role_setup
from esp.users.models import ESPUser, StudentInfo
from esp.program.models import RegistrationProfile


# ---------------------------------------------------------------------------
# Base fixture helper
# ---------------------------------------------------------------------------

class StudentRegSanityFrameworkTest(ProgramFrameworkTest):
    """
    Extends ProgramFrameworkTest with helpers to create Walk-in and Lunch
    class categories and enrol students into them — isolating sanity-check
    scenarios from the regular registration fixtures.
    """

    def setUp(self, *args, **kwargs):
        kwargs.setdefault('num_timeslots', 2)
        kwargs.setdefault('timeslot_length', 50)
        kwargs.setdefault('timeslot_gap', 10)
        kwargs.setdefault('num_teachers', 2)
        kwargs.setdefault('classes_per_teacher', 1)
        kwargs.setdefault('sections_per_class', 1)
        kwargs.setdefault('num_rooms', 2)
        super().setUp(*args, **kwargs)
        self.schedule_randomly()
        self.controller = StudentRegSanityController(self.program)

    # ------------------------------------------------------------------
    # Fixture helpers
    # ------------------------------------------------------------------

    def _get_or_create_category(self, name):
        category, _ = ClassCategories.objects.get_or_create(category=name)
        return category

    def _create_special_class(self, category_name):
        """Create a one-section class belonging to *category_name*."""
        category = self._get_or_create_category(category_name)
        teacher = self.teachers[0]
        cls = ClassSubject.objects.create(
            parent_program=self.program,
            category=category,
            class_size_max=30,
            grade_min=7,
            grade_max=12,
            status=1,
        )
        cls.makeTeacher(teacher)
        section = cls.add_section(duration=1.0)
        section.status = 1
        section.save()
        # Assign a timeslot so the section appears in queries filtered on
        # meeting_times__isnull=False
        timeslot = self.program.getTimeSlots().first()
        if timeslot:
            section.meeting_times.add(timeslot)
        return cls, section

    def _enrol_student(self, student, section, reg_type_name="Enrolled"):
        """Create an active StudentRegistration for *student* in *section*."""
        reg_type, _ = RegistrationType.objects.get_or_create(name=reg_type_name)
        sr = StudentRegistration.objects.create(
            user=student,
            section=section,
            relationship=reg_type,
            start_date=datetime.datetime.now() - datetime.timedelta(hours=1),
            end_date=datetime.datetime.now() + datetime.timedelta(days=30),
        )
        return sr


# ---------------------------------------------------------------------------
# 1.  Constructor tests
# ---------------------------------------------------------------------------

class StudentRegSanityControllerInitTest(StudentRegSanityFrameworkTest):
    """Verify that the controller initialises correctly."""

    def test_init_stores_program(self):
        """Controller must retain the program it was created with."""
        self.assertEqual(self.controller.program, self.program)

    def test_init_default_options(self):
        """Default options are applied when none are passed."""
        ctrl = StudentRegSanityController(self.program)
        import os
        self.assertEqual(ctrl.options['directory'], os.getenv('HOME'))

    def test_init_custom_option_override(self):
        """Custom kwargs override the defaults."""
        ctrl = StudentRegSanityController(self.program, directory='/tmp/test')
        self.assertEqual(ctrl.options['directory'], '/tmp/test')

    def test_init_extra_options_preserved(self):
        """Arbitrary extra kwargs are stored in options without error."""
        ctrl = StudentRegSanityController(self.program, my_custom_key='hello')
        self.assertEqual(ctrl.options['my_custom_key'], 'hello')


# ---------------------------------------------------------------------------
# 2.  sanitize_walkin tests
# ---------------------------------------------------------------------------

class SanitizeWalkinTest(StudentRegSanityFrameworkTest):
    """Tests for StudentRegSanityController.sanitize_walkin()."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.walkin_cls, self.walkin_section = self._create_special_class("Walk-in Activity")

    # --- happy-path: no walk-in registrations ---

    def test_no_walkin_registrations_returns_empty_report(self):
        """When there are no walk-in registrations, report is an empty list."""
        report = self.controller.sanitize_walkin(fake=True)
        # Each entry is (section, count).  All counts should be 0.
        section_counts = [count for _, count in report]
        self.assertTrue(
            all(c == 0 for c in section_counts),
            "Expected all walk-in section counts to be 0 with no enrolments, got: %s" % report,
        )

    # --- happy-path: with walk-in registrations present ---

    def test_walkin_registrations_appear_in_report(self):
        """
        Registrations in a Walk-in section must be counted in the report so
        that administrators know they exist.
        """
        student = self.students[0]
        self._enrol_student(student, self.walkin_section)

        report = self.controller.sanitize_walkin(fake=True)
        walkin_counts = {sec.id: count for sec, count in report if sec.id == self.walkin_section.id}
        self.assertIn(
            self.walkin_section.id, walkin_counts,
            "Walk-in section not present in report",
        )
        self.assertEqual(
            walkin_counts[self.walkin_section.id], 1,
            "Expected 1 walk-in registration, report shows different count",
        )

    def test_multiple_walkin_registrations_counted_correctly(self):
        """Count must match the actual number of enrolments."""
        for student in self.students[:3]:
            self._enrol_student(student, self.walkin_section)

        report = self.controller.sanitize_walkin(fake=True)
        walkin_counts = {sec.id: count for sec, count in report}
        self.assertEqual(
            walkin_counts.get(self.walkin_section.id, 0), 3,
            "Walk-in count mismatch: expected 3",
        )

    # --- dry-run (fake=True) must NOT expire registrations ---

    def test_dry_run_does_not_expire_registrations(self):
        """
        With fake=True, sanitize_walkin must leave all registrations active
        so it is safe to call as a read-only check.
        """
        student = self.students[0]
        sr = self._enrol_student(student, self.walkin_section)

        self.controller.sanitize_walkin(fake=True)

        sr.refresh_from_db()
        self.assertFalse(
            sr.is_expired(),
            "sanitize_walkin(fake=True) must not expire any registrations",
        )

    # --- real mode (fake=False) MUST expire registrations ---

    def test_real_run_expires_walkin_registrations(self):
        """
        With fake=False the walk-in registrations must be expired so
        subsequent live queries no longer count the student as enrolled.
        """
        student = self.students[0]
        sr = self._enrol_student(student, self.walkin_section)

        self.controller.sanitize_walkin(fake=False)

        sr.refresh_from_db()
        self.assertTrue(
            sr.is_expired(),
            "sanitize_walkin(fake=False) must expire walk-in registrations",
        )

    # --- regular class registrations are NOT touched ---

    def test_regular_class_registrations_unaffected(self):
        """
        Walk-in sanitisation must never touch registrations in ordinary
        (non-walk-in) class sections.
        """
        regular_section = self.program.sections().filter(
            parent_class__category__category="Core"  # or whatever the default is
        ).first()
        if regular_section is None:
            # Use any non-walkin section
            regular_section = self.program.sections().exclude(
                parent_class__category__category="Walk-in Activity"
            ).first()
        if regular_section is None:
            self.skipTest("No non-walk-in section available in test program")

        student = self.students[0]
        sr = self._enrol_student(student, regular_section)

        self.controller.sanitize_walkin(fake=False)

        sr.refresh_from_db()
        self.assertFalse(
            sr.is_expired(),
            "sanitize_walkin must not expire registrations for normal classes",
        )

    # --- return value structure is always a list ---

    def test_return_value_is_list(self):
        """Return type must be a list regardless of walk-in enrolment state."""
        report = self.controller.sanitize_walkin(fake=True)
        self.assertIsInstance(report, list, "sanitize_walkin must return a list")

    def test_report_entries_are_tuples_of_section_and_int(self):
        """Each entry in the report must be a (ClassSection, int) tuple."""
        self._enrol_student(self.students[0], self.walkin_section)
        report = self.controller.sanitize_walkin(fake=True)
        for entry in report:
            self.assertEqual(len(entry), 2, "Each report entry must be a 2-tuple")
            sec, count = entry
            self.assertIsInstance(sec, ClassSection)
            self.assertIsInstance(count, int)


# ---------------------------------------------------------------------------
# 3.  sanitize_lunch tests
# ---------------------------------------------------------------------------

class SanitizeLunchTest(StudentRegSanityFrameworkTest):
    """Tests for StudentRegSanityController.sanitize_lunch()."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.lunch_cls, self.lunch_section = self._create_special_class("Lunch")

    # --- no lunch registrations ---

    def test_no_lunch_registrations_returns_empty_counts(self):
        """Report should show zero enrolments when no one is enrolled in lunch."""
        report = self.controller.sanitize_lunch(fake=True)
        counts = [count for _, count in report]
        self.assertTrue(
            all(c == 0 for c in counts),
            "Expected all lunch counts to be 0 with no enrolments",
        )

    # --- lunch registrations are detected ---

    def test_lunch_registrations_appear_in_report(self):
        """Students enrolled in a Lunch class must appear in the sanity report."""
        student = self.students[0]
        self._enrol_student(student, self.lunch_section)

        report = self.controller.sanitize_lunch(fake=True)
        lunch_counts = {cls.id: count for cls, count in report}
        self.assertIn(
            self.lunch_cls.id, lunch_counts,
            "Lunch class not found in report",
        )
        self.assertEqual(
            lunch_counts[self.lunch_cls.id], 1,
            "Expected exactly 1 lunch registration in report",
        )

    def test_multiple_lunch_registrations_counted_correctly(self):
        """Count must reflect all enrolled students."""
        for student in self.students[:2]:
            self._enrol_student(student, self.lunch_section)

        report = self.controller.sanitize_lunch(fake=True)
        lunch_counts = {cls.id: count for cls, count in report}
        self.assertEqual(
            lunch_counts.get(self.lunch_cls.id, 0), 2,
            "Lunch count mismatch: expected 2",
        )

    # --- dry-run safety ---

    def test_dry_run_does_not_expire_lunch_registrations(self):
        """fake=True must not alter any DB state."""
        student = self.students[0]
        sr = self._enrol_student(student, self.lunch_section)

        self.controller.sanitize_lunch(fake=True)

        sr.refresh_from_db()
        self.assertFalse(
            sr.is_expired(),
            "sanitize_lunch(fake=True) must not expire registrations",
        )

    # --- real run expires lunch registrations ---

    def test_real_run_expires_lunch_registrations(self):
        """fake=False must expire all lunch registrations."""
        student = self.students[0]
        sr = self._enrol_student(student, self.lunch_section)

        self.controller.sanitize_lunch(fake=False)

        sr.refresh_from_db()
        self.assertTrue(
            sr.is_expired(),
            "sanitize_lunch(fake=False) must expire lunch registrations",
        )

    def test_real_run_expires_all_students_in_lunch(self):
        """Every enrolled student's registration must be expired, not just the first."""
        srs = [self._enrol_student(s, self.lunch_section) for s in self.students[:3]]
        self.controller.sanitize_lunch(fake=False)
        for sr in srs:
            sr.refresh_from_db()
            self.assertTrue(
                sr.is_expired(),
                "Registration for student %s was not expired" % sr.user,
            )

    # --- return value ---

    def test_return_value_is_list(self):
        report = self.controller.sanitize_lunch(fake=True)
        self.assertIsInstance(report, list)

    def test_report_entries_are_class_and_int(self):
        """Each entry is a (ClassSubject, int) pair."""
        self._enrol_student(self.students[0], self.lunch_section)
        report = self.controller.sanitize_lunch(fake=True)
        for entry in report:
            self.assertEqual(len(entry), 2)
            cls_obj, count = entry
            self.assertIsInstance(count, int)


# ---------------------------------------------------------------------------
# 4.  sanitize() dispatcher tests
# ---------------------------------------------------------------------------

class SanitizeDispatcherTest(StudentRegSanityFrameworkTest):
    """Tests for the sanitize() top-level dispatcher method."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.walkin_cls, self.walkin_section = self._create_special_class("Walk-in Activity")
        self.lunch_cls, self.lunch_section = self._create_special_class("Lunch")

    # --- None / missing checks argument ---

    def test_none_checks_returns_none(self):
        """Calling sanitize() with checks=None prints a warning and returns None."""
        result = self.controller.sanitize(checks=None, fake=True, csvlog=False)
        self.assertIsNone(result, "sanitize(checks=None) must return None")

    # --- help string ---

    def test_help_returns_none(self):
        """sanitize('--help') is informational and must return None."""
        result = self.controller.sanitize(checks='--help', fake=True, csvlog=False)
        self.assertIsNone(result, "sanitize('--help') must return None")

    # --- antiwalk-in check ---

    def test_antiwalk_in_dispatches_to_sanitize_walkin(self):
        """
        Passing 'antiwalk-in' must call sanitize_walkin and place its result
        under 'walkin' in the returned dict.
        """
        result = self.controller.sanitize(
            checks=['antiwalk-in'], fake=True, csvlog=False
        )
        self.assertIsNotNone(result, "sanitize must return a dict when checks are provided")
        self.assertIn('walkin', result, "Result dict must contain 'walkin' key")
        self.assertIsInstance(result['walkin'], list)

    # --- antilunch check ---

    def test_antilunch_dispatches_to_sanitize_lunch(self):
        """
        Passing 'antilunch' must call sanitize_lunch and place its result
        under 'antilunch' in the returned dict.
        """
        result = self.controller.sanitize(
            checks=['antilunch'], fake=True, csvlog=False
        )
        self.assertIsNotNone(result)
        self.assertIn('antilunch', result, "Result dict must contain 'antilunch' key")
        self.assertIsInstance(result['antilunch'], list)

    # --- both checks together ---

    def test_multiple_checks_run_all(self):
        """Both antiwalk-in and antilunch run when both are specified."""
        result = self.controller.sanitize(
            checks=['antiwalk-in', 'antilunch'], fake=True, csvlog=False
        )
        self.assertIn('walkin', result)
        self.assertIn('antilunch', result)

    # --- string shorthand (not a list) ---

    def test_single_string_check_treated_as_list(self):
        """
        A bare string 'antiwalk-in' must be treated the same as ['antiwalk-in']
        (the method wraps it internally).
        """
        result = self.controller.sanitize(
            checks='antiwalk-in', fake=True, csvlog=False
        )
        self.assertIn('walkin', result)

    # --- unknown check name is silently ignored ---

    def test_unknown_check_does_not_crash(self):
        """An unrecognised check name must not raise an exception."""
        try:
            result = self.controller.sanitize(
                checks=['nonexistent_check'], fake=True, csvlog=False
            )
            # Result dict should be empty (no matching handlers)
            self.assertIsNotNone(result)
        except Exception as exc:
            self.fail("sanitize() raised an unexpected exception for unknown check: %s" % exc)

    # --- end-to-end: fake=False actually removes records ---

    def test_end_to_end_antiwalk_in_real_run(self):
        """
        Full integration: after a real antiwalk-in run, the walk-in student
        registration must be expired and no longer appear in live queries.
        """
        student = self.students[0]
        sr = self._enrol_student(student, self.walkin_section)

        self.controller.sanitize(checks=['antiwalk-in'], fake=False, csvlog=False)

        sr.refresh_from_db()
        self.assertTrue(
            sr.is_expired(),
            "Walk-in registration must be expired after real antiwalk-in run",
        )

    def test_end_to_end_antilunch_real_run(self):
        """
        Full integration: after a real antilunch run, the lunch student
        registration must be expired.
        """
        student = self.students[0]
        sr = self._enrol_student(student, self.lunch_section)

        self.controller.sanitize(checks=['antilunch'], fake=False, csvlog=False)

        sr.refresh_from_db()
        self.assertTrue(
            sr.is_expired(),
            "Lunch registration must be expired after real antilunch run",
        )

    # --- returned reports dict structure ---

    def test_returned_dict_is_dict(self):
        result = self.controller.sanitize(
            checks=['antiwalk-in', 'antilunch'], fake=True, csvlog=False
        )
        self.assertIsInstance(result, dict)

    def test_returned_dict_stored_on_self(self):
        """
        The dispatcher must also store the result on self.reports so callers
        can still access it after the method returns.
        """
        self.controller.sanitize(
            checks=['antiwalk-in'], fake=True, csvlog=False
        )
        self.assertTrue(
            hasattr(self.controller, 'reports'),
            "sanitize() must set self.reports",
        )
        self.assertIn('walkin', self.controller.reports)
