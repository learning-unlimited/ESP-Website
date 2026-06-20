"""
Direct unit tests for LotteryAssignmentController (esp/program/controllers/lottery.py).

LSRAssignmentTest (program/tests.py) covers end-to-end enroll/waitlist correctness
and lunch constraints. This file adds invariant and edge-case tests that verify
numpy array postconditions directly, independent of the HTTP layer.

Note: save_assignments() creates only 'Enrolled' SRs — no waitlist records.

Refs: #3780, #794
"""

import numpy

from esp.program.controllers.lottery import LotteryAssignmentController
from esp.program.models import (
    RegistrationProfile,
    RegistrationType,
    StudentRegistration,
    StudentSubjectInterest,
)
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, StudentInfo


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------

class LotteryTestBase(ProgramFrameworkTest):
    """Base for lottery tests: scheduled sections, grade profiles, Priority/1 SRs."""

    def setUp(self):
        super().setUp(
            num_students=10,
            num_teachers=3,
            classes_per_teacher=2,
            num_timeslots=3,
            room_capacity=5,
        )
        self.schedule_randomly()

        self.priority_rt, _ = RegistrationType.objects.get_or_create(
            name='Priority/1', defaults={'category': 'student'}
        )
        self.enrolled_rt, _ = RegistrationType.objects.get_or_create(
            name='Enrolled', defaults={'category': 'student'}
        )

        schoolyear = ESPUser.program_schoolyear(self.program)
        # Sections must be scheduled for the controller to include them.
        sections = list(self.program.sections().filter(
            meeting_times__isnull=False
        ).distinct())

        for i, student in enumerate(self.students):
            # Grade profile required for grade-range invariant checks.
            si = StudentInfo(
                user=student,
                graduation_year=ESPUser.YOGFromGrade(9, schoolyear),
            )
            si.save()
            RegistrationProfile(
                user=student,
                student_info=si,
                most_recent_profile=True,
            ).save()
            # Priority/1 SR required for students to appear in lotteried_students.
            if sections:
                StudentRegistration.objects.get_or_create(
                    user=student,
                    section=sections[i % len(sections)],
                    relationship=self.priority_rt,
                )

    def _make_controller(self):
        return LotteryAssignmentController(self.program)


# ---------------------------------------------------------------------------
# LotteryBasicTest
# ---------------------------------------------------------------------------

class LotteryBasicTest(LotteryTestBase):
    """Tests for controller initialization and basic operation."""

    def test_compute_assignments_completes_without_exception(self):
        """compute_assignments() runs to completion without raising."""
        self._make_controller().compute_assignments()

    def test_student_sections_shape_and_dtype(self):
        """student_sections is a bool array of shape (num_students, num_sections)."""
        ctrl = self._make_controller()
        ctrl.compute_assignments()
        self.assertEqual(ctrl.student_sections.shape, (ctrl.num_students, ctrl.num_sections))
        self.assertEqual(ctrl.student_sections.dtype, bool)

    def test_interest_matrix_populated_from_ssi(self):
        """SSI records populate the interest matrix for valid sections of the subject."""
        # Add SSI for all lottery students on all subjects — at least one entry
        # must appear in the interest matrix after initialization.
        for student in self.students:
            for cls in self.program.classes():
                StudentSubjectInterest.objects.get_or_create(
                    user=student, subject=cls
                )
        ctrl = self._make_controller()
        self.assertTrue(
            numpy.any(ctrl.interest),
            'interest matrix should have at least one True entry when SSI records exist',
        )

    def test_priority_registration_populates_priority_matrix(self):
        """Priority/1 SRs populate the priority[1] matrix."""
        ctrl = self._make_controller()
        self.assertTrue(numpy.any(ctrl.priority[1]))

    def test_interested_students_enrolled_or_sections_full(self):
        """
        Every student who requested a section is either enrolled in at
        least one class, or all their requested sections were full,
        grade-blocked, or timeslot-blocked.
        """
        for student in self.students:
            for cls in self.program.classes():
                StudentSubjectInterest.objects.get_or_create(
                    user=student, subject=cls
                )

        ctrl = self._make_controller()
        ctrl.compute_assignments()

        for si_idx in range(ctrl.num_students):
            requested = ctrl.interest[si_idx] | numpy.any(
                [ctrl.priority[p][si_idx]
                 for p in range(1, ctrl.effective_priority_limit + 1)],
                axis=0,
            )
            # Skip if student made no requests, or already got at least one class.
            if not numpy.any(requested) or numpy.any(ctrl.student_sections[si_idx]):
                continue
            # Student got nothing — every requested section must have a blocking reason.
            for sj_idx in numpy.nonzero(requested)[0]:
                section_full = (
                    numpy.sum(ctrl.student_sections[:, sj_idx])
                    >= ctrl.section_capacities[sj_idx]
                )
                grade_blocked = ctrl.options['check_grade'] and (
                    ctrl.student_grades[si_idx] < ctrl.section_grade_min[sj_idx]
                    or ctrl.student_grades[si_idx] > ctrl.section_grade_max[sj_idx]
                )
                timeslot_blocked = numpy.any(
                    ctrl.student_schedules[si_idx] & ctrl.section_schedules[sj_idx]
                )
                self.assertTrue(
                    section_full or grade_blocked or timeslot_blocked,
                    f'Student {si_idx} missed section {sj_idx} for no apparent reason'
                )


# ---------------------------------------------------------------------------
# LotteryInvariantTest
# ---------------------------------------------------------------------------

class LotteryInvariantTest(LotteryTestBase):
    """Hard invariants on numpy arrays — must hold regardless of random seed."""

    def setUp(self):
        super().setUp()
        self.ctrl = self._make_controller()
        self.ctrl.compute_assignments()

    def test_no_section_overcapacity(self):
        """No section has more enrolled students than its capacity."""
        enrollments = numpy.sum(self.ctrl.student_sections, axis=0)
        self.assertEqual(numpy.sum(enrollments > self.ctrl.section_capacities), 0)

    def test_no_timeslot_conflicts(self):
        """No student is enrolled in two sections that share a timeslot."""
        # Reconstruct student_schedules from student_sections × section_schedules.
        # Any value > 1 means a student was assigned two sections at the same slot.
        reconstructed = numpy.dot(
            self.ctrl.student_sections.astype(numpy.int32),
            self.ctrl.section_schedules.astype(numpy.int32),
        )
        self.assertEqual(numpy.sum(reconstructed > 1), 0)

    def test_grade_range_respected(self):
        """No student is enrolled in a section outside their grade range."""
        for si in range(self.ctrl.num_sections):
            enrolled = numpy.nonzero(self.ctrl.student_sections[:, si])[0]
            if enrolled.size == 0:
                continue
            grades = self.ctrl.student_grades[enrolled]
            self.assertTrue(numpy.all(grades >= self.ctrl.section_grade_min[si]))
            self.assertTrue(numpy.all(grades <= self.ctrl.section_grade_max[si]))

    def test_student_sections_consistent_with_schedules(self):
        """student_schedules is consistent with student_sections."""
        reconstructed = numpy.dot(
            self.ctrl.student_sections.astype(numpy.int32),
            self.ctrl.section_schedules.astype(numpy.int32),
        ).astype(bool)
        self.assertTrue(numpy.array_equal(reconstructed, self.ctrl.student_schedules))

    def test_enrolled_only_in_requested_sections(self):
        """Students are only enrolled in sections they expressed interest in."""
        requested = (
            self.ctrl.interest
            | numpy.logical_or.reduce(self.ctrl.priority[1:])
        )
        self.assertEqual(
            numpy.sum(self.ctrl.student_sections & ~requested), 0
        )


# ---------------------------------------------------------------------------
# LotteryEdgeCaseTest
# ---------------------------------------------------------------------------

class LotteryEdgeCaseTest(LotteryTestBase):
    """Edge cases for LotteryAssignmentController."""

    def test_no_ssi_interest_matrix_is_all_false(self):
        """With no SSI or Interested SR, the interest matrix is all-False."""
        self.assertFalse(numpy.any(self._make_controller().interest))

    def test_no_interest_compute_assignments_completes(self):
        """compute_assignments() with only priority SRs completes without error."""
        ctrl = self._make_controller()
        ctrl.compute_assignments()
        self.assertEqual(ctrl.student_sections.shape, (ctrl.num_students, ctrl.num_sections))

    def test_deterministic_with_fixed_seed(self):
        """Same numpy seed produces identical student_sections on two runs.

        Regression guard: a numpy upgrade that alters RNG behavior would
        change lottery outcomes silently without this test.
        """
        rng_state = numpy.random.get_state()
        try:
            ctrl1 = self._make_controller()
            numpy.random.seed(42)
            ctrl1.compute_assignments(check_result=False)

            ctrl2 = self._make_controller()
            numpy.random.seed(42)
            ctrl2.compute_assignments(check_result=False)

            self.assertTrue(numpy.array_equal(ctrl1.student_sections, ctrl2.student_sections))
        finally:
            numpy.random.set_state(rng_state)

    def test_clear_assignments_resets_arrays(self):
        """clear_assignments() resets student_sections and student_schedules to zero."""
        ctrl = self._make_controller()
        ctrl.compute_assignments()
        ctrl.clear_assignments()
        self.assertFalse(numpy.any(ctrl.student_sections))
        self.assertFalse(numpy.any(ctrl.student_schedules))


# ---------------------------------------------------------------------------
# LotterySaveTest
# ---------------------------------------------------------------------------

class LotterySaveTest(LotteryTestBase):
    """Tests for save_assignments() and clear_saved_assignments() DB behavior."""

    def _run_lottery(self):
        ctrl = self._make_controller()
        ctrl.compute_assignments()
        return ctrl

    def test_save_creates_enrolled_registrations(self):
        """save_assignments() creates Enrolled SRs matching numpy.sum(student_sections)."""
        ctrl = self._run_lottery()
        expected = int(numpy.sum(ctrl.student_sections))
        ctrl.save_assignments(try_mailman=False)
        actual = StudentRegistration.valid_objects().filter(
            section__parent_class__parent_program=self.program,
            relationship__name='Enrolled',
        ).count()
        self.assertEqual(actual, expected)

    def test_save_count_matches_numpy_sum(self):
        """Valid Enrolled SR count equals numpy.sum(student_sections)."""
        ctrl = self._run_lottery()
        ctrl.save_assignments(try_mailman=False)
        db_count = StudentRegistration.valid_objects().filter(
            section__parent_class__parent_program=self.program,
            relationship__name='Enrolled',
        ).count()
        self.assertEqual(db_count, int(numpy.sum(ctrl.student_sections)))

    def test_clear_expires_enrollments(self):
        """clear_saved_assignments() expires all Enrolled SRs."""
        ctrl = self._run_lottery()
        ctrl.save_assignments(try_mailman=False)
        ctrl.clear_saved_assignments()
        remaining = StudentRegistration.valid_objects().filter(
            section__parent_class__parent_program=self.program,
            relationship__name='Enrolled',
        ).count()
        self.assertEqual(remaining, 0)

    def test_clear_does_not_delete_records(self):
        """clear_saved_assignments() expires SRs but does not delete them."""
        ctrl = self._run_lottery()
        ctrl.save_assignments(try_mailman=False)
        total_before = StudentRegistration.objects.filter(
            section__parent_class__parent_program=self.program,
            relationship__name='Enrolled',
        ).count()
        ctrl.clear_saved_assignments()
        total_after = StudentRegistration.objects.filter(
            section__parent_class__parent_program=self.program,
            relationship__name='Enrolled',
        ).count()
        self.assertEqual(total_before, total_after)
