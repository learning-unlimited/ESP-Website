__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
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

from esp.program.models import FinancialAidRequest
from esp.accounting.models import FinancialAidGrant, LineItemType

from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController

from decimal import Decimal
import random
import re

class StudentRegTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        # Set up the program -- we want to be sure of these parameters
        kwargs.update( {
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 6, 'classes_per_teacher': 1, 'sections_per_class': 2,
            'num_rooms': 6,
            } )
        super(StudentRegTest, self).setUp(*args, **kwargs)

        self.add_student_profiles()
        self.schedule_randomly()

        #   Make all modules non-required for now, so we don't have to be shown required pages
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        # Get and remember the instance of StudentClassRegModule
        pm = ProgramModule.objects.get(handler='StudentClassRegModule')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.moduleobj.user = self.students[0]

    def get_template_names(self, response):
        return [x.name for x in response.templates]

    def expect_template(self, response, template):
        self.assertTrue(template in self.get_template_names(response), 'Wrong template for profile: got %s, expected %s' % (self.get_template_names(response), template))

    def test_confirm(self):
        program = self.program

        #   Pick a student and log in
        student = random.choice(self.students)
        self.assertTrue( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )

        #   Sign up for a class directly
        sec = random.choice(program.sections())
        sec.preregister_student(student)

        #   Get the receipt and check that the class appears on it with title and time
        response = self.client.get('/learn/%s/confirmreg' % self.program.getUrlBase())
        self.assertTrue(sec.title() in response.content)
        for ts in sec.meeting_times.all():
            self.assertTrue(ts.short_description in response.content)

    def test_catalog(self):

        def verify_catalog_correctness():
            response = self.client.get('/learn/%s/catalog' % program.getUrlBase())
            for cls in self.program.classes():
                #   Find the portion of the catalog corresponding to this class
                pattern = r"""<div id="class_%d" class=".*?show_class">.*?</div>\s*?</div>\s*?</div>""" % cls.id
                cls_fragment = re.search(pattern, response.content, re.DOTALL).group(0)

                pat2 = r"""<div.*?class="class_title">(?P<title>.*?)</div>.*?<div class="class_content">(?P<description>.*?)</div>.*?<strong>Enrollment</strong>(?P<enrollment>.*?)</div>"""
                cls_info = re.search(pat2, cls_fragment, re.DOTALL).groupdict(0)

                #   Check title
                title = cls_info['title'].strip()
                expected_title = '%s: %s' % (cls.emailcode(), cls.title)
                self.assertTrue(title == expected_title, 'Incorrect class title in catalog: got "%s", expected "%s"' % (title, expected_title))

                #   Check description
                description = cls_info['description'].replace('<br />', '').strip()
                self.assertTrue(description == cls.class_info.strip(), 'Incorrect class description in catalog: got "%s", expected "%s"' % (description, cls.class_info.strip()))

                #   Check enrollments
                enrollments = [x.replace('<br />', '').strip() for x in cls_info['enrollment'].split('Section')[1:]]
                for sec in cls.sections.order_by('id'):
                    i = sec.index() - 1
                    expected_str = '%s: %s (max %s)' % (sec.index(), sec.num_students(), sec.capacity)
                    self.assertTrue(enrollments[i] == expected_str, 'Incorrect enrollment for %s in catalog: got "%s", expected "%s"' % (sec.emailcode(), enrollments[i], expected_str))

        program = self.program

        #   Get the catalog and check that everything is OK
        verify_catalog_correctness()

        #   Change a class title and check
        cls = random.choice(program.classes())
        cls.title = 'New %s' % cls.title
        cls.save()
        verify_catalog_correctness()

        #   Change a class description and check
        cls2 = random.choice(program.classes())
        cls2.class_info = 'New %s' % cls2.class_info
        cls2.save()
        verify_catalog_correctness()

        #   Register a student for a class and check
        sec = random.choice(program.sections())
        student = random.choice(self.students)
        sec.preregister_student(student)
        verify_catalog_correctness()

    def test_profile(self):

        #   Login as a student and ensure we can submit the profile
        student = random.choice(self.students)
        self.assertTrue( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )
        response = self.client.get('/learn/%s/profile' % self.program.getUrlBase())
        self.expect_template(response, 'users/profile.html')

        #   Login as a teacher and ensure we get the right message
        teacher = random.choice(self.teachers)
        self.assertTrue( self.client.login( username=teacher.username, password='password' ), "Couldn't log in as student %s" % teacher.username )
        response = self.client.get('/learn/%s/profile' % self.program.getUrlBase())
        self.expect_template(response, 'errors/program/notastudent.html')

        #   Login as an admin and ensure we get the right message
        admin = random.choice(self.admins)
        self.assertTrue( self.client.login( username=admin.username, password='password' ), "Couldn't log in as student %s" % admin.username )
        response = self.client.get('/learn/%s/profile' % self.program.getUrlBase())
        self.expect_template(response, 'users/profile.html')

    def test_finaid(self):
        """ Verify that financial aid behaves as specified. """

        program_cost = 25.0

        #   Set the cost of the program
        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(program_cost)

        #   Choose a random student and sign up for a class
        student = random.choice(self.students)
        iac = IndividualAccountingController(self.program, student)
        sec = random.choice(self.program.sections())
        sec.preregister_student(student)

        #   Check that the student owes the cost of the program
        self.assertEqual(iac.amount_due(), program_cost)

        #   Apply for financial aid
        self.assertTrue( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )
        response = self.client.get(
                    '/learn/%s/finaid' % self.program.url,
                    **{'wsgi.url_scheme': 'https'})
        self.assertEqual(response.status_code, 200)

        form_settings = {
            'reduced_lunch': '',
            'household_income': '12345',
            'extra_explaination': 'No',
            'student_prepare': '',
        }
        response = self.client.post('/learn/%s/finaid' % self.program.getUrlBase(), form_settings)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])

        #   Check that the student still owes the cost of the program
        self.assertEqual(iac.amount_due(), program_cost)

        #   Have an admin approve the financial aid app and check a few different cases:
        request = FinancialAidRequest.objects.get(user=student, program=self.program)

        #   - 100 percent
        (fg, created) = FinancialAidGrant.objects.get_or_create(request=request, percent=100)
        self.assertEqual(iac.amount_due(), 0.0)

        #   - absolute discount amount
        fg.percent = None
        fg.amount_max_dec = Decimal('15.0')
        fg.save()
        self.assertEqual(iac.amount_due(), program_cost - 15.0)

        #   - discount percentage
        fg.amount_max_dec = None
        fg.percent = 50
        fg.save()
        self.assertEqual(iac.amount_due(), program_cost / 2)

        #   Check that deleting the financial aid grant restores original program cost
        fg.delete()
        self.assertEqual(iac.amount_due(), program_cost)

        #   Check that the 'free/reduced lunch' option on the finaid results in zero amount due
        form_settings = {
            'reduced_lunch': 'checked',
            'household_income': '12345',
            'extra_explaination': 'No',
            'student_prepare': '',
        }
        response = self.client.post('/learn/%s/finaid' % self.program.getUrlBase(), form_settings)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), 0)

    def test_extracosts(self):
        """ Verify that the "Student Extra Costs" module behaves as specified. """

        program_cost = 25.0

        #   Set up some extra costs options: Item1 (max-qty 1) for $10, Item2 (max-qty 10) for $5, and selectable food
        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(program_cost, [('Item1', 10, 1), ('Item2', 5, 10)], [('Food', [('Small', 3), ('Large', 7)])])

        #   Choose a random student and check that the extracosts page loads
        student = random.choice(self.students)
        iac = IndividualAccountingController(self.program, student)
        self.assertTrue( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )
        response = self.client.get('/learn/%s/extracosts' % self.program.url)
        self.assertEqual(response.status_code, 200)

        #   Check that they are being charged the program admission fee
        self.assertEqual(iac.amount_due(), program_cost)

        #   Check that selecting one of the "buy-one" extra items works
        lit1 = LineItemType.objects.get(program=self.program, text='Item1')
        lit2 = LineItemType.objects.get(program=self.program, text='Item2')
        response = self.client.post('/learn/%s/extracosts' % self.program.getUrlBase(), {'%d-cost' % lit1.id: 'checked', '%d-count' % lit2.id: '0'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), program_cost + 10)

        #   Check that selecting one or more than one of the "buy many" extra items works
        response = self.client.post('/learn/%s/extracosts' % self.program.getUrlBase(), {'%d-count' % lit2.id: '1'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), program_cost + 5)

        response = self.client.post('/learn/%s/extracosts' % self.program.getUrlBase(), {'%d-count' % lit2.id: '3'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), program_cost + 15)

        #   Check that selecting an option for a "multiple choice" extra item works
        lit3 = LineItemType.objects.get(program=self.program, text='Food')
        lio = filter(lambda x: x[2] == 'Large', lit3.options)[0]
        response = self.client.post('/learn/%s/extracosts' % self.program.getUrlBase(), {'%d-count' % lit2.id: '0', 'multi%d-option' % lit3.id: str(lio[0])})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), program_cost + 7)

        #   Check that financial aid applies to the "full" cost including the extra items
        #   (e.g. we are not forcing financial aid students to pay for food)
        request = FinancialAidRequest.objects.create(user=student, program=self.program)
        (fg, created) = FinancialAidGrant.objects.get_or_create(request=request, percent=100)
        self.assertEqual(iac.amount_due(), 0.0)
        fg.delete()

        #   Check that removing items on the form removes their cost for the student
        response = self.client.post('/learn/%s/extracosts' % self.program.getUrlBase(), {'%d-count' % lit2.id: '0'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), program_cost)

