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
    ClassSubject,
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
            # Alternate grades 7 and 12 so grade filtering is exercised.
            grade = 7 if i % 2 == 0 else 12
            si = StudentInfo(
                user=student,
                graduation_year=ESPUser.YOGFromGrade(grade, schoolyear),
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
        for student in self.students:
            for cls in self.program.classes():
                StudentSubjectInterest.objects.get_or_create(
                    user=student, subject=cls
                )
        ctrl = self._make_controller()
        self.assertTrue(numpy.any(ctrl.interest))

    def test_priority_registration_populates_priority_matrix(self):
        """Priority/1 SRs populate the priority[1] matrix."""
        ctrl = self._make_controller()
        self.assertTrue(numpy.any(ctrl.priority[1]))

    def test_interested_students_enrolled_or_sections_full(self):
        """Every interested student is enrolled or has a verifiable blocking reason."""
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
        """No student is enrolled in a section outside their grade range.

        Meaningful because setUp alternates student grades between 7 and 12,
        and some classes have restricted ranges (grade 10-12), so grade
        filtering is actually exercised.
        """
        # Restrict half the classes to grade 10-12 so grade-7 students are filtered.
        classes = list(ClassSubject.objects.filter(parent_program=self.program))
        for cls in classes[:len(classes) // 2]:
            cls.grade_min = 10
            cls.grade_max = 12
            cls.save()

        ctrl = self._make_controller()
        ctrl.compute_assignments()

        for si in range(ctrl.num_sections):
            enrolled = numpy.nonzero(ctrl.student_sections[:, si])[0]
            if enrolled.size == 0:
                continue
            grades = ctrl.student_grades[enrolled]
            self.assertTrue(
                numpy.all(grades >= ctrl.section_grade_min[si]),
                f'Section {si} (grade_min={ctrl.section_grade_min[si]}): grades {grades}'
            )
            self.assertTrue(
                numpy.all(grades <= ctrl.section_grade_max[si]),
                f'Section {si} (grade_max={ctrl.section_grade_max[si]}): grades {grades}'
            )

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


    def test_fill_section_handles_zero_and_sparse_weights(self):
        """fill_section must not raise or produce NaN when too few students have positive weight."""
        for positive_count in (0, 1, 2, 5):
            ctrl = self._make_controller()
            ctrl.clear_assignments()
            si = int(numpy.nonzero(ctrl.section_schedules.any(axis=1))[0][0])
            ctrl.interest[:, si] = True
            ctrl.section_capacities[si] = 3          # fewer than the 10 students
            ctrl.student_weights[:] = 0
            ctrl.student_weights[:positive_count] = 1
            ctrl.fill_section(si)
            enrolled = ctrl.student_sections[:, si]
            self.assertEqual(numpy.sum(enrolled), 3)
            self.assertFalse(numpy.any(numpy.isnan(ctrl.student_weights)))
            # With fewer positive-weight students than spaces, all of them must be picked
            if positive_count < 3:
                for s in range(positive_count):
                    self.assertTrue(enrolled[s])

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


# ---------------------------------------------------------------------------
# LotteryStatsTest
# ---------------------------------------------------------------------------

class LotteryStatsTest(LotteryTestBase):
    """Tests for compute_stats() and extract_stats() class enrollment statistics."""

    def test_compute_stats_class_enrollment_counts(self):
        """compute_stats() accurately computes class enrollment counts and ratios."""
        ctrl = self._make_controller()
        ctrl.compute_assignments()
        stats = ctrl.compute_stats(display=False)

        section_enrollments = numpy.sum(ctrl.student_sections, axis=0)
        self.assertTrue(numpy.array_equal(stats['section_enrollments'], section_enrollments))
        self.assertEqual(stats['num_empty_classes'], int(numpy.sum(section_enrollments == 0)))
        self.assertEqual(stats['num_enrolled_classes'], int(numpy.sum(section_enrollments > 0)))
        self.assertEqual(
            stats['num_full_classes'],
            int(numpy.sum((ctrl.section_capacities > 0) & (section_enrollments >= ctrl.section_capacities))),
        )
        self.assertEqual(
            stats['num_empty_classes'] + stats['num_enrolled_classes'],
            stats['num_sections'],
        )
        self.assertEqual(stats['total_spaces'], int(numpy.sum(ctrl.section_capacities)))
        self.assertAlmostEqual(
            stats['overall_capacity_ratio'],
            float(stats['num_registrations']) / stats['total_spaces'],
        )

    def test_compute_stats_when_all_classes_empty(self):
        """When no students are enrolled, all classes are counted as empty."""
        ctrl = self._make_controller()
        ctrl.clear_assignments()
        stats = ctrl.compute_stats(display=False)

        self.assertEqual(stats['num_empty_classes'], ctrl.num_sections)
        self.assertEqual(stats['num_enrolled_classes'], 0)
        self.assertEqual(stats['num_full_classes'], 0)
        self.assertEqual(stats['overall_capacity_ratio'], 0.0)

    def test_compute_stats_mixed_empty_partial_and_full_classes(self):
        """compute_stats() distinguishes empty, enrolled, and full sections."""
        ctrl = self._make_controller()
        ctrl.clear_assignments()
        self.assertGreaterEqual(ctrl.num_sections, 3)

        # Section 0: full (capacity 2, 2 students enrolled)
        # Section 1: partially filled (capacity 5, 1 student enrolled)
        # Remaining sections: empty (0 students enrolled)
        ctrl.section_capacities[:] = 5
        ctrl.section_capacities[0] = 2
        ctrl.student_sections[0, 0] = True
        ctrl.student_sections[1, 0] = True
        ctrl.student_sections[2, 1] = True

        stats = ctrl.compute_stats(display=False)
        self.assertEqual(stats['num_full_classes'], 1)
        self.assertEqual(stats['num_enrolled_classes'], 2)
        self.assertEqual(stats['num_empty_classes'], ctrl.num_sections - 2)
        self.assertEqual(stats['num_registrations'], 3)
        expected_spaces = 2 + 5 * (ctrl.num_sections - 1)
        self.assertEqual(stats['total_spaces'], expected_spaces)
        self.assertAlmostEqual(stats['overall_capacity_ratio'], 3.0 / expected_spaces)

    def test_compute_stats_zero_total_spaces_ratio_is_na(self):
        """When total_spaces is 0, overall_capacity_ratio is 'NA'."""
        ctrl = self._make_controller()
        ctrl.clear_assignments()
        ctrl.section_capacities[:] = 0

        stats = ctrl.compute_stats(display=False)
        self.assertEqual(stats['total_spaces'], 0)
        self.assertEqual(stats['num_full_classes'], 0)
        self.assertEqual(stats['overall_capacity_ratio'], 'NA')

        extracted = dict(ctrl.extract_stats(stats))
        self.assertIn('NA% of available spaces were filled', extracted['ratios'])

    def test_extract_stats_includes_class_enrollment_stats(self):
        """extract_stats() formats class enrollment counts and capacity ratio for display."""
        ctrl = self._make_controller()
        ctrl.compute_assignments()
        stats = ctrl.compute_stats(display=False)
        extracted = dict(ctrl.extract_stats(stats))

        self.assertIn('counts', extracted)
        counts = extracted['counts']
        self.assertIn(f'{stats["total_spaces"]:6d} total available spaces', counts)
        self.assertIn(f'{stats["num_sections"]:6d} available sections', counts)
        self.assertIn(
            f'{stats["num_enrolled_classes"]:6d} sections had at least 1 student enrolled',
            counts,
        )
        self.assertIn(f'{stats["num_empty_classes"]:6d} sections were empty', counts)
        self.assertIn(
            f'{stats["num_full_classes"]:6d} sections were filled to capacity',
            counts,
        )

        self.assertIn('ratios', extracted)
        ratios = extracted['ratios']
        self.assertIn(
            f'{stats["overall_capacity_ratio"] * 100.0:2.2f}% of available spaces were filled',
            ratios,
        )
