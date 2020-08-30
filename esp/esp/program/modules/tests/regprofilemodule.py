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
        super(RegProfileModuleTest, self).setUp(*args, **kwargs)

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
        lines = response.content.split('\n')

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
