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

from esp.program.models import FinancialAidRequest, SplashInfo
from esp.accounting.models import FinancialAidGrant, LineItemType

from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController
from esp.users.models import ESPUser

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
        self.assertTrue(template in self.get_template_names(response), f'Wrong template for profile: got {self.get_template_names(response)}, expected {template}')

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
                expected_title = f'{cls.emailcode()}: {cls.title}'
                self.assertTrue(title == expected_title, f'Incorrect class title in catalog: got "{title}", expected "{expected_title}"')

                #   Check description
                description = cls_info['description'].replace('<br />', '').strip()
                self.assertTrue(description == cls.class_info.strip(), f'Incorrect class description in catalog: got "{description}", expected "{cls.class_info.strip()}"')

                #   Check enrollments
                enrollments = [x.replace('<br />', '').strip() for x in cls_info['enrollment'].split('Section')[1:]]
                class_sections = cls.sections.order_by('id')
                self.assertTrue(len(enrollments) == len(list(class_sections)),
                                f'Recovered {len(enrollments)} enrollments from catalog but expecting {len(list(class_sections))}. Listed below\n\tRecovered: {enrollments}\n\tExpecting: {list(class_sections)}')
                for sec in class_sections:
                    i = sec.index() - 1
                    expected_str = f'{sec.index()}: {sec.num_students()} (max {sec.capacity})'
                    self.assertTrue(enrollments[i] == expected_str, f'Incorrect enrollment for {sec.emailcode()} in catalog: got "{enrollments[i]}", expected "{expected_str}"')

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

    def test_separate_catalog(self):
        from esp.tagdict.models import Tag
        from esp.program.models import ClassSubject

        # Enable separate catalog pages
        Tag.setTag('separate_catalog_pages', target=self.program, value='True')

        # Get a category ID from existing classes
        classes = ClassSubject.objects.catalog(self.program)
        self.assertTrue(len(classes) > 0, "No classes found to test catalog")
        cat = classes[0].category
        cat_id = cat.id
        cat_name = cat.category

        # Test main catalog page (should only show categories, no classes)
        response = self.client.get('/learn/%s/catalog' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jump to Categories')
        self.assertContains(response, '/learn/%s/catalog/%s' % (self.program.getUrlBase(), cat_id))

        # Test specific category page
        response = self.client.get('/learn/%s/catalog/%s' % (self.program.getUrlBase(), cat_id))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Back to Category List')
        self.assertContains(response, cat_name)

        # Disable the tag and ensure original behavior
        Tag.setTag('separate_catalog_pages', target=self.program, value='False')
        response = self.client.get('/learn/%s/catalog' % self.program.getUrlBase())
        self.assertContains(response, 'Jump to Categories')
        # Anchor links instead of URL links
        self.assertContains(response, '#cat%s' % cat_id)

    def test_separate_catalog_main_page_no_class_content(self):
        """When separate_catalog_pages is enabled, the main catalog page should
        not render individual class descriptions — only category links."""
        from esp.tagdict.models import Tag
        from esp.program.models import ClassSubject

        Tag.setTag('separate_catalog_pages', target=self.program, value='True')

        classes = ClassSubject.objects.catalog(self.program)
        self.assertTrue(len(classes) > 0)

        response = self.client.get('/learn/%s/catalog' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('UTF-8')
        # Individual class divs should NOT appear on the main page
        for cls in classes:
            self.assertNotIn('class_%d' % cls.id, content,
                "Class %s should not appear on the main catalog page when separate_catalog_pages is enabled" % cls.emailcode())

    def test_separate_catalog_category_shows_only_matching_classes(self):
        """A category page should only show classes belonging to that category."""
        from esp.tagdict.models import Tag
        from esp.program.models import ClassSubject

        Tag.setTag('separate_catalog_pages', target=self.program, value='True')

        classes = ClassSubject.objects.catalog(self.program)
        self.assertTrue(len(classes) > 0)

        # Build a mapping of category_id -> class ids
        cat_classes = {}
        for cls in classes:
            cat_classes.setdefault(cls.category_id, []).append(cls.id)

        # Only test if we have at least one category with classes
        for cat_id, class_ids in cat_classes.items():
            response = self.client.get('/learn/%s/catalog/%s' % (self.program.getUrlBase(), cat_id))
            self.assertEqual(response.status_code, 200)
            content = response.content.decode('UTF-8')

            # Classes in this category should be present
            for cid in class_ids:
                self.assertIn('class_%d' % cid, content,
                    "Class id=%d should appear on category %d page" % (cid, cat_id))

            # Classes from OTHER categories should NOT be present
            for other_cat_id, other_ids in cat_classes.items():
                if other_cat_id == cat_id:
                    continue
                for cid in other_ids:
                    self.assertNotIn('class_%d' % cid, content,
                        "Class id=%d (category %d) should not appear on category %d page" % (cid, other_cat_id, cat_id))

    def test_separate_catalog_invalid_category_id(self):
        """A non-numeric extra parameter should yield an empty class list (no crash)."""
        from esp.tagdict.models import Tag

        Tag.setTag('separate_catalog_pages', target=self.program, value='True')

        response = self.client.get('/learn/%s/catalog/not-a-number' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)
        # Should still render the page without error
        content = response.content.decode('UTF-8')
        self.assertNotIn('class_', content,
            "No classes should appear for an invalid category id")

    def test_separate_catalog_nonexistent_category_id(self):
        """A numeric category id that doesn't match any category should show no classes."""
        from esp.tagdict.models import Tag

        Tag.setTag('separate_catalog_pages', target=self.program, value='True')

        response = self.client.get('/learn/%s/catalog/999999' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('UTF-8')
        self.assertNotIn('class_', content,
            "No classes should appear for a non-existent category id")

    def test_separate_catalog_back_link(self):
        """The category page should contain a link back to the main catalog."""
        from esp.tagdict.models import Tag
        from esp.program.models import ClassSubject

        Tag.setTag('separate_catalog_pages', target=self.program, value='True')

        classes = ClassSubject.objects.catalog(self.program)
        self.assertTrue(len(classes) > 0)
        cat_id = classes[0].category_id

        response = self.client.get('/learn/%s/catalog/%s' % (self.program.getUrlBase(), cat_id))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/learn/%s/catalog' % self.program.getUrlBase(),
            msg_prefix="Category page should contain a back-link to the main catalog")
        self.assertContains(response, 'Back to Category List')

    def test_separate_catalog_disabled_shows_all_classes(self):
        """When the tag is disabled (or absent), the catalog should render all classes
        with anchor-based category navigation."""
        from esp.tagdict.models import Tag
        from esp.program.models import ClassSubject

        # Ensure the tag is explicitly disabled
        Tag.setTag('separate_catalog_pages', target=self.program, value='False')

        classes = ClassSubject.objects.catalog(self.program)
        self.assertTrue(len(classes) > 0)

        response = self.client.get('/learn/%s/catalog' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('UTF-8')

        # All classes should appear on the single catalog page
        for cls in classes:
            self.assertIn('class_%d' % cls.id, content,
                "Class %s should appear on the catalog when separate_catalog_pages is disabled" % cls.emailcode())

        # Category links should be anchors, not separate-page URLs
        seen_categories = set()
        for cls in classes:
            if cls.category_id not in seen_categories:
                seen_categories.add(cls.category_id)
                self.assertContains(response, '#cat%s' % cls.category_id)
                self.assertNotContains(response, '/learn/%s/catalog/%s' % (self.program.getUrlBase(), cls.category_id))

    def test_separate_catalog_context_variables(self):
        """Verify that the template context contains the expected variables
        for separate catalog mode."""
        from esp.tagdict.models import Tag
        from esp.program.models import ClassSubject

        Tag.setTag('separate_catalog_pages', target=self.program, value='True')

        classes = ClassSubject.objects.catalog(self.program)
        self.assertTrue(len(classes) > 0)
        cat_id = classes[0].category_id

        # Main catalog page: separate_catalog=True, selected_category=None
        response = self.client.get('/learn/%s/catalog' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['separate_catalog'],
            "Context should have separate_catalog=True")
        self.assertIsNone(response.context['selected_category'],
            "Context should have selected_category=None on main page")
        self.assertIn('categories', response.context)
        self.assertTrue(len(response.context['categories']) > 0,
            "Context should contain at least one category")

        # Category-specific page: separate_catalog=True, selected_category set
        response = self.client.get('/learn/%s/catalog/%s' % (self.program.getUrlBase(), cat_id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['separate_catalog'])
        self.assertIsNotNone(response.context['selected_category'],
            "Context should have selected_category set on a category page")
        self.assertEqual(response.context['selected_category']['id'], cat_id)

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


class UserviewGradeUpdateTest(ProgramFrameworkTest):
    """
    Tests for the grade-update functionality introduced in PR #208 (commit
    7db5367) that resolves Issue #26.  The feature allows an admin to visit
    /manage/userview?username=<student>&graduation_year=<year> and have the
    student's graduation year updated immediately.

    Covers Issue #226: "Test for updating student grades".
    """

    def setUp(self, *args, **kwargs):
        # Minimal program scaffold; we only need students, teachers, and admins.
        kwargs.update({
            'num_timeslots': 1, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 1, 'classes_per_teacher': 1, 'sections_per_class': 1,
            'num_rooms': 1,
        })
        super().setUp(*args, **kwargs)

        # Build StudentInfo / RegistrationProfile rows for every student.
        self.add_student_profiles()

        self.student = self.students[0]
        self.admin   = self.admins[0]

        # Record the initial graduation year so each test can assert "unchanged".
        self.initial_grad_year = (
            self.student.getLastProfile().student_info.graduation_year
        )

        # A graduation year different from the initial one, chosen from a valid
        # ChoiceField value (grade 11 in the current school year).
        new_grade = 11
        new_yog = ESPUser.YOGFromGrade(new_grade)
        # Make sure we actually pick a *different* value
        if new_yog == self.initial_grad_year:
            new_grade = 10
            new_yog = ESPUser.YOGFromGrade(new_grade)
        self.new_grad_year = new_yog

        self.userview_base = '/manage/userview'

    # ------------------------------------------------------------------
    # Test 1: Admin can update a student's grade
    # ------------------------------------------------------------------

    def test_admin_can_update_grade(self):
        """A logged-in admin should be able to change a student's graduation
        year via the graduation_year GET parameter."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(self.userview_base, data={
            'username': self.student.username,
            'graduation_year': self.new_grad_year,
        })
        self.assertEqual(response.status_code, 200)

        # Re-fetch from DB to confirm persistence.
        updated_info = self.student.getLastProfile().student_info
        self.assertEqual(
            updated_info.graduation_year, self.new_grad_year,
            "Admin update failed: expected grad year %s, got %s"
            % (self.new_grad_year, updated_info.graduation_year),
        )

    # ------------------------------------------------------------------
    # Test 2: A student cannot update their own grade
    # ------------------------------------------------------------------

    def test_student_cannot_update_own_grade(self):
        """A student is not an administrator, so the view should return 403
        and leave the graduation year unchanged."""
        self.client.login(username=self.student.username, password='password')
        response = self.client.get(self.userview_base, data={
            'username': self.student.username,
            'graduation_year': self.new_grad_year,
        })
        self.assertEqual(
            response.status_code, 403,
            "Expected 403 for non-admin access, got %s" % response.status_code,
        )

        # Grade must not have changed.
        info = self.student.getLastProfile().student_info
        self.assertEqual(
            info.graduation_year, self.initial_grad_year,
            "Graduation year was incorrectly modified by the student themselves.",
        )

    # ------------------------------------------------------------------
    # Test 3: An unrelated non-admin user cannot update the grade
    # ------------------------------------------------------------------

    def test_non_admin_cannot_update_grade(self):
        """A teacher (non-admin) should receive 403 and leave the grade
        unchanged."""
        teacher = self.teachers[0]
        self.client.login(username=teacher.username, password='password')
        response = self.client.get(self.userview_base, data={
            'username': self.student.username,
            'graduation_year': self.new_grad_year,
        })
        self.assertEqual(
            response.status_code, 403,
            "Expected 403 for teacher access, got %s" % response.status_code,
        )

        info = self.student.getLastProfile().student_info
        self.assertEqual(
            info.graduation_year, self.initial_grad_year,
            "Graduation year was incorrectly modified by a non-admin teacher.",
        )

    # ------------------------------------------------------------------
    # Test 4: Unauthenticated user is redirected and grade is unchanged
    # ------------------------------------------------------------------

    def test_unauthenticated_cannot_update_grade(self):
        """An unauthenticated visitor should be redirected to login (302) and
        the graduation year must remain untouched."""
        # Ensure no session cookie is active.
        self.client.logout()
        response = self.client.get(self.userview_base, data={
            'username': self.student.username,
            'graduation_year': self.new_grad_year,
        })
        self.assertEqual(
            response.status_code, 302,
            "Expected 302 redirect for unauthenticated access, got %s"
            % response.status_code,
        )

        info = self.student.getLastProfile().student_info
        self.assertEqual(
            info.graduation_year, self.initial_grad_year,
            "Graduation year was incorrectly modified by an unauthenticated user.",
        )

    # ------------------------------------------------------------------
    # Test 5: Invalid (non-numeric) graduation_year does not crash silently
    # and leaves the grade unchanged
    # ------------------------------------------------------------------

    def test_invalid_graduation_year_does_not_change_grade(self):
        """Passing a non-integer graduation_year should be silently ignored:
        the view returns 200 without crashing, and the graduation year in the
        DB remains unchanged."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(self.userview_base, data={
            'username': self.student.username,
            'graduation_year': 'not_a_number',
        })
        self.assertEqual(
            response.status_code, 200,
            "Expected 200 for invalid graduation_year input, got %s"
            % response.status_code,
        )

        info = self.student.getLastProfile().student_info
        self.assertEqual(
            info.graduation_year, self.initial_grad_year,
            "Graduation year was incorrectly modified on invalid input.",
        )

    # ------------------------------------------------------------------
    # Test 6: StudentInfo is recreated only for valid grade updates
    # ------------------------------------------------------------------

    def test_creates_student_info_when_missing(self):
        """If a student's most recent profile has no StudentInfo row, an admin
        grade update should recreate it and persist the new graduation year."""
        profile = self.student.getLastProfile()
        profile.student_info = None
        profile.save()

        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(self.userview_base, data={
            'username': self.student.username,
            'graduation_year': self.new_grad_year,
        })
        self.assertEqual(response.status_code, 200)

        updated_info = self.student.getLastProfile().student_info
        self.assertIsNotNone(updated_info)
        self.assertEqual(
            updated_info.graduation_year, self.new_grad_year,
            "Expected StudentInfo to be recreated and graduation year updated.",
        )

    def test_out_of_range_graduation_year_does_not_change_grade(self):
        """Passing a graduation year outside configured grade options should be
        ignored safely, leaving the existing graduation year unchanged."""
        self.client.login(username=self.admin.username, password='password')

        for invalid_year in ('-100', '999999'):
            response = self.client.get(self.userview_base, data={
                'username': self.student.username,
                'graduation_year': invalid_year,
            })
            self.assertEqual(response.status_code, 200)

            info = self.student.getLastProfile().student_info
            self.assertEqual(
                info.graduation_year, self.initial_grad_year,
                "Graduation year changed unexpectedly for invalid input %s"
                % invalid_year,
            )

    def test_invalid_graduation_year_does_not_create_missing_student_info(self):
        """If StudentInfo is missing, invalid input must not recreate it."""
        profile = self.student.getLastProfile()
        profile.student_info = None
        profile.save()

        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(self.userview_base, data={
            'username': self.student.username,
            'graduation_year': 'not_a_number',
        })
        self.assertEqual(response.status_code, 200)

        profile.refresh_from_db()
        self.assertIsNone(
            profile.student_info,
            "StudentInfo should not be created for invalid graduation year input.",
        )

    # ------------------------------------------------------------------
    # Test 7: change_grade_form is present in template context
    # ------------------------------------------------------------------

    def test_change_grade_form_in_context(self):
        """A GET to userview without a graduation_year param should still
        include 'change_grade_form' in the template context so the UI can
        render the grade-change widget."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(self.userview_base, data={
            'username': self.student.username,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'change_grade_form', response.context,
            "'change_grade_form' was not found in the userview template context.",
        )

