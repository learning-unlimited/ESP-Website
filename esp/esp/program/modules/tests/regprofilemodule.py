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
            self.assertTrue( not self.moduleobj.isCompleted(student), "The profile should be incomplete at first." )

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
        self.assertTrue( self.moduleobj.isCompleted(self.students[0]), "Profile id wiped." )
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
        self.assertTrue( not self.moduleobj.isCompleted(self.students[1]), "Profile too old but accepted anyway." )
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
    """Comprehensive tests for RegistrationProfile form flows (issue #225)."""

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 3, 'num_teachers': 2})
        super().setUp(*args, **kwargs)
        self.student_profile_url = '%sprofile' % self.program.get_learn_url()

    def _valid_student_post(self, student, grade=9):
        from esp.users.models import ESPUser

        yog = str(ESPUser.YOGFromGrade(grade))
        return {
            'profile_page': '',
            'first_name': student.first_name,
            'last_name': student.last_name,
            'e_mail': student.email,
            'phone_day': '+16175550101',
            'phone_cell': '',
            'receive_txt_message': 'False',
            'address_street': '123 Main St',
            'address_city': 'Boston',
            'address_state': 'MA',
            'address_zip': '02139',
            'address_country': '',
            'emerg_first_name': 'Emergency',
            'emerg_last_name': 'Contact',
            'emerg_e_mail': 'emerg@example.com',
            'emerg_phone_day': '+16175550102',
            'emerg_phone_cell': '',
            'emerg_address_street': '456 Side St',
            'emerg_address_city': 'Cambridge',
            'emerg_address_state': 'MA',
            'emerg_address_zip': '02139',
            'emerg_address_country': '',
            'guard_first_name': 'Guardian',
            'guard_last_name': 'Person',
            'guard_e_mail': 'guardian@example.com',
            'guard_phone_day': '+16175550103',
            'guard_phone_cell': '',
            'graduation_year': yog,
            'dob_0': '6',
            'dob_1': '15',
            'dob_2': '2010',
            'k12school': '',
            'school': 'Test High School',
            'unmatched_school': 'on',
            'heard_about_0': '',
            'heard_about_1': '',
            'transportation_0': '',
            'transportation_1': '',
        }

    def test_student_profile_invalid_data(self):
        """Missing graduation_year must attach a field-specific validation error."""
        from esp.program.models import RegistrationProfile

        student = self.students[1]
        self.client.login(username=student.username, password='password')

        before_count = RegistrationProfile.objects.filter(
            user=student,
            student_info__isnull=False,
        ).count()

        invalid = self._valid_student_post(student, grade=9)
        invalid['graduation_year'] = ''
        response = self.client.post(self.student_profile_url, invalid)

        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('graduation_year', response.context['form'].errors)
        self.assertIn('This field is required.', response.context['form'].errors['graduation_year'])

        after_count = RegistrationProfile.objects.filter(
            user=student,
            student_info__isnull=False,
        ).count()
        self.assertEqual(before_count, after_count)

    def test_edit_existing_student_profile(self):
        """Second valid POST should update existing program profile, not create another."""
        from esp.program.models import RegistrationProfile

        student = self.students[0]
        self.client.login(username=student.username, password='password')

        initial = self._valid_student_post(student, grade=9)
        initial.update({'first_name': 'Original', 'address_city': 'Boston'})
        initial_response = self.client.post(self.student_profile_url, initial)

        self.assertIn(initial_response.status_code, (200, 302))
        initial_profiles = RegistrationProfile.objects.filter(
            user=student,
            program=self.program,
            student_info__isnull=False,
        )
        self.assertEqual(initial_profiles.count(), 1)
        initial_profile_id = initial_profiles.get().id

        updated = self._valid_student_post(student, grade=9)
        updated.update({'first_name': 'Updated', 'address_city': 'Somerville'})
        response = self.client.post(self.student_profile_url, updated)

        self.assertIn(response.status_code, (200, 302))

        student.refresh_from_db()
        self.assertEqual(student.first_name, 'Updated')

        profiles_after_edit = RegistrationProfile.objects.filter(
            user=student,
            program=self.program,
            student_info__isnull=False,
        )
        self.assertEqual(profiles_after_edit.count(), 1)
        self.assertEqual(profiles_after_edit.get().id, initial_profile_id)

    def test_grade_null_when_omitted(self):
        """Omitting graduation_year must not auto-default to the smallest grade."""
        from esp.program.models import RegistrationProfile
        from esp.users.models import ESPUser

        student = self.students[2]
        self.client.login(username=student.username, password='password')

        before_count = RegistrationProfile.objects.filter(
            user=student,
            student_info__isnull=False,
        ).count()

        payload = self._valid_student_post(student, grade=9)
        del payload['graduation_year']
        response = self.client.post(self.student_profile_url, payload)

        if response.status_code in (301, 302):
            smallest_yog = ESPUser.YOGFromGrade(min(ESPUser.grade_options()))
            prof = RegistrationProfile.objects.filter(
                user=student,
                student_info__isnull=False,
            ).order_by('-last_ts').first()

            self.assertIsNotNone(prof)
            self.assertNotEqual(prof.student_info.graduation_year, smallest_yog)
            self.assertIn(prof.student_info.graduation_year, (None, ''))
        else:
            self.assertEqual(response.status_code, 200)
            self.assertIn('form', response.context)
            self.assertIn('graduation_year', response.context['form'].errors)
            self.assertIn('This field is required.', response.context['form'].errors['graduation_year'])

            after_count = RegistrationProfile.objects.filter(
                user=student,
                student_info__isnull=False,
            ).count()
            self.assertEqual(before_count, after_count)
