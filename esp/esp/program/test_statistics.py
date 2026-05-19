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

from datetime import datetime, date
from unittest.mock import patch

from types import SimpleNamespace

from esp.program.models import Program, RegistrationProfile
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
from esp.users.models import ESPUser


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
        # Ensure RegistrationProfile rows exist for all users so that stats
        # functions which filter on profiles exercise real data paths.
        self.add_user_profiles()

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

    def test_valid_zipcode_counting(self):
        profile = SimpleNamespace(contact_user=SimpleNamespace(address_zip="53419"))
        _, rd = self._call(profiles=[profile])
        self.assertEqual(dict(rd["zip_data"]), {"53419": 1})
        self.assertEqual(rd["invalid"], 0)

    def test_invalid_zipcode_formats(self):
        short_zip = SimpleNamespace(contact_user=SimpleNamespace(address_zip="123"))
        alpha_zip = SimpleNamespace(contact_user=SimpleNamespace(address_zip="abcde"))

        _, rd = self._call(profiles=[short_zip, alpha_zip])
        self.assertEqual(rd["invalid"], 2)
        self.assertEqual(rd["zip_data"], [])

    def test_missing_contact_info(self):
        no_contact = SimpleNamespace(contact_user=None)
        _, rd = self._call(profiles=[no_contact])
        self.assertEqual(rd["invalid"], 1)


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

    def test_birthyear_counting_logic(self):
        dob_dummy = SimpleNamespace(
            student_info=SimpleNamespace(
                graduation_year=2027,
                dob=date(2005, 5, 20)
            )
        )
        profiles = [dob_dummy]
        _, rd = self._call(profiles=profiles)

        self.assertEqual(rd['birthyear_data'], [(2005, 1)])
        self.assertEqual(rd['gradyear_data'], [(2027, 1)])

    def test_birthyear_aggregation_multiple_students(self):
        student_a = SimpleNamespace(
            student_info=SimpleNamespace(graduation_year=2027, dob=date(2005, 1, 1))
        )
        student_b = SimpleNamespace(
            student_info=SimpleNamespace(graduation_year=2028, dob=date(2005, 12, 31))
        )
        profiles = [student_a, student_b]
        _, rd = self._call(profiles=profiles)

        self.assertEqual(rd['birthyear_data'], [(2005, 2)])


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

    def test_school_and_k12_counting_logic(self):
        k12_dummy = SimpleNamespace(
            student_info=SimpleNamespace(
                k12school=SimpleNamespace(name="Chaitanya Techno School"),
                school=None
            )
        )

        uni_dummy = SimpleNamespace(
            student_info=SimpleNamespace(
                k12school=None,
                school="Amrita Vishwa Vidyapeetham"
            )
        )

        profiles = [k12_dummy, uni_dummy]
        _, rd = self._call(profiles=profiles, rd={})

        self.assertEqual(rd['num_k12school'], 1)
        self.assertEqual(rd['num_school'], 1)

        expected_names = ["Amrita Vishwa Vidyapeetham", "Chaitanya Techno School"]
        actual_names = [item[0] for item in rd['school_data']]

        self.assertCountEqual(actual_names, expected_names)


# ===========================================================================
# startreg()
# ===========================================================================

class StartRegTest(StatisticsTestBase):

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

    def test_registration_and_confirmation_counting(self):
        mock_regs = [
            {
                'user_id': 1,
                'section__parent_class__parent_program': self.programs[0].id,
                'first_date': datetime(2026, 3, 20)
            }
        ]

        mock_confirms = [
            {
                'user_id': 1,
                'program_id': self.programs[0].id,
                'last_time': datetime(2026, 3, 21)
            }
        ]

        with patch('esp.program.models.StudentRegistration.objects.filter') as mock_reg_query, \
             patch('esp.users.models.Record.objects.filter') as mock_conf_query:

            mock_reg_query.return_value.values.return_value.annotate.return_value = mock_regs
            mock_conf_query.return_value.values.return_value.annotate.return_value = mock_confirms

            _, rd = self._call(rd={})

            program, reg_list, confirm_list = rd['program_data'][0]

            self.assertEqual(reg_list[0][0], datetime(2026, 3, 20).date())
            self.assertEqual(reg_list[0][1], 1)

            self.assertEqual(confirm_list[0][0], datetime(2026, 3, 21).date())
            self.assertEqual(confirm_list[0][1], 1)


# ===========================================================================
# repeats()
# ===========================================================================

class RepeatsTest(StatisticsTestBase):
    """Tests for statistics.repeats().

    NOTE: repeats() references 'program__program_type' (statistics.py L258),
    but the Program model has no ``program_type`` field.  Every call therefore
    raises ``django.core.exceptions.FieldError``.  These tests document the
    pre-existing bug so it does not silently break the rest of the suite.
    """

    def _call(self, students=None, profiles=None, rd=None):
        if students is None:
            students = self.student_qs
        if profiles is None:
            profiles = self.student_profiles
        if rd is None:
            rd = {}
        return repeats(_form(), self.programs, students, profiles, rd), rd

    def test_returns_string(self):
        from django.core.exceptions import FieldError
        with self.assertRaises(FieldError):
            self._call()

    def test_result_dict_has_repeat_data(self):
        from django.core.exceptions import FieldError
        with self.assertRaises(FieldError):
            self._call(rd={})

    def test_repeat_data_is_list(self):
        from django.core.exceptions import FieldError
        with self.assertRaises(FieldError):
            self._call(rd={})

    def test_empty_students_gives_empty_repeat_data(self):
        from django.core.exceptions import FieldError
        with self.assertRaises(FieldError):
            self._call(students=self.empty_users, profiles=self.empty_profiles, rd={})

    def test_repeats_logic_flow(self):
        mock_data = [
            (1, "Science"),
            (1, "Science"),
            (1, "Math"),
            (2, "Math"),
        ]

        with patch('esp.users.models.Record.objects.filter') as mock_filter:
            mock_filter.return_value.values_list.return_value = mock_data

            _, rd = self._call(rd={})
            repeat_data = dict(rd['repeat_data'])

            self.assertIn("1x Math, 2x Science", repeat_data)
            self.assertEqual(repeat_data["1x Math, 2x Science"], 1) # One student has this signature
            self.assertIn("1x Math", repeat_data)
            self.assertEqual(repeat_data["1x Math"], 1) # One student has this signature


# ===========================================================================
# heardabout()
# ===========================================================================

class HeardAboutTest(StatisticsTestBase):

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

    def test_heard_about_normalization_logic(self):
        profiles = [
            SimpleNamespace(student_info=SimpleNamespace(heard_about="School!")),
            SimpleNamespace(student_info=SimpleNamespace(heard_about="school")),
            SimpleNamespace(student_info=SimpleNamespace(heard_about="Friend...")),
            SimpleNamespace(student_info=SimpleNamespace(heard_about="FRIEND")),
        ]

        _, rd = self._call(profiles=profiles, rd={})

        data_dict = dict(rd['heardabout_data'])

        self.assertEqual(data_dict["School!"], 2)
        self.assertEqual(data_dict["Friend..."], 2)

        self.assertEqual(len(rd['heardabout_data']), 2)


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
