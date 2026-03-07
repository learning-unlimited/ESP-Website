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

from esp.program.models import FinancialAidRequest, SplashInfo, RegistrationType, StudentRegistration, ProgramModule
from esp.accounting.models import FinancialAidGrant, LineItemType

from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController
from esp.tagdict.models import Tag
from esp.program.controllers.studentclassregmodule import RegistrationTypeController

from decimal import Decimal
import json
import random
import re

class StudentRegTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        # Set up the program -- we want to be sure of these parameters
        kwargs.update( {
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 6, 'classes_per_teacher': 1, 'sections_per_class': 2,
            'num_rooms': 6, 'sibling_discount': 20,
            } )
        super().setUp(*args, **kwargs)

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
        self.assertContains(response, sec.title(), status_code=200)
        for ts in sec.meeting_times.all():
            self.assertContains(response, ts.short_description, status_code=200)

    def test_catalog(self):

        def verify_catalog_correctness():
            response = self.client.get('/learn/%s/catalog' % program.getUrlBase())
            for cls in self.program.classes():
                #   Find the portion of the catalog corresponding to this class
                pattern = r"""<div id="class_%d" class=".*?show_class" data-difficulty=".*" data-duration=".+" data-is-closed=".+">.*?</div>\s*?</div>\s*?</div>""" % cls.id
                cls_fragment = re.search(pattern, response.content.decode('UTF-8'), re.DOTALL).group(0)

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
                class_sections = cls.sections.order_by('id')
                self.assertTrue(len(enrollments) == len(list(class_sections)),
                                'Recovered {} enrollments from catalog but expecting {}. Listed below\n\tRecovered: {}\n\tExpecting: {}'.format(len(enrollments), len(list(class_sections)), enrollments, list(class_sections)))
                for sec in class_sections:
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
        LineItemType.objects.filter(text='Food', program=self.program).update(for_finaid=True) # Food should be covered by financial aid
        sd_lit = pac.default_siblingdiscount_lineitemtype() # Get the sibling discount line item type

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
        response = self.client.post('/learn/%s/extracosts' % self.program.getUrlBase(), {'%d-cost' % lit1.id: 'checked', '%d-count' % lit2.id: '0', '%d-siblingdiscount' % sd_lit.id: 'False'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), program_cost + 10)

        #   Check that selecting one or more than one of the "buy many" extra items works
        response = self.client.post('/learn/%s/extracosts' % self.program.getUrlBase(), {'%d-count' % lit2.id: '1', '%d-siblingdiscount' % sd_lit.id: 'False'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), program_cost + 5)

        response = self.client.post('/learn/%s/extracosts' % self.program.getUrlBase(), {'%d-count' % lit2.id: '3', '%d-siblingdiscount' % sd_lit.id: 'False'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), program_cost + 15)

        #   Check that selecting an option for a "multiple choice" extra item works
        lit3 = LineItemType.objects.get(program=self.program, text='Food')
        lio = [x for x in lit3.options if x[2] == 'Large'][0]
        response = self.client.post('/learn/%s/extracosts' % self.program.getUrlBase(), {'%d-count' % lit2.id: '0', 'multi%d-option' % lit3.id: str(lio[0]), '%d-siblingdiscount' % sd_lit.id: 'False'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), program_cost + 7)

        #   Check that financial aid applies to the "full" cost including the extra items
        #   (e.g. we are not forcing financial aid students to pay for food)
        request = FinancialAidRequest.objects.create(user=student, program=self.program)
        (fg, created) = FinancialAidGrant.objects.get_or_create(request=request, percent=100)
        self.assertEqual(iac.amount_due(), 0)

        #   Check that financial aid only covers items marked as "for_finaid"
        LineItemType.objects.filter(text='Food', program=self.program).update(for_finaid=False)
        self.assertEqual(iac.amount_due(), 7)

        fg.delete()

        #   Check that removing items on the form removes their cost for the student
        response = self.client.post('/learn/%s/extracosts' % self.program.getUrlBase(), {'%d-count' % lit2.id: '0', '%d-siblingdiscount' % sd_lit.id: 'False'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), program_cost)

        #   Check that the sibling discount works
        response = self.client.post('/learn/%s/extracosts' % self.program.getUrlBase(), {'%d-siblingdiscount' % sd_lit.id: 'True', '%d-siblingname' % sd_lit.id: 'Test Name'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), program_cost - 20)
        spi = SplashInfo.getForUser(student, self.program)
        self.assertEqual(spi.siblingname, 'Test Name')


class RegistrationTypeVisibilityTest(ProgramFrameworkTest):
    """
    Tests for Issue #227: registration type visibility filtering on the student
    registration page, introduced in PR #207 to resolve Issue #35.

    The 'display_registration_names' Tag controls which RegistrationTypes are
    shown on the student main registration page.  These tests exercise
    RegistrationTypeController.getVisibleRegistrationTypeNames() directly and
    through the live HTTP response to /learn/<prog>/studentreg.
    """

    def setUp(self):
        modules = [
            ProgramModule.objects.get(handler='TeacherClassRegModule'),
            ProgramModule.objects.get(handler='StudentClassRegModule'),
            ProgramModule.objects.get(handler='StudentRegCore'),
        ]
        super().setUp(modules=modules)
        self.schedule_randomly()
        self.add_student_profiles()

        # Disable the required-modules gate so the studentreg page renders directly
        scrmi = self.program.studentclassregmoduleinfo
        scrmi.force_show_required_modules = False
        scrmi.save()

        # Ensure the registration types we test with exist
        RegistrationType.objects.get_or_create(name='Enrolled')
        self.rt_waitlisted, _ = RegistrationType.objects.get_or_create(name='Waitlisted')
        self.rt_priority, _   = RegistrationType.objects.get_or_create(name='Priority')

        # Pick the first student and give them registrations under all three types
        self.student = self.students[0]
        self.student.set_password('password')
        self.student.save()

        section = self.teachers[0].getTaughtSectionsFromProgram(self.program)[0]
        for rt_name in ('Enrolled', 'Waitlisted', 'Priority'):
            rt = RegistrationType.objects.get(name=rt_name)
            StudentRegistration.objects.get_or_create(
                user=self.student, section=section, relationship=rt
            )

        # Start each test with a clean slate — no display_registration_names tag
        Tag.objects.filter(key='display_registration_names').delete()

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _set_tag(self, names):
        """Create/update a program-scoped display_registration_names tag."""
        Tag.setTag(
            key='display_registration_names',
            target=self.program,
            value=json.dumps(names),
        )

    def _student_login(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
            'Could not log in as test student',
        )

    def _get_studentreg(self):
        return self.client.get('/learn/' + self.program.url + '/studentreg')

    # ------------------------------------------------------------------
    # Test A: Default behaviour — no tag set
    # ------------------------------------------------------------------

    def test_default_no_tag(self):
        """
        When no display_registration_names tag exists the controller returns
        only the default ['Enrolled'] list, and the student reg page does not
        surface any non-default registration type names.
        """
        # Controller returns the hardcoded default
        visible = RegistrationTypeController.getVisibleRegistrationTypeNames(self.program)
        self.assertIn('Enrolled', visible)
        self.assertNotIn('Waitlisted', visible)
        self.assertNotIn('Priority', visible)

        # HTTP response agrees
        self._student_login()
        response = self._get_studentreg()
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Waitlisted')
        self.assertNotContains(response, 'Priority')

    # ------------------------------------------------------------------
    # Test B: Tag restricts which types are visible
    # ------------------------------------------------------------------

    def test_tag_restricts_visible_types(self):
        """
        When the tag lists only 'Waitlisted', the controller returns
        ['Waitlisted', 'Enrolled'] (tag value merged with the mandatory
        default).  The student reg page shows 'Waitlisted' but not 'Priority'.
        """
        self._set_tag(['Waitlisted'])

        visible = RegistrationTypeController.getVisibleRegistrationTypeNames(self.program)
        self.assertIn('Enrolled', visible,
                      'Enrolled must always be present regardless of tag')
        self.assertIn('Waitlisted', visible)
        self.assertNotIn('Priority', visible)

        self._student_login()
        response = self._get_studentreg()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Waitlisted')
        self.assertNotContains(response, 'Priority')

    # ------------------------------------------------------------------
    # Test C: Changing the tag dynamically updates what the page shows
    # ------------------------------------------------------------------

    def test_tag_change_reflects_on_page(self):
        """
        Updating the tag value is immediately reflected on the next GET of
        the student reg page without any restart or cache invalidation step.
        """
        self._student_login()

        # First configuration: only Waitlisted (+ Enrolled)
        self._set_tag(['Waitlisted'])
        response = self._get_studentreg()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Waitlisted')
        self.assertNotContains(response, 'Priority')

        # Second configuration: only Priority (+ Enrolled)
        Tag.objects.filter(key='display_registration_names').delete()
        self._set_tag(['Priority'])
        response = self._get_studentreg()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Priority')
        self.assertNotContains(response, 'Waitlisted')

    # ------------------------------------------------------------------
    # Test D: 'All' sentinel returns every RegistrationType
    # ------------------------------------------------------------------

    def test_all_sentinel_shows_every_type(self):
        """
        When the tag contains the special value 'All', every RegistrationType
        name in the database is returned.  Passing for_VRT_form=True additionally
        appends the literal string 'All' to the result (used by the admin form).
        """
        self._set_tag(['All'])

        # Normal (student-facing) call: every RT name, but NOT the literal 'All'
        visible = RegistrationTypeController.getVisibleRegistrationTypeNames(self.program)
        all_names = list(
            RegistrationType.objects.values_list('name', flat=True)
                                    .distinct().order_by('name')
        )
        for name in all_names:
            self.assertIn(name, visible,
                         'Expected %r in visible types when tag is "All"' % name)
        self.assertNotIn('All', visible,
                         'Literal "All" must not appear in the student-facing list')

        # Admin VRT form call: 'All' appended so the form can re-select it
        visible_vrt = RegistrationTypeController.getVisibleRegistrationTypeNames(
            self.program, for_VRT_form=True
        )
        self.assertIn('All', visible_vrt)

    # ------------------------------------------------------------------
    # Test E: Empty or invalid tag falls back safely
    # ------------------------------------------------------------------

    def test_empty_tag_falls_back_to_default(self):
        """
        A tag that exists but carries an empty string value is treated as
        absent: the controller returns the default ['Enrolled'] list and
        the student reg page renders without error.
        """
        # Manually insert a tag with an empty value (bypasses Tag.setTag validation)
        Tag.objects.get_or_create(key='display_registration_names', value='')

        visible = RegistrationTypeController.getVisibleRegistrationTypeNames(self.program)
        # Empty string is falsy -> falls back to default_names
        self.assertEqual(list(visible), RegistrationTypeController.default_names)

        self._student_login()
        response = self._get_studentreg()
        self.assertEqual(response.status_code, 200)

    def test_malformed_tag_raises_json_error(self):
        """
        A tag value that is not valid JSON causes json.JSONDecodeError to be
        raised by the controller.  This documents the current (unguarded)
        behaviour so that any future defensive fix is intentional and tested.
        """
        Tag.objects.get_or_create(key='display_registration_names', value='not_valid_json')
        with self.assertRaises(json.JSONDecodeError):
            RegistrationTypeController.getVisibleRegistrationTypeNames(self.program)

    def test_none_program_returns_default(self):
        """
        Passing prog=None (or any non-Program value) to the controller is
        safe: it returns the default set without touching the database.
        """
        visible = RegistrationTypeController.getVisibleRegistrationTypeNames(None)
        self.assertEqual(set(visible), set(RegistrationTypeController.default_names))

    def test_invalid_program_id_returns_default(self):
        """
        Passing a numeric program id that does not exist in the database
        returns the default set without raising an exception.
        """
        visible = RegistrationTypeController.getVisibleRegistrationTypeNames(999999999)
        self.assertEqual(set(visible), set(RegistrationTypeController.default_names))

