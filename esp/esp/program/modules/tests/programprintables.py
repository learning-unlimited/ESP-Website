__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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

from esp.program.tests import ProgramFrameworkTest

from django.test.client import RequestFactory

class ProgramPrintablesModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        from esp.program.models import Program
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        # Set up the program -- we want to be sure of these parameters
        kwargs.update({'num_students': 3,})
        super(ProgramPrintablesModuleTest, self).setUp(*args, **kwargs)

        self.add_student_profiles()
        self.schedule_randomly()
        self.classreg_students()

        # Get and remember the instance of this module
        m = ProgramModule.objects.get(handler='ProgramPrintables', module_type='manage')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, m)

        self.factory = RequestFactory()

    def get_response(self, view_name, user_type, list_name):
        #   Log in an administrator
        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'), "Failed to log in admin user.")

        #   Select users to fetch
        response = self.client.get('/manage/%s/%s' % (self.program.getUrlBase(), view_name))
        self.assertEquals(response.status_code, 200)
        post_data = {
            'recipient_type': user_type,
            'base_list': list_name,
            'use_checklist': 0,
        }
        response = self.client.post('/manage/%s/%s' % (self.program.getUrlBase(), view_name), post_data)
        self.assertTrue(response.status_code, 200)
        return response

    def get_userlist_views(self):
        #   Hard-code some views that can be tested using simple teacher/student lists.
        #   Exclude those tested by specialized functions below.
        teacher_views = ['teacherlist', 'teachersbytime', 'teacherschedules']
        student_views = ['studentsbyname', 'emergencycontacts', 'flatstudentschedules', 'studentchecklist', 'student_tickets']
        result = []
        for v in teacher_views:
            result.append((v, 'teachers', 'class_approved'))
        for v in student_views:
            result.append((v, 'students', 'enrolled'))
        return result

    def testAllViewsWithUserList(self):
        #   Specify which basic list of users to use for each printables view.
        view_pairs = self.get_userlist_views()

        #   Test each view in sequence with the appropriate list of users.
        #   Doesn't check correctness; please add separate test functions for that.
        for (view_name, user_type, list_name) in view_pairs:
            self.get_response(view_name, user_type, list_name)

    def testClassRosters(self):
        #   Check that all classes show up on the rosters.
        response = self.get_response('classrosters', 'teachers', 'class_approved')
        self.assertContains(response, '<div class="classtitle">', count=len(self.program.classes()))

    def testSchedules(self):
        #   Check that our Latex->PDF schedule generation code runs without error
        response = self.get_response('studentschedules', 'students', 'enrolled')

        #   Check that the output is an actual PDF file
        self.assertTrue(response['Content-Type'].startswith('application/pdf'))


