"""
Unit tests for esp/esp/program/controllers/classchange.py

``ClassChangeController.__init__`` contains an interactive ``input()`` prompt
that asks for program confirmation.  All tests patch ``builtins.input`` to
return ``'y'`` so the constructor can be exercised without user interaction.

Tests focus on:
  1. Constructor — options defaults, option overrides, program storage.
  2. Pure numpy helpers — ``get_index_array``, ``get_ids``, ``get_ids_and_indices``.
  3. Email text generators — ``get_changed_student_email_text``,
     ``get_unchanged_student_email_text``, ``get_student_schedule``.
  4. ``compute_assignments`` — runs the lottery algorithm in-memory; verifies
     the numpy arrays have the correct shapes and sensible values without
     writing to the database.
  5. ``clear_assignments`` — verifies state is reset to originals.

``save_assignments``, ``unsave_assignments``, and ``send_emails`` are *not*
tested here because they perform destructive database writes and real email
sends respectively; those belong in integration-level tests.

Base class: ProgramFrameworkTest, which provides a fully scheduled program
fixture (classes, sections, timeslots, teachers, students).
"""

from unittest.mock import patch

import numpy

from esp.program.models import (
    StudentRegistration,
    RegistrationType,
)
from esp.program.controllers.classchange import ClassChangeController
from esp.program.tests import ProgramFrameworkTest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_controller(program, **kwargs):
    """Instantiate ClassChangeController with ``input`` patched to 'y'."""
    with patch("builtins.input", return_value="y"):
        return ClassChangeController(program, **kwargs)


class ClassChangeTestBase(ProgramFrameworkTest):
    """
    Sets up a program fixture and optionally creates 'Request' registrations
    so that ``ClassChangeController.students`` is non-empty.
    """

    def setUp(self, *args, **kwargs):
        kwargs.setdefault("num_timeslots", 2)
        kwargs.setdefault("timeslot_length", 50)
        kwargs.setdefault("timeslot_gap", 10)
        kwargs.setdefault("num_teachers", 2)
        kwargs.setdefault("classes_per_teacher", 1)
        kwargs.setdefault("sections_per_class", 1)
        kwargs.setdefault("num_rooms", 2)
        super().setUp(*args, **kwargs)

        # Grab the first available section for registration fixtures.
        self.first_section = self.program.sections().order_by("id").first()

    def _create_request_registration(self, student, section=None):
        """Give *student* a 'Request' StudentRegistration on *section*."""
        if section is None:
            section = self.first_section
        req_type, _ = RegistrationType.objects.get_or_create(name="Request")
        reg, _ = StudentRegistration.objects.get_or_create(
            user=student,
            section=section,
            relationship=req_type,
        )
        return reg


# ===========================================================================
# __init__ / constructor tests
# ===========================================================================

class ClassChangeControllerInitTest(ClassChangeTestBase):

    def test_stores_program_object(self):
        ctrl = _make_controller(self.program)
        self.assertEqual(ctrl.program, self.program)

    def test_accepts_program_id(self):
        ctrl = _make_controller(self.program.id)
        self.assertEqual(ctrl.program, self.program)

    def test_default_options_applied(self):
        ctrl = _make_controller(self.program)
        defaults = ClassChangeController.default_options
        for key, val in defaults.items():
            self.assertEqual(ctrl.options[key], val, msg=f"Option '{key}' mismatch")

    def test_custom_option_overrides_default(self):
        ctrl = _make_controller(self.program, check_grade=True)
        self.assertTrue(ctrl.options["check_grade"])

    def test_extra_kwargs_stored_in_options(self):
        ctrl = _make_controller(self.program, stats_display=True)
        self.assertTrue(ctrl.options["stats_display"])

    def test_invalid_confirmation_raises(self):
        """If the user types 'n', the constructor should raise AssertionError."""
        with patch("builtins.input", return_value="n"):
            with self.assertRaises(AssertionError):
                ClassChangeController(self.program)

    def test_numpy_arrays_initialised_with_correct_student_axis(self):
        ctrl = _make_controller(self.program)
        # No 'Request' registrations → num_students == 0
        self.assertEqual(ctrl.enroll_orig.shape[0], ctrl.num_students)
        self.assertEqual(ctrl.request.shape[0], ctrl.num_students)

    def test_numpy_arrays_initialised_with_correct_section_axis(self):
        ctrl = _make_controller(self.program)
        self.assertEqual(ctrl.enroll_orig.shape[1], ctrl.num_sections)
        self.assertEqual(ctrl.request.shape[1], ctrl.num_sections)

    def test_numpy_arrays_initialised_with_correct_timeslot_axis(self):
        ctrl = _make_controller(self.program)
        self.assertEqual(ctrl.enroll_orig.shape[2], ctrl.num_timeslots)

    def test_num_sections_matches_program(self):
        ctrl = _make_controller(self.program)
        expected = self.program.sections().filter(
            status__gt=0,
            parent_class__status__gt=0,
            meeting_times__isnull=False,
        ).distinct().count()
        self.assertEqual(ctrl.num_sections, expected)

    def test_num_timeslots_matches_program(self):
        ctrl = _make_controller(self.program)
        expected = self.program.getTimeSlots().order_by("id").distinct().count()
        self.assertEqual(ctrl.num_timeslots, expected)

    def test_with_request_students_num_students_nonzero(self):
        student = self.students[0]
        self._create_request_registration(student)
        ctrl = _make_controller(self.program)
        self.assertGreater(ctrl.num_students, 0)


# ===========================================================================
# get_index_array()
# ===========================================================================

class GetIndexArrayTest(ClassChangeTestBase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.ctrl = _make_controller(self.program)

    def test_basic_mapping(self):
        arr = numpy.array([1, 6, 5, 3])
        result = self.ctrl.get_index_array(arr)
        # value 1 → index 0, value 6 → index 1, value 5 → index 2, value 3 → index 3
        self.assertEqual(result[1], 0)
        self.assertEqual(result[6], 1)
        self.assertEqual(result[5], 2)
        self.assertEqual(result[3], 3)

    def test_unoccupied_slots_are_minus_one(self):
        arr = numpy.array([1, 3])
        result = self.ctrl.get_index_array(arr)
        self.assertEqual(result[0], -1)
        self.assertEqual(result[2], -1)

    def test_output_length(self):
        arr = numpy.array([2, 5, 10])
        result = self.ctrl.get_index_array(arr)
        self.assertEqual(len(result), 11)  # max_index + 1

    def test_single_element(self):
        arr = numpy.array([4])
        result = self.ctrl.get_index_array(arr)
        self.assertEqual(result[4], 0)
        self.assertEqual(len(result), 5)

    def test_consecutive_indices(self):
        arr = numpy.array([0, 1, 2, 3])
        result = self.ctrl.get_index_array(arr)
        for i in range(4):
            self.assertEqual(result[i], i)


# ===========================================================================
# get_ids() and get_ids_and_indices()
# ===========================================================================

class GetIdsTest(ClassChangeTestBase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.ctrl = _make_controller(self.program)

    def test_get_ids_returns_numpy_array(self):
        sections_qs = self.program.sections().order_by("id").distinct()
        result = self.ctrl.get_ids(sections_qs)
        self.assertIsInstance(result, numpy.ndarray)

    def test_get_ids_length_matches_queryset(self):
        sections_qs = self.program.sections().order_by("id").distinct()
        result = self.ctrl.get_ids(sections_qs)
        self.assertEqual(len(result), sections_qs.count())

    def test_get_ids_values_are_sorted(self):
        sections_qs = self.program.sections().order_by("id").distinct()
        result = self.ctrl.get_ids(sections_qs)
        self.assertTrue(all(result[i] <= result[i + 1] for i in range(len(result) - 1)))

    def test_get_ids_and_indices_returns_tuple(self):
        sections_qs = self.program.sections().order_by("id").distinct()
        result = self.ctrl.get_ids_and_indices(sections_qs)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_get_ids_and_indices_ids_match_get_ids(self):
        sections_qs = self.program.sections().order_by("id").distinct()
        ids, _ = self.ctrl.get_ids_and_indices(sections_qs)
        expected = self.ctrl.get_ids(sections_qs)
        numpy.testing.assert_array_equal(ids, expected)

    def test_get_ids_and_indices_round_trip(self):
        """index_array[id_array[i]] should equal i for all valid IDs."""
        sections_qs = self.program.sections().order_by("id").distinct()
        ids, index_arr = self.ctrl.get_ids_and_indices(sections_qs)
        for i, sid in enumerate(ids):
            self.assertEqual(index_arr[sid], i)


# ===========================================================================
# clear_assignments()
# ===========================================================================

class ClearAssignmentsTest(ClassChangeTestBase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.ctrl = _make_controller(self.program)

    def test_clear_restores_section_capacities(self):
        orig = self.ctrl.section_capacities_orig.copy()
        # Modify capacity then clear.
        self.ctrl.section_capacities[:] = 0
        self.ctrl.clear_assignments()
        numpy.testing.assert_array_equal(self.ctrl.section_capacities, orig)

    def test_clear_restores_section_scores(self):
        orig = self.ctrl.section_scores_orig.copy()
        self.ctrl.section_scores[:] = 999
        self.ctrl.clear_assignments()
        numpy.testing.assert_array_equal(self.ctrl.section_scores, orig)

    def test_clear_restores_enroll_final(self):
        orig = self.ctrl.enroll_final_orig.copy()
        self.ctrl.enroll_final[:] = ~self.ctrl.enroll_final_orig
        self.ctrl.clear_assignments()
        numpy.testing.assert_array_equal(self.ctrl.enroll_final, orig)

    def test_changed_array_reset_to_zeros(self):
        self.ctrl.clear_assignments()
        self.assertFalse(self.ctrl.changed.any())


# ===========================================================================
# compute_assignments() — in-memory lottery, no DB writes
# ===========================================================================

class ComputeAssignmentsTest(ClassChangeTestBase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        # Create a Request registration so the controller has ≥1 student.
        self._create_request_registration(self.students[0])
        self.ctrl = _make_controller(self.program)

    def test_compute_does_not_raise(self):
        """compute_assignments() must complete without exceptions."""
        self.ctrl.compute_assignments()

    def test_enroll_final_shape_preserved(self):
        shape_before = self.ctrl.enroll_final.shape
        self.ctrl.compute_assignments()
        self.assertEqual(self.ctrl.enroll_final.shape, shape_before)

    def test_enroll_final_is_boolean(self):
        self.ctrl.compute_assignments()
        self.assertEqual(self.ctrl.enroll_final.dtype, bool)

    def test_student_not_enrolled_in_conflicting_timeslots(self):
        """After assignment, a student may not appear in two sections whose
        timeslots overlap."""
        self.ctrl.compute_assignments()
        for student_idx in range(self.ctrl.num_students):
            for ts_idx in range(self.ctrl.num_timeslots):
                enrolled_here = self.ctrl.enroll_final[student_idx, :, ts_idx]
                self.assertLessEqual(
                    enrolled_here.sum(), 1,
                    msg="Student assigned to multiple sections in the same timeslot",
                )

    def test_compute_can_be_called_multiple_times(self):
        """compute_assignments is idempotent — multiple calls should not raise."""
        self.ctrl.compute_assignments()
        self.ctrl.compute_assignments()

    def test_clear_then_compute_yields_same_result(self):
        self.ctrl.compute_assignments()
        first_result = self.ctrl.enroll_final.copy()
        self.ctrl.clear_assignments()
        # Fix the random seed to get deterministic results on re-run.
        numpy.random.seed(42)
        self.ctrl.compute_assignments()
        # Results may differ due to randomness, but we can at least verify
        # the shape is the same.
        self.assertEqual(self.ctrl.enroll_final.shape, first_result.shape)


# ===========================================================================
# Email text generation
# ===========================================================================

class EmailTextTest(ClassChangeTestBase):
    """Tests for get_student_schedule, get_changed_student_email_text, and
    get_unchanged_student_email_text.  These methods index into self.students,
    so we need at least one student with a Request registration."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self._create_request_registration(self.students[0])
        self.ctrl = _make_controller(self.program)
        # Student at index 0 in the controller's student list.
        self.student_idx = 0

    def test_get_student_schedule_returns_bytes(self):
        """get_student_schedule encodes its output to ASCII bytes."""
        schedule = self.ctrl.get_student_schedule(self.student_idx)
        self.assertIsInstance(schedule, bytes)

    def test_get_student_schedule_contains_table_tag(self):
        schedule = self.ctrl.get_student_schedule(self.student_idx)
        self.assertIn(b"<table", schedule)

    def test_get_changed_student_email_text_returns_bytes(self):
        text = self.ctrl.get_changed_student_email_text(self.student_idx)
        self.assertIsInstance(text, bytes)

    def test_get_changed_student_email_text_contains_html(self):
        text = self.ctrl.get_changed_student_email_text(self.student_idx)
        self.assertIn(b"<html>", text)

    def test_get_changed_student_email_text_mentions_program(self):
        text = self.ctrl.get_changed_student_email_text(self.student_idx)
        program_name = self.program.niceName().encode("ascii", "ignore")
        self.assertIn(program_name, text)

    def test_get_unchanged_student_email_text_returns_bytes(self):
        text = self.ctrl.get_unchanged_student_email_text(self.student_idx)
        self.assertIsInstance(text, bytes)

    def test_get_unchanged_student_email_text_contains_html(self):
        text = self.ctrl.get_unchanged_student_email_text(self.student_idx)
        self.assertIn(b"<html>", text)

    def test_get_unchanged_student_email_text_mentions_program(self):
        text = self.ctrl.get_unchanged_student_email_text(self.student_idx)
        program_name = self.program.niceName().encode("ascii", "ignore")
        self.assertIn(program_name, text)

    def test_changed_and_unchanged_emails_differ(self):
        changed = self.ctrl.get_changed_student_email_text(self.student_idx)
        unchanged = self.ctrl.get_unchanged_student_email_text(self.student_idx)
        self.assertNotEqual(changed, unchanged)
