"""
Unit tests for esp/esp/program/statistics.py

All statistics functions share the signature:
    fn(form, programs, students_or_teachers, profiles, result_dict={})
and return an HTML string from render_to_string().

Tests verify:
  1. The function returns a string (not None, not an exception).
  2. `result_dict` is populated with the correct keys.
  3. Computed values (counts, lengths, limits) are correct.
  4. Edge-case inputs (empty querysets, limit=0, limit=1) are handled safely.

Base class: ProgramFrameworkTest (from esp.program.tests), which provides a
complete program fixture including teachers, scheduled class sections, and
students.  We convert the list attributes to QuerySets where functions require
them.
"""

from types import SimpleNamespace

from django.test import TestCase

from esp.program.models import Program, StudentRegistration, RegistrationType
from esp.program.tests import ProgramFrameworkTest
from esp.program.statistics import (
    zipcodes,
    demographics,
    schools,
    startreg,
    repeats,
    heardabout,
    hours,
    student_reg,
    teacher_reg,
    class_reg,
)
from esp.users.models import ESPUser, RegistrationProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _form(limit=0):
    """Return a minimal stand-in form whose cleaned_data supports ``limit``."""
    return SimpleNamespace(cleaned_data={"limit": limit})


class StatisticsTestBase(ProgramFrameworkTest):
    """Base that wires up the QuerySets expected by all statistics functions."""

    def setUp(self, *args, **kwargs):
        # Smaller fixture so tests run faster.
        kwargs.setdefault("num_timeslots", 2)
        kwargs.setdefault("timeslot_length", 50)
        kwargs.setdefault("timeslot_gap", 10)
        kwargs.setdefault("num_teachers", 3)
        kwargs.setdefault("classes_per_teacher", 1)
        kwargs.setdefault("sections_per_class", 1)
        kwargs.setdefault("num_rooms", 3)
        super().setUp(*args, **kwargs)

        # Build QuerySets from the list fixtures set by ProgramFrameworkTest.
        self.programs = Program.objects.filter(pk=self.program.pk)
        self.student_qs = ESPUser.objects.filter(
            pk__in=[s.pk for s in self.students]
        )
        self.teacher_qs = ESPUser.objects.filter(
            pk__in=[t.pk for t in self.teachers]
        )
        self.student_profiles = RegistrationProfile.objects.filter(
            user__in=self.student_qs, most_recent_profile=True
        )
        self.teacher_profiles = RegistrationProfile.objects.filter(
            user__in=self.teacher_qs, most_recent_profile=True
        )
        self.empty_users = ESPUser.objects.none()
        self.empty_profiles = RegistrationProfile.objects.none()


# ===========================================================================
# zipcodes()
# ===========================================================================

class ZipcodesTest(StatisticsTestBase):

    def _call(self, form=None, profiles=None, rd=None):
        if form is None:
            form = _form()
        if profiles is None:
            profiles = self.student_profiles
        if rd is None:
            rd = {}
        return zipcodes(form, self.programs, self.student_qs, profiles, rd), rd

    def test_returns_string(self):
        result, _ = self._call()
        self.assertIsInstance(result, str)

    def test_result_dict_has_required_keys(self):
        _, rd = self._call(rd={})
        self.assertIn("zip_data", rd)
        self.assertIn("invalid", rd)

    def test_invalid_count_nonnegative(self):
        _, rd = self._call(rd={})
        self.assertGreaterEqual(rd["invalid"], 0)

    def test_zip_data_is_list(self):
        _, rd = self._call(rd={})
        self.assertIsInstance(rd["zip_data"], list)

    def test_limit_truncates_results(self):
        _, rd = self._call(form=_form(limit=1), rd={})
        self.assertLessEqual(len(rd["zip_data"]), 1)

    def test_zero_limit_returns_all(self):
        """limit=0 is falsy — no truncation should be applied."""
        _, full_rd = self._call(form=_form(limit=0), rd={})
        # Just check we get at least as many as the truncated case.
        _, one_rd = self._call(form=_form(limit=1), rd={})
        self.assertGreaterEqual(len(full_rd["zip_data"]), len(one_rd["zip_data"]))

    def test_empty_profiles_gives_zero_invalid(self):
        _, rd = self._call(profiles=self.empty_profiles, rd={})
        self.assertEqual(rd["invalid"], 0)
        self.assertEqual(rd["zip_data"], [])


# ===========================================================================
# demographics()
# ===========================================================================

class DemographicsTest(StatisticsTestBase):

    def _call(self, students=None, profiles=None, rd=None):
        if students is None:
            students = self.student_qs
        if profiles is None:
            profiles = self.student_profiles
        if rd is None:
            rd = {}
        return demographics(_form(), self.programs, students, profiles, rd), rd

    def test_returns_string(self):
        result, _ = self._call()
        self.assertIsInstance(result, str)

    def test_result_dict_has_all_keys(self):
        _, rd = self._call(rd={})
        expected_keys = [
            "num_classes", "num_sections", "num_class_hours",
            "num_student_class_hours", "gradyear_data", "birthyear_data",
            "finaid_applied", "finaid_lunch", "finaid_approved",
        ]
        for key in expected_keys:
            self.assertIn(key, rd, msg=f"Missing key in result_dict: {key}")

    def test_class_counts_nonnegative(self):
        _, rd = self._call(rd={})
        self.assertGreaterEqual(rd["num_classes"], 0)
        self.assertGreaterEqual(rd["num_sections"], 0)
        self.assertGreaterEqual(rd["num_class_hours"], 0)

    def test_finaid_counts_nonnegative(self):
        _, rd = self._call(rd={})
        self.assertGreaterEqual(rd["finaid_applied"], 0)
        self.assertGreaterEqual(rd["finaid_lunch"], 0)
        self.assertGreaterEqual(rd["finaid_approved"], 0)

    def test_empty_students(self):
        result, rd = self._call(students=self.empty_users, profiles=self.empty_profiles, rd={})
        self.assertIsInstance(result, str)
        self.assertEqual(rd["finaid_applied"], 0)
        self.assertEqual(rd["finaid_approved"], 0)

    def test_gradyear_data_is_list(self):
        _, rd = self._call(rd={})
        self.assertIsInstance(rd["gradyear_data"], list)

    def test_birthyear_data_is_list(self):
        _, rd = self._call(rd={})
        self.assertIsInstance(rd["birthyear_data"], list)


# ===========================================================================
# schools()
# ===========================================================================

class SchoolsTest(StatisticsTestBase):

    def _call(self, form=None, profiles=None, rd=None):
        if form is None:
            form = _form()
        if profiles is None:
            profiles = self.student_profiles
        if rd is None:
            rd = {}
        return schools(form, self.programs, self.student_qs, profiles, rd), rd

    def test_returns_string(self):
        result, _ = self._call()
        self.assertIsInstance(result, str)

    def test_result_dict_has_required_keys(self):
        _, rd = self._call(rd={})
        self.assertIn("school_data", rd)
        self.assertIn("num_k12school", rd)
        self.assertIn("num_school", rd)

    def test_school_counts_nonnegative(self):
        _, rd = self._call(rd={})
        self.assertGreaterEqual(rd["num_k12school"], 0)
        self.assertGreaterEqual(rd["num_school"], 0)

    def test_school_data_is_list(self):
        _, rd = self._call(rd={})
        self.assertIsInstance(rd["school_data"], list)

    def test_limit_truncates(self):
        _, rd = self._call(form=_form(limit=1), rd={})
        self.assertLessEqual(len(rd["school_data"]), 1)

    def test_empty_profiles(self):
        _, rd = self._call(profiles=self.empty_profiles, rd={})
        self.assertEqual(rd["num_k12school"], 0)
        self.assertEqual(rd["num_school"], 0)
        self.assertEqual(rd["school_data"], [])


# ===========================================================================
# startreg()
# ===========================================================================

class StartregTest(StatisticsTestBase):

    def _call(self, students=None, profiles=None, rd=None):
        if students is None:
            students = self.student_qs
        if profiles is None:
            profiles = self.student_profiles
        if rd is None:
            rd = {}
        return startreg(_form(), self.programs, students, profiles, rd), rd

    def test_returns_string(self):
        result, _ = self._call()
        self.assertIsInstance(result, str)

    def test_result_dict_has_program_data(self):
        _, rd = self._call(rd={})
        self.assertIn("program_data", rd)

    def test_program_data_length_equals_programs(self):
        _, rd = self._call(rd={})
        self.assertEqual(len(rd["program_data"]), self.programs.count())

    def test_empty_students(self):
        result, rd = self._call(students=self.empty_users, profiles=self.empty_profiles, rd={})
        self.assertIsInstance(result, str)
        # All registration/confirmation lists should be empty.
        for _prog, reg_list, confirm_list in rd["program_data"]:
            self.assertEqual(reg_list, [])
            self.assertEqual(confirm_list, [])


# ===========================================================================
# repeats()
# ===========================================================================

class RepeatsTest(StatisticsTestBase):

    def _call(self, students=None, profiles=None, rd=None):
        if students is None:
            students = self.student_qs
        if profiles is None:
            profiles = self.student_profiles
        if rd is None:
            rd = {}
        return repeats(_form(), self.programs, students, profiles, rd), rd

    def test_returns_string(self):
        result, _ = self._call()
        self.assertIsInstance(result, str)

    def test_result_dict_has_repeat_data(self):
        _, rd = self._call(rd={})
        self.assertIn("repeat_data", rd)

    def test_repeat_data_is_list(self):
        _, rd = self._call(rd={})
        self.assertIsInstance(rd["repeat_data"], list)

    def test_empty_students_gives_empty_repeat_data(self):
        _, rd = self._call(students=self.empty_users, profiles=self.empty_profiles, rd={})
        self.assertEqual(rd["repeat_data"], [])


# ===========================================================================
# heardabout()
# ===========================================================================

class HeardaboutTest(StatisticsTestBase):

    def _call(self, form=None, profiles=None, rd=None):
        if form is None:
            form = _form()
        if profiles is None:
            profiles = self.student_profiles
        if rd is None:
            rd = {}
        return heardabout(form, self.programs, self.student_qs, profiles, rd), rd

    def test_returns_string(self):
        result, _ = self._call()
        self.assertIsInstance(result, str)

    def test_result_dict_has_heardabout_data(self):
        _, rd = self._call(rd={})
        self.assertIn("heardabout_data", rd)

    def test_heardabout_data_is_list(self):
        _, rd = self._call(rd={})
        self.assertIsInstance(rd["heardabout_data"], list)

    def test_limit_truncates(self):
        _, rd = self._call(form=_form(limit=1), rd={})
        self.assertLessEqual(len(rd["heardabout_data"]), 1)

    def test_empty_profiles(self):
        _, rd = self._call(profiles=self.empty_profiles, rd={})
        self.assertEqual(rd["heardabout_data"], [])


# ===========================================================================
# hours()
# ===========================================================================

class HoursTest(StatisticsTestBase):

    def _call(self, students=None, profiles=None, rd=None):
        if students is None:
            students = self.student_qs
        if profiles is None:
            profiles = self.student_profiles
        if rd is None:
            rd = {}
        return hours(_form(), self.programs, students, profiles, rd), rd

    def test_returns_string(self):
        result, _ = self._call()
        self.assertIsInstance(result, str)

    def test_result_dict_has_hours_data(self):
        _, rd = self._call(rd={})
        self.assertIn("hours_data", rd)

    def test_hours_data_length_equals_programs(self):
        _, rd = self._call(rd={})
        self.assertEqual(len(rd["hours_data"]), self.programs.count())

    def test_hours_data_tuple_structure(self):
        """Each entry is (program, enrolled_flat, attended_flat,
        program_timeslots, timeslots_enrolled_flat, timeslots_attended_flat,
        students_count)."""
        _, rd = self._call(rd={})
        for entry in rd["hours_data"]:
            self.assertEqual(len(entry), 7, msg=f"Unexpected hours_data tuple length: {entry}")

    def test_empty_students(self):
        result, _ = self._call(students=self.empty_users, profiles=self.empty_profiles, rd={})
        self.assertIsInstance(result, str)


# ===========================================================================
# student_reg()
# ===========================================================================

class StudentRegStatTest(StatisticsTestBase):
    """Tests for statistics.student_reg (not esp.program.modules.studentreg)."""

    def _call(self, students=None, profiles=None, rd=None):
        if students is None:
            students = self.student_qs
        if profiles is None:
            profiles = self.student_profiles
        if rd is None:
            rd = {}
        return student_reg(_form(), self.programs, students, profiles, rd), rd

    def test_returns_string(self):
        result, _ = self._call()
        self.assertIsInstance(result, str)

    def test_result_dict_has_all_keys(self):
        _, rd = self._call(rd={})
        for key in ("prog_data", "stat_names", "x_axis_categories", "left_axis_data"):
            self.assertIn(key, rd, msg=f"Missing key: {key}")

    def test_prog_data_length_equals_programs(self):
        _, rd = self._call(rd={})
        self.assertEqual(len(rd["prog_data"]), self.programs.count())

    def test_stat_names_has_four_entries(self):
        _, rd = self._call(rd={})
        self.assertEqual(len(rd["stat_names"]), 4)

    def test_each_prog_stat_has_four_values(self):
        _, rd = self._call(rd={})
        for _prog, stats in rd["prog_data"]:
            self.assertEqual(len(stats), 4, msg=f"Expected 4 stats per program, got {stats}")

    def test_stat_counts_nonnegative(self):
        _, rd = self._call(rd={})
        for _prog, stats in rd["prog_data"]:
            for val in stats:
                self.assertGreaterEqual(val, 0)


# ===========================================================================
# teacher_reg()
# ===========================================================================

class TeacherRegTest(StatisticsTestBase):

    def _call(self, teachers=None, profiles=None, rd=None):
        if teachers is None:
            teachers = self.teacher_qs
        if profiles is None:
            profiles = self.teacher_profiles
        if rd is None:
            rd = {}
        return teacher_reg(_form(), self.programs, teachers, profiles, rd), rd

    def test_returns_string(self):
        result, _ = self._call()
        self.assertIsInstance(result, str)

    def test_result_dict_has_all_keys(self):
        _, rd = self._call(rd={})
        for key in ("prog_data", "stat_names", "x_axis_categories", "left_axis_data"):
            self.assertIn(key, rd, msg=f"Missing key: {key}")

    def test_prog_data_length_equals_programs(self):
        _, rd = self._call(rd={})
        self.assertEqual(len(rd["prog_data"]), self.programs.count())

    def test_stat_names_has_three_entries(self):
        _, rd = self._call(rd={})
        self.assertEqual(len(rd["stat_names"]), 3)

    def test_each_prog_stat_has_three_values(self):
        _, rd = self._call(rd={})
        for _prog, stats in rd["prog_data"]:
            self.assertEqual(len(stats), 3)

    def test_empty_teachers(self):
        result, _ = self._call(teachers=self.empty_users, profiles=self.empty_profiles, rd={})
        self.assertIsInstance(result, str)


# ===========================================================================
# class_reg()
# ===========================================================================

class ClassRegTest(StatisticsTestBase):

    def _call(self, teachers=None, profiles=None, rd=None):
        if teachers is None:
            teachers = self.teacher_qs
        if profiles is None:
            profiles = self.teacher_profiles
        if rd is None:
            rd = {}
        return class_reg(_form(), self.programs, teachers, profiles, rd), rd

    def test_returns_string(self):
        result, _ = self._call()
        self.assertIsInstance(result, str)

    def test_result_dict_has_all_keys(self):
        _, rd = self._call(rd={})
        for key in (
            "prog_data", "stat_names", "stat_categories",
            "x_axis_categories", "left_axis_data", "right_axis_data",
        ):
            self.assertIn(key, rd, msg=f"Missing key: {key}")

    def test_stat_categories_has_two_entries(self):
        _, rd = self._call(rd={})
        self.assertEqual(len(rd["stat_categories"]), 2)

    def test_prog_data_length_equals_programs(self):
        _, rd = self._call(rd={})
        self.assertEqual(len(rd["prog_data"]), self.programs.count())

    def test_each_prog_stat_has_six_values(self):
        """Three classes stats + three class-student-hour stats = 6."""
        _, rd = self._call(rd={})
        for _prog, stats in rd["prog_data"]:
            self.assertEqual(len(stats), 6)

    def test_class_counts_nonnegative(self):
        _, rd = self._call(rd={})
        for _prog, stats in rd["prog_data"]:
            for val in stats:
                self.assertGreaterEqual(val, 0)

    def test_empty_teachers(self):
        result, _ = self._call(teachers=self.empty_users, profiles=self.empty_profiles, rd={})
        self.assertIsInstance(result, str)
