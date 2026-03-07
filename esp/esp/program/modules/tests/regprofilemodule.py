__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2010 by the individual contributors
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

from datetime import datetime, timedelta
from esp.program.tests import ProgramFrameworkTest
from esp.middleware.threadlocalrequest import get_current_request

class RegProfileModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        from esp.program.models import Program
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        # Set up the program -- we want to be sure of these parameters
        kwargs.update({'num_students': 3,})
        super().setUp(*args, **kwargs)

        # Get and remember the instance of this module
        m = ProgramModule.objects.get(handler='RegProfileModule', module_type='learn')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, m)

    def runTest(self):
        from esp.program.models import RegistrationProfile

        #   Check that the profile page does not cause an error when not logged in
        #   (it should redirect to a login page)
        response = self.client.get('/learn/%s/profile' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 302)

        # Check that the people start out without profiles
        # We'll probably need to be a little more careful about how we set
        # the ProgramModuleObj's user if we ever cache isCompleted().
        for student in self.students:
            get_current_request().user = student
            self.assertTrue( not self.moduleobj.isCompleted(), "The profile should be incomplete at first." )

        # First student: Test non-saving of initial program profile
        get_current_request().user = self.students[0]
        prof = RegistrationProfile.getLastForProgram(self.students[0], self.program)
        self.assertTrue( self.students[0].registrationprofile_set.count() <= 0, "Profile was saved when it shouldn't have been." )
        # Test migration of initial non-program profile to a program
        prof = self.students[0].getLastProfile()
        prof.program = None
        prof.save()
        self.assertTrue( self.students[0].registrationprofile_set.count() >= 1, "Profile failed to save." )
        self.assertTrue( self.students[0].registrationprofile_set.count() <= 1, "Too many profiles." )
        self.assertTrue( self.moduleobj.isCompleted(), "Profile id wiped." )
        self.assertTrue( self.students[0].registrationprofile_set.all()[0].program == self.program, "Profile failed to migrate to program." )
        self.assertTrue( self.students[0].registrationprofile_set.count() <= 1, "Too many profiles." )

        # Second student: Test non-auto-saving of sufficiently old profiles
        get_current_request().user = self.students[1]
        prof = self.students[1].getLastProfile()
        prof.program = None
        # HACK -- save properly to dump the appropriate cache.
        # Then save sneakily so that we can override the timestamp.
        prof.save()
        prof.last_ts = datetime.now() - timedelta(10)
        super(RegistrationProfile, prof).save()
        # Continue testing
        self.assertTrue( self.students[1].registrationprofile_set.count() >= 1, "Profile failed to save." )
        self.assertTrue( self.students[1].registrationprofile_set.count() <= 1, "Too many profiles." )
        self.assertTrue( not self.moduleobj.isCompleted(), "Profile too old but accepted anyway." )
        self.assertTrue( self.students[1].registrationprofile_set.count() <= 1, "Too many profiles." )

        get_current_request().user = self.students[2]
        for r in RegistrationProfile.objects.filter(user=self.students[2]):
            r.delete()
        # Test to see whether the graduation year is required
        self.client.login(username=self.students[2].username, password='password')
        response = self.client.post('%sprofile' % self.program.get_learn_url(), {'graduation_year': '', 'profile_page': ''})
        lines = response.content.decode('UTF-8').split('\n')

        ## Find the line for the start of the graduation-year form field
        for i, line in enumerate(lines):
            if 'id="id_graduation_year"' in line:
                break
        self.assertTrue(i < len(lines)-1) ## Found the relevant line

        ## Find the line for the end of the graduation-year form field
        for j, line in enumerate(lines[i:]):
            if '</select>' in line:
                break
        self.assertTrue(j < len(lines) - 2) ## Found the line, need to also find the error message on the next line

        ## Find the error message
        self.assertTrue('<span class="form_error">This field is required.</span>' in lines[i+j+1])

        ## Validate that the default value of the form is the empty string, like we assumed in POST'ing it above
        found_default = False
        for line in lines[i:i+j]:
            found_default = found_default or ('<option value="" selected></option>' in line)
        self.assertTrue(found_default)


class RegistrationProfileFlowTest(ProgramFrameworkTest):
    """
    Comprehensive tests for the RegistrationProfile workflow (issue #225).

    Covers:
      - First-time profile creation for students and teachers
      - Editing / updating an existing profile
      - Invalid POST data (missing required fields)
      - Default grade behaviour from PR #193 (empty option must be pre-selected,
        not the smallest grade)
      - Grade remains null / produces an error when omitted from POST
    """

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 3, 'num_teachers': 2})
        super().setUp(*args, **kwargs)
        self.student_profile_url = '%sprofile' % self.program.get_learn_url()
        self.teacher_profile_url = '%sprofile' % self.program.get_teach_url()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _valid_student_post(self, grade=9):
        """Return a minimal valid POST dict for StudentProfileForm."""
        from esp.users.models import ESPUser
        yog = str(ESPUser.YOGFromGrade(grade))
        return {
            'profile_page':       '',
            # UserContactForm
            'first_name':         'Test',
            'last_name':          'Student',
            'e_mail':             'teststudent@example.com',
            # phone_cell satisfies the require_student_phonenum check when enabled
            'phone_cell':         '+16175559999',
            'address_street':     '123 Test St',
            'address_city':       'Cambridge',
            'address_state':      'MA',
            'address_zip':        '02139',
            # StudentInfoForm
            'graduation_year':    yog,
            'dob_0':              '5',     # month (SplitDateWidget: 0=month)
            'dob_1':              '15',    # day
            'dob_2':              '2010',  # year
            # EmergContactForm
            'emerg_first_name':   'Emerg',
            'emerg_last_name':    'Contact',
            'emerg_phone_day':    '+16175551234',
            'emerg_address_street': '123 Test St',
            'emerg_address_city': 'Cambridge',
            'emerg_address_state': 'MA',
            'emerg_address_zip':  '02139',
            # GuardContactForm
            'guard_first_name':   'Guard',
            'guard_last_name':    'Ian',
            'guard_phone_day':    '+16175555678',
        }

    def _valid_teacher_post(self):
        """Return a minimal valid POST dict for TeacherProfileForm."""
        return {
            'profile_page':   '',
            # UserContactForm (address fields are optional for teachers)
            'first_name':     'Test',
            'last_name':      'Teacher',
            'e_mail':         'testteacher@example.com',
            # Teachers always require at least one phone (isTeacher() branch in clean())
            'phone_cell':     '+16175558888',
            # TeacherInfoForm – affiliation is a DropdownOtherField (MultiWidget)
            'affiliation_0':  'Undergrad',
            'affiliation_1':  '',
        }

    # ------------------------------------------------------------------
    # 1. Unauthenticated access
    # ------------------------------------------------------------------

    def test_unauthenticated_redirect(self):
        """GET /learn/<prog>/profile without login must redirect (302)."""
        self.client.logout()
        response = self.client.get(self.student_profile_url)
        self.assertEqual(response.status_code, 302)

    # ------------------------------------------------------------------
    # 2. GET profile page – student
    # ------------------------------------------------------------------

    def test_get_profile_page_student(self):
        """A logged-in student can load the profile page and sees the grade field."""
        self.client.login(username=self.students[0].username, password='password')
        response = self.client.get(self.student_profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_graduation_year"')

    # ------------------------------------------------------------------
    # 3. First-time student profile creation
    # ------------------------------------------------------------------

    def test_first_time_student_profile_creation(self):
        """POSTing valid student data creates a RegistrationProfile with correct grade."""
        from esp.program.models import RegistrationProfile
        from esp.users.models import ESPUser

        student = self.students[0]
        RegistrationProfile.objects.filter(user=student).delete()

        self.client.login(username=student.username, password='password')
        response = self.client.post(self.student_profile_url, self._valid_student_post(grade=9))

        # Redirect on success (or 200 if the module re-renders)
        self.assertIn(response.status_code, (200, 302),
                      "Expected 200 or 302 after valid profile POST")

        # A profile with student_info must now exist
        profiles = RegistrationProfile.objects.filter(user=student, student_info__isnull=False)
        self.assertTrue(profiles.exists(),
                        "A RegistrationProfile with student_info should be created")

        # grade must match the submitted value, not be forced to the smallest grade
        expected_yog = ESPUser.YOGFromGrade(9)
        prof = profiles.order_by('-last_ts').first()
        self.assertIsNotNone(prof.student_info.graduation_year)
        self.assertEqual(int(prof.student_info.graduation_year), expected_yog,
                         "graduation_year should equal the POSTed value, not the smallest grade")

    # ------------------------------------------------------------------
    # 4. Invalid data – graduation_year omitted
    # ------------------------------------------------------------------

    def test_student_profile_invalid_data(self):
        """POSTing with an empty graduation_year must fail validation (200 + error)."""
        from esp.program.models import RegistrationProfile

        student = self.students[1]
        RegistrationProfile.objects.filter(user=student).delete()

        self.client.login(username=student.username, password='password')
        response = self.client.post(self.student_profile_url,
                                    {'graduation_year': '', 'profile_page': ''})

        # Form must be re-rendered with an error, not redirected
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')

        # No completed profile should have been written
        self.assertFalse(
            RegistrationProfile.objects.filter(user=student, student_info__isnull=False).exists(),
            "No profile with student_info should be created when graduation_year is missing",
        )

    # ------------------------------------------------------------------
    # 5. Editing an existing student profile
    # ------------------------------------------------------------------

    def test_edit_existing_student_profile(self):
        """Posting updated contact data on an existing profile updates user info."""
        from esp.program.models import RegistrationProfile

        student = self.students[2]
        RegistrationProfile.objects.filter(user=student).delete()

        self.client.login(username=student.username, password='password')

        # Create the initial profile
        initial = self._valid_student_post(grade=9)
        initial.update({'first_name': 'Original', 'address_city': 'Boston'})
        self.client.post(self.student_profile_url, initial)

        # Edit: change first_name and city (grade unchanged – allow_change_grade_level is False)
        updated = self._valid_student_post(grade=9)
        updated.update({'first_name': 'Updated', 'address_city': 'Somerville'})
        response = self.client.post(self.student_profile_url, updated)

        self.assertIn(response.status_code, (200, 302))

        # User's first_name should reflect the edited submission
        student.refresh_from_db()
        self.assertEqual(student.first_name, 'Updated',
                         "User first_name should be updated after editing the profile")

        # Profile count should remain bounded (no runaway duplicates)
        profile_count = RegistrationProfile.objects.filter(user=student).count()
        self.assertLessEqual(profile_count, 3,
                             "Editing a profile must not create unbounded duplicates")

    # ------------------------------------------------------------------
    # 6. GET profile page – teacher
    # ------------------------------------------------------------------

    def test_get_profile_page_teacher(self):
        """A logged-in teacher can load the teacher profile page (200)."""
        self.client.login(username=self.teachers[0].username, password='password')
        response = self.client.get(self.teacher_profile_url)
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # 7. First-time teacher profile creation
    # ------------------------------------------------------------------

    def test_first_time_teacher_profile_creation(self):
        """POSTing valid teacher data creates a RegistrationProfile with teacher_info."""
        from esp.program.models import RegistrationProfile

        teacher = self.teachers[1]
        RegistrationProfile.objects.filter(user=teacher).delete()

        self.client.login(username=teacher.username, password='password')
        response = self.client.post(self.teacher_profile_url, self._valid_teacher_post())

        self.assertIn(response.status_code, (200, 302))
        self.assertTrue(
            RegistrationProfile.objects.filter(user=teacher, teacher_info__isnull=False).exists(),
            "A RegistrationProfile with teacher_info should be created after valid teacher POST",
        )

    # ------------------------------------------------------------------
    # 8. Default grade NOT auto-selected (PR #193)
    # ------------------------------------------------------------------

    def test_default_grade_not_auto_selected(self):
        """
        On a fresh profile page the graduation_year <select> must have the empty
        option pre-selected, never the smallest available grade (PR #193).
        """
        from esp.program.models import RegistrationProfile
        from esp.users.models import ESPUser

        student = self.students[0]
        RegistrationProfile.objects.filter(user=student).delete()

        self.client.login(username=student.username, password='password')
        response = self.client.get(self.student_profile_url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        lines = content.split('\n')

        # Locate the graduation_year <select>
        start_idx = None
        for i, line in enumerate(lines):
            if 'id="id_graduation_year"' in line:
                start_idx = i
                break
        self.assertIsNotNone(start_idx,
                             "graduation_year select not found in profile page HTML")

        # Locate its closing </select>
        end_offset = None
        for j, line in enumerate(lines[start_idx:]):
            if '</select>' in line:
                end_offset = j
                break
        self.assertIsNotNone(end_offset,
                             "Closing </select> for graduation_year not found")

        select_html = '\n'.join(lines[start_idx: start_idx + end_offset + 1])

        # The empty/blank option must be the selected one
        self.assertTrue(
            '<option value="" selected>' in select_html or
            '<option value="" selected></option>' in select_html,
            "The empty option must be pre-selected for graduation_year on a new profile (PR #193)",
        )

        # The smallest grade option must NOT be shown as selected
        smallest_grade = min(ESPUser.grade_options())
        smallest_yog   = str(ESPUser.YOGFromGrade(smallest_grade))
        self.assertNotIn(
            'value="%s" selected' % smallest_yog,
            select_html,
            "The smallest grade must NOT be auto-selected on the profile page (PR #193)",
        )

    # ------------------------------------------------------------------
    # 9. Grade null / error when omitted from POST (PR #193)
    # ------------------------------------------------------------------

    def test_grade_null_when_omitted(self):
        """
        Omitting graduation_year from a student profile POST must either:
          (a) produce a validation error and leave the profile uncreated, or
          (b) leave graduation_year as None/N/A – never defaulting to smallest grade.
        """
        from esp.program.models import RegistrationProfile
        from esp.users.models import ESPUser

        student = self.students[1]
        RegistrationProfile.objects.filter(user=student).delete()

        self.client.login(username=student.username, password='password')
        response = self.client.post(self.student_profile_url,
                                    {'graduation_year': '', 'profile_page': ''})

        if response.status_code in (301, 302):
            # If a redirect happened, the grade stored must NOT be the smallest grade
            smallest_yog = ESPUser.YOGFromGrade(min(ESPUser.grade_options()))
            prof = RegistrationProfile.objects.filter(
                user=student, student_info__isnull=False
            ).order_by('-last_ts').first()
            if prof is not None:
                self.assertNotEqual(
                    prof.student_info.graduation_year,
                    smallest_yog,
                    "graduation_year must not auto-default to the smallest grade (PR #193)",
                )
        else:
            # Expected path: 200 with a form error, nothing persisted
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'This field is required.')
