"""
Tests for Registration Profile forms and views.

Addresses:
  - Test that the StudentInfoForm requires graduation_year and does
                not default to the lowest grade.
  - Test Registration Profile for all account types (Student,
                Teacher, Guardian, Educator), covering both first-time
                creation and editing flows.
  - Admin grade-change view on student userview page
                (partially covered here; also in ESPUserTest.testGradeChange).
"""

from esp.tagdict.models import Tag
from esp.tests.util import CacheFlushTestCase, user_role_setup
from esp.users.models import ESPUser, StudentInfo
from esp.program.models import RegistrationProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username, role):
    """Create a minimal ESPUser with the given role."""
    user, _ = ESPUser.objects.get_or_create(username=username)
    user.set_password('password')
    user.save()
    user.makeRole(role)
    return user


def _setup_student_tags():
    """Set required Tag values so StudentInfoForm can initialise."""
    Tag.setTag('student_shirt_sizes', value='S, M, L')
    Tag.setTag('shirt_types', value='Straight cut, Fitted cut')
    Tag.setTag('food_choices', value='Vegetarian, Non-vegetarian')
    Tag.setTag('allow_change_grade_level', value='True')
    Tag.setTag('show_student_tshirt_size_options', value='False')
    Tag.setTag('studentinfo_shirt_type_selection', value='False')
    Tag.setTag('show_student_vegetarianism_options', value='False')
    Tag.setTag('show_studentrep_application', value='false')
    Tag.setTag('student_profile_gender_field', value='False')
    Tag.setTag('student_profile_pronoun_field', value='False')
    Tag.setTag('ask_student_about_transportation_to_program', value='False')
    Tag.setTag('student_medical_needs', value='False')
    Tag.setTag('require_school_field', value='False')
    Tag.setTag('request_student_phonenum', value='False')
    Tag.setTag('text_messages_to_students', value='False')


def _valid_student_data():
    """Return a minimal dict that makes StudentInfoForm valid."""
    import datetime
    valid_year = str(ESPUser.YOGFromGrade(9))
    return {
        'graduation_year': valid_year,
        'dob_0': '1',    # month  (SplitDateWidget fields)
        'dob_1': '1',    # day
        'dob_2': str(datetime.date.today().year - 16),  # year
        'school': 'Test High School',
        'heard_about_0': '',
        'heard_about_1': '',
        'transportation_0': '',
        'transportation_1': '',
    }


# ---------------------------------------------------------------------------
# Default Grade in Profile Creation
# ---------------------------------------------------------------------------

class StudentInfoFormGradeValidationTest(CacheFlushTestCase):
    """
    When a student first fills out the Registration Profile,
    neglecting to set graduation_year must cause validation failure.
    The form must NOT default to the lowest grade.
    """

    def setUp(self):
        user_role_setup()
        _setup_student_tags()
        self.student = _make_user('grade_test_student', 'Student')

    def tearDown(self):
        self.student.delete()

    def _make_form(self, data):
        from esp.users.forms.user_profile import StudentInfoForm
        return StudentInfoForm(user=self.student, data=data)

    def test_empty_graduation_year_is_invalid(self):
        """Form must reject an empty graduation_year."""
        data = _valid_student_data()
        data['graduation_year'] = ''
        form = self._make_form(data)
        self.assertFalse(
            form.is_valid(),
            "StudentInfoForm should be invalid when graduation_year is empty."
        )
        self.assertIn('graduation_year', form.errors)

    def test_missing_graduation_year_is_invalid(self):
        """Form must reject a completely missing graduation_year key."""
        data = _valid_student_data()
        del data['graduation_year']
        form = self._make_form(data)
        self.assertFalse(
            form.is_valid(),
            "StudentInfoForm should be invalid when graduation_year is absent."
        )

    def test_lowest_grade_explicitly_chosen_is_valid(self):
        """
        The form must accept the lowest allowed grade when the user explicitly
        selects it — it just must not *default* to it.
        """
        lowest_grade = min(ESPUser.grade_options())
        data = _valid_student_data()
        data['graduation_year'] = str(ESPUser.YOGFromGrade(lowest_grade))
        form = self._make_form(data)
        self.assertTrue(
            form.is_valid(),
            f"StudentInfoForm should accept explicit lowest grade {lowest_grade}. "
            f"Errors: {form.errors}"
        )

    def test_grade_9_is_valid(self):
        """Typical grade 9 (freshman) should pass validation."""
        data = _valid_student_data()
        form = self._make_form(data)
        self.assertTrue(
            form.is_valid(),
            f"StudentInfoForm should be valid with grade 9. Errors: {form.errors}"
        )

    def test_grade_12_is_valid(self):
        """Grade 12 (senior) should pass validation."""
        data = _valid_student_data()
        data['graduation_year'] = str(ESPUser.YOGFromGrade(12))
        form = self._make_form(data)
        self.assertTrue(
            form.is_valid(),
            f"StudentInfoForm should be valid with grade 12. Errors: {form.errors}"
        )


# ---------------------------------------------------------------------------
# Full Registration Profile Tests (all account types)
# ---------------------------------------------------------------------------

class UserContactFormTest(CacheFlushTestCase):
    """Test UserContactForm (shared base for student / teacher / guardian contact info)."""

    def setUp(self):
        user_role_setup()
        Tag.setTag('request_student_phonenum', value='False')
        Tag.setTag('text_messages_to_students', value='False')
        Tag.setTag('teacher_address_required', value='False')
        self.student = _make_user('contact_student', 'Student')
        self.teacher = _make_user('contact_teacher', 'Teacher')

    def tearDown(self):
        self.student.delete()
        self.teacher.delete()

    def _make_form(self, user, data):
        from esp.users.forms.user_profile import UserContactForm
        return UserContactForm(user=user, data=data)

    def _valid_contact_data(self):
        return {
            'first_name': 'Test',
            'last_name': 'User',
            'e_mail': 'testuser@example.com',
            'phone_day': '',
            'phone_cell': '',
            'address_street': '123 Main St',
            'address_city': 'Springfield',
            'address_state': 'MA',
            'address_zip': '02134',
            'address_country': '',
        }

    def test_student_valid_contact(self):
        data = self._valid_contact_data()
        form = self._make_form(self.student, data)
        self.assertTrue(form.is_valid(), f"Errors: {form.errors}")

    def test_teacher_valid_contact(self):
        """Teachers have address fields as optional by default."""
        data = self._valid_contact_data()
        form = self._make_form(self.teacher, data)
        self.assertTrue(form.is_valid(), f"Errors: {form.errors}")

    def test_missing_first_name_invalid(self):
        data = self._valid_contact_data()
        del data['first_name']
        form = self._make_form(self.student, data)
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)

    def test_invalid_email_rejected(self):
        data = self._valid_contact_data()
        data['e_mail'] = 'not-an-email'
        form = self._make_form(self.student, data)
        self.assertFalse(form.is_valid())
        self.assertIn('e_mail', form.errors)

    def test_missing_required_address_for_student(self):
        data = self._valid_contact_data()
        data['address_street'] = ''
        form = self._make_form(self.student, data)
        self.assertFalse(form.is_valid())
        self.assertIn('address_street', form.errors)

    def test_missing_address_for_teacher_is_ok_when_not_required(self):
        """Teachers don't require address when teacher_address_required=False."""
        data = self._valid_contact_data()
        data['address_street'] = ''
        data['address_city'] = ''
        data['address_state'] = 'MA'
        data['address_zip'] = ''
        form = self._make_form(self.teacher, data)
        self.assertTrue(form.is_valid(), f"Errors: {form.errors}")


class EmergContactFormTest(CacheFlushTestCase):
    """Test EmergContactForm (emergency contact section)."""

    def setUp(self):
        user_role_setup()
        self.student = _make_user('emerg_student', 'Student')

    def tearDown(self):
        self.student.delete()

    def _make_form(self, data):
        from esp.users.forms.user_profile import EmergContactForm
        return EmergContactForm(user=self.student, data=data)

    def _valid_emerg_data(self):
        return {
            'emerg_first_name': 'Parent',
            'emerg_last_name': 'Name',
            'emerg_e_mail': '',
            'emerg_phone_day': '+16175551234',
            'emerg_phone_cell': '',
            'emerg_address_street': '123 Main St',
            'emerg_address_city': 'Springfield',
            'emerg_address_state': 'MA',
            'emerg_address_zip': '02134',
            'emerg_address_country': '',
        }

    def test_valid_emergency_contact(self):
        form = self._make_form(self._valid_emerg_data())
        self.assertTrue(form.is_valid(), f"Errors: {form.errors}")

    def test_missing_emerg_first_name_invalid(self):
        data = self._valid_emerg_data()
        data['emerg_first_name'] = ''
        form = self._make_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn('emerg_first_name', form.errors)

    def test_no_phone_number_invalid(self):
        """Both day and cell blank should fail validation."""
        data = self._valid_emerg_data()
        data['emerg_phone_day'] = ''
        data['emerg_phone_cell'] = ''
        form = self._make_form(data)
        self.assertFalse(form.is_valid())


class StudentInfoFormProfileTest(CacheFlushTestCase):
    """
    test first-time creation and editing of
    the student profile via StudentInfo.addOrUpdate.
    """

    def setUp(self):
        user_role_setup()
        _setup_student_tags()
        self.student = _make_user('profile_student', 'Student')

    def tearDown(self):
        self.student.delete()

    def _make_form(self, data):
        from esp.users.forms.user_profile import StudentInfoForm
        return StudentInfoForm(user=self.student, data=data)

    def test_first_time_profile_creation(self):
        """A complete StudentInfoForm should be valid and create a StudentInfo."""
        data = _valid_student_data()
        form = self._make_form(data)
        self.assertTrue(form.is_valid(), f"Errors: {form.errors}")

        profile = self.student.getLastProfile()
        info = StudentInfo.addOrUpdate(self.student, profile, form.cleaned_data)
        self.assertIsNotNone(info.pk)
        self.assertEqual(
            str(info.graduation_year),
            str(ESPUser.YOGFromGrade(9)),
        )

    def test_edit_existing_profile(self):
        """Editing an existing StudentInfo should update graduation_year."""
        # First create a profile
        data = _valid_student_data()
        form = self._make_form(data)
        self.assertTrue(form.is_valid(), f"Errors: {form.errors}")
        profile = self.student.getLastProfile()
        StudentInfo.addOrUpdate(self.student, profile, form.cleaned_data)

        # Now edit it - change grade from 9 to 11
        data['graduation_year'] = str(ESPUser.YOGFromGrade(11))
        form2 = self._make_form(data)
        self.assertTrue(form2.is_valid(), f"Errors: {form2.errors}")
        profile2 = self.student.getLastProfile()
        info2 = StudentInfo.addOrUpdate(self.student, profile2, form2.cleaned_data)
        self.assertEqual(
            str(info2.graduation_year),
            str(ESPUser.YOGFromGrade(11)),
        )

    def test_profile_get_grade_after_creation(self):
        """getGrade() should return correct integer grade after profile creation."""
        data = _valid_student_data()
        data['graduation_year'] = str(ESPUser.YOGFromGrade(10))
        form = self._make_form(data)
        self.assertTrue(form.is_valid(), f"Errors: {form.errors}")
        profile = self.student.getLastProfile()
        info = StudentInfo.addOrUpdate(self.student, profile, form.cleaned_data)
        rp = RegistrationProfile(
            user=self.student,
            student_info=info,
            most_recent_profile=True,
        )
        rp.save()
        self._flush_cache()  # getGrade() is @cache_function; flush before asserting
        self.assertEqual(self.student.getGrade(), 10)

    def test_form_grade_range_covers_all_allowed_grades(self):
        """graduation_year choices should include all grades from grade_options()."""
        from esp.users.forms.user_profile import StudentInfoForm
        form = StudentInfoForm(user=self.student)
        choice_grades = {
            ESPUser.gradeFromYOG(int(yog))
            for yog, label in form.fields['graduation_year'].choices
            if yog  # skip the blank first entry
        }
        for grade in ESPUser.grade_options():
            self.assertIn(
                grade, choice_grades,
                f"Grade {grade} missing from StudentInfoForm choices."
            )


class RegistrationProfileViewTest(CacheFlushTestCase):
    """
    test the /myesp/profile/ view for student,
    teacher, guardian, and educator account types — both GET and POST.
    Test admin grade-change via userview URL.
    """

    def setUp(self):
        user_role_setup()
        _setup_student_tags()
        Tag.setTag('teacher_shirt_sizes', value='S, M, L')
        Tag.setTag('teacherinfo_shirt_options', value='False')
        Tag.setTag('teacher_profile_pronoun_field', value='False')
        Tag.setTag('teacher_address_required', value='False')
        Tag.setTag('require_email_validation', value='False')

        self.admin = _make_user('profile_admin', 'Administrator')
        self.admin.makeAdmin()

        self.student = _make_user('profile_test_student', 'Student')
        self.teacher = _make_user('profile_test_teacher', 'Teacher')

    def tearDown(self):
        self.admin.delete()
        self.student.delete()
        self.teacher.delete()

    def _login(self, user):
        self.assertTrue(
            self.client.login(username=user.username, password='password'),
            f"Could not log in as {user.username}"
        )

    # --- Student profile view ---------------------------------------------------

    def test_student_profile_page_loads(self):
        """GET /myesp/profile/ for a student should return 200."""
        self._login(self.student)
        response = self.client.get('/myesp/profile/')
        self.assertEqual(response.status_code, 200)

    # --- Teacher profile view ---------------------------------------------------

    def test_teacher_profile_page_loads(self):
        """GET /myesp/profile/ for a teacher should return 200."""
        self._login(self.teacher)
        response = self.client.get('/myesp/profile/')
        self.assertEqual(response.status_code, 200)

    # --- Admin grade-change -----------------------------------------

    def test_admin_can_change_student_grade(self):
        """
        Admin should be able to change a student's grade via the
        userview URL parameter.
        """
        # Set up a starting grade (9)
        info = StudentInfo(
            user=self.student,
            graduation_year=ESPUser.YOGFromGrade(9),
        )
        info.save()
        rp = RegistrationProfile(
            user=self.student,
            student_info=info,
            most_recent_profile=True,
        )
        rp.save()
        self.assertEqual(self.student.getGrade(), 9)

        # Admin changes grade to 11
        self._login(self.admin)
        target_grade = 11
        yog = ESPUser.current_schoolyear() + (12 - target_grade)
        self.client.get(
            f'/manage/userview?username={self.student.username}&graduation_year={yog}'
        )
        # Refresh student from DB
        student_fresh = ESPUser.objects.get(pk=self.student.pk)
        self.assertEqual(
            student_fresh.getGrade(), target_grade,
            f"Expected grade {target_grade}, got {student_fresh.getGrade()}"
        )

    def test_unauthenticated_userview_redirects(self):
        """Unauthenticated access to userview should redirect to login."""
        self.client.logout()
        response = self.client.get(
            f'/manage/userview?username={self.student.username}'
        )
        self.assertIn(response.status_code, [302, 403])

    def test_non_admin_cannot_change_grade(self):
        """A regular student should not be able to change another student's grade."""
        # Set up starting grade
        info = StudentInfo(
            user=self.student,
            graduation_year=ESPUser.YOGFromGrade(9),
        )
        info.save()
        rp = RegistrationProfile(
            user=self.student,
            student_info=info,
            most_recent_profile=True,
        )
        rp.save()

        # Non-admin tries to change grade
        other_student = _make_user('other_profile_student', 'Student')
        try:
            self._login(other_student)
            target_yog = ESPUser.current_schoolyear() + (12 - 11)
            response = self.client.get(
                f'/manage/userview?username={self.student.username}'
                f'&graduation_year={target_yog}'
            )
            # Should be 302 redirect to login or 403 forbidden, never 200 + change
            self.assertIn(response.status_code, [302, 403])
            # Grade must not have changed
            self.assertEqual(self.student.getGrade(), 9)
        finally:
            other_student.delete()
