from __future__ import absolute_import
from __future__ import division
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
from esp.accounting.models import CybersourcePostback, FinancialAidGrant, LineItemType, Transfer

from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.middleware.esperrormiddleware import ESPError_NoLog
from esp.program.tests import ProgramFrameworkTest
from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController

from decimal import Decimal
from django.conf import settings
from django.test import override_settings
from django.core import mail
from unittest import mock
import json
import unittest
import random
import re

class StudentRegTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        # Set up the program -- we want to be sure of these parameters
        kwargs.update( {
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 6, 'classes_per_teacher': 1, 'sections_per_class': 2,
            'num_rooms': 6, 'sibling_discount': 20,
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

        #   MIT: reduced lunch does not auto-approve; amount due unchanged
        form_settings = {
            'reduced_lunch': 'checked',
            'household_income': '12345',
            'extra_explaination': 'No',
            'student_prepare': '',
        }
        response = self.client.post('/learn/%s/finaid' % self.program.getUrlBase(), form_settings)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), program_cost)

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

    def test_payment_identifier_with_finaid(self):
        """ A student whose financial aid covers admission but not an extra
        item is charged only for the extra; the payment identifier must
        reconcile against that amount (MIT Splash 2026 T-shirt bug). """

        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(70, [('Shirt', 10, 1)], [])

        student = random.choice(self.students)
        iac = IndividualAccountingController(self.program, student)
        iac.ensure_required_transfers()
        iac.set_preference('Shirt', 1)
        iac.grant_full_financial_aid()
        self.assertEqual(iac.amount_due(), 10)

        identifier = iac.get_identifier()
        IndividualAccountingController.record_payment_from_identifier(
            identifier, Decimal('10.00'), 'txn-finaid')
        self.assertTrue(identifier.endswith(':0.00:70.00'), identifier)
        self.assertEqual(iac.amount_paid(), 10)
        self.assertEqual(iac.amount_due(), 0)
        self.assertFalse(iac.get_transfers().filter(
            line_item__for_payments=False, paid_in__isnull=True,
        ).exclude(line_item__text__in=iac.finaid_items).exists())

    def test_payment_identifier_legacy_format(self):
        """ Identifiers generated before the financial aid field was added
        (three fields) must still be accepted. """

        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(70, [('Shirt', 10, 1)], [])

        student = random.choice(self.students)
        iac = IndividualAccountingController(self.program, student)
        iac.ensure_required_transfers()
        iac.set_preference('Shirt', 1)

        identifier = iac.get_identifier()
        self.assertTrue(identifier.endswith(':0.00:0.00'), identifier)
        legacy = identifier.rsplit(':', 1)[0]
        IndividualAccountingController.record_payment_from_identifier(
            legacy, Decimal('80.00'), 'txn-legacy')
        self.assertEqual(iac.amount_due(), 0)

    def test_payment_identifier_partial_finaid_later_item(self):
        """ With a partial grant, an aid-covered item added after admission
        was already paid must reconcile against only the remaining aid. """

        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(70, [('Food', 10, 1)], [])
        LineItemType.objects.filter(text='Food', program=self.program).update(for_finaid=True)

        student = random.choice(self.students)
        iac = IndividualAccountingController(self.program, student)
        iac.ensure_required_transfers()
        iac.set_finaid_params(None, 50)

        #   First payment: admission only, half covered
        self.assertEqual(iac.amount_due(), 35)
        IndividualAccountingController.record_payment_from_identifier(
            iac.get_identifier(), Decimal('35.00'), 'txn-1')
        self.assertEqual(iac.amount_due(), 0)

        #   Later add an aid-covered item; only its half of the aid is new
        iac.set_preference('Food', 1)
        self.assertEqual(iac.amount_due(), 5)
        IndividualAccountingController.record_payment_from_identifier(
            iac.get_identifier(), Decimal('5.00'), 'txn-2')
        self.assertEqual(iac.amount_due(), 0)

    def test_payment_identifier_rounding(self):
        """ A percentage grant that produces fractional cents is rounded to
        cents (half-up, in the student's favor), so the aid, amount due, and
        identifier all agree to the cent. """

        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(Decimal('15.50'), [], [])

        student = random.choice(self.students)
        iac = IndividualAccountingController(self.program, student)
        iac.ensure_required_transfers()
        iac.set_finaid_params(None, 33)
        self.assertEqual(iac.amount_finaid(), Decimal('5.12'))  # 33% of 15.50 = 5.115
        self.assertEqual(iac.amount_due(), Decimal('10.38'))

        IndividualAccountingController.record_payment_from_identifier(
            iac.get_identifier(), Decimal('10.38'), 'txn-round')
        self.assertEqual(iac.amount_due(), 0)

    def _post_cybersource(self, data):
        #   submit_transaction commits the raw postback log before processing,
        #   which is forbidden inside the TestCase transaction; skip that step.
        with mock.patch('esp.program.views.transaction.commit'):
            return self.client.post('/manage/submit_transaction/', data)

    def _post_cybersource_accept(self, identifier, amount, transaction_id):
        return self._post_cybersource({
            'decision': 'ACCEPT',
            'reason_code': '100',
            'req_merchant_defined_data1': identifier,
            'req_amount': amount,
            'transaction_id': transaction_id,
        })

    def test_cybersource_overpayment_notifies_treasury(self):
        """ If aid is granted while the student is on the payment page, the
        payment is still recorded and treasury is asked to refund the
        difference. """

        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(70, [('Shirt', 10, 1)], [])

        student = random.choice(self.students)
        iac = IndividualAccountingController(self.program, student)
        iac.ensure_required_transfers()
        iac.set_preference('Shirt', 1)

        #   Form loaded at $80, then aid granted before the payment arrives
        identifier = iac.get_identifier()
        iac.grant_full_financial_aid()
        mail.outbox = []
        response = self._post_cybersource_accept(identifier, '80.00', 'txn-over')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(iac.amount_paid(), 80)
        self.assertEqual(iac.amount_due(), -70)
        treasury = [m for m in mail.outbox if m.subject.startswith('[ESP CC] Overpayment')]
        self.assertEqual(len(treasury), 1)
        self.assertIn('$70.00', treasury[0].subject)
        self.assertEqual(treasury[0].to, [settings.DEFAULT_EMAIL_ADDRESSES['treasury']])
        self.assertIn('txn-over', treasury[0].body)

    def test_cybersource_exact_payment_no_notification(self):
        """ A normal payment (here, the full-aid + extra case) sends no
        overpayment notification. """

        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(70, [('Shirt', 10, 1)], [])

        student = random.choice(self.students)
        iac = IndividualAccountingController(self.program, student)
        iac.ensure_required_transfers()
        iac.set_preference('Shirt', 1)
        iac.grant_full_financial_aid()

        mail.outbox = []
        response = self._post_cybersource_accept(iac.get_identifier(), '10.00', 'txn-exact')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(iac.amount_due(), 0)
        self.assertFalse([m for m in mail.outbox if m.subject.startswith('[ESP CC]')])

    def test_finaid_approve_records_grant_amount(self):
        """ Approving a request stores the actual aid amount on the grant's
        transfer (it used to be computed before the grant was saved, so it
        was always $0.00), and re-finalizing updates it rather than adding a
        duplicate. """

        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(70, [('Shirt', 10, 1)], [])

        student = random.choice(self.students)
        iac = IndividualAccountingController(self.program, student)
        iac.ensure_required_transfers()
        iac.set_preference('Shirt', 1)

        request = FinancialAidRequest.objects.create(user=student, program=self.program)
        request.approve()
        grant_transfers = Transfer.objects.filter(user=student, line_item=iac.default_finaid_lineitemtype())
        self.assertEqual([t.amount_dec for t in grant_transfers], [Decimal('70.00')])

        grant = FinancialAidGrant.objects.get(request=request)
        grant.finalized = False
        grant.percent = 50
        grant.finalize()
        self.assertEqual([t.amount_dec for t in grant_transfers.all()], [Decimal('35.00')])

    def test_viewpay_shows_finaid(self):
        """ The admin credit card view lists financial aid as a credit,
        computed live so it reflects changes made after approval. """

        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(70, [('Shirt', 10, 1), ('Food', 7, 1)], [])
        LineItemType.objects.filter(text='Food', program=self.program).update(for_finaid=True)

        student = random.choice(self.students)
        iac = IndividualAccountingController(self.program, student)
        iac.ensure_required_transfers()
        iac.set_preference('Shirt', 1)
        #   viewpay lists students who are registered for a class
        self.program.sections()[0].preregister_student(student)
        FinancialAidRequest.objects.create(user=student, program=self.program).approve()

        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'))
        response = self.client.get('/manage/%s/viewpay' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '-$70.00 - Financial aid (100% grant)')
        self.assertContains(response, '$10.00 - Shirt')
        self.assertContains(response, '$80.00 billed; $10.00 owed')

        #   An aid-covered item added after approval is reflected immediately
        iac.set_preference('Food', 1)
        response = self.client.get('/manage/%s/viewpay' % self.program.getUrlBase())
        self.assertContains(response, '-$77.00 - Financial aid (100% grant)')
        self.assertContains(response, '$87.00 billed; $10.00 owed')

    def test_finaid_grant_terms(self):
        """ Short grant descriptions, with $0.00 / 0% treated as not set. """
        cases = [
            ((None, 100), '100%'),
            ((Decimal('0.00'), 100), '100%'),
            ((Decimal('40.00'), 100), '100%'),
            ((None, 50), '50%'),
            ((Decimal('40.00'), None), 'up to $40.00'),
            ((Decimal('40.00'), 0), 'up to $40.00'),
            ((Decimal('40.00'), 50), 'up to $40.00 + 50%'),
            ((Decimal('0.00'), 0), 'nothing'),
        ]
        for (amount, percent), expected in cases:
            grant = FinancialAidGrant(amount_max_dec=amount, percent=percent)
            self.assertEqual(grant.terms, expected, (amount, percent))

    def _setup_shirt_program(self, shirt_max=1):
        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(70, [('Shirt', 10, shirt_max)], [])
        student = random.choice(self.students)
        iac = IndividualAccountingController(self.program, student)
        iac.ensure_required_transfers()
        return iac

    def _treasury_mail(self, prefix):
        return [m for m in mail.outbox if m.subject.startswith(prefix)]

    def test_cybersource_unmatched_payment_is_still_recorded(self):
        """ If a payment can't be matched to items (here, the student removed
        an item while paying), the payment is still recorded, flagged for
        review, and treasury is told; the student is told not to pay again. """
        iac = self._setup_shirt_program()
        iac.set_preference('Shirt', 1)
        identifier = iac.get_identifier()
        iac.set_preference('Shirt', 0)

        mail.outbox = []
        response = self._post_cybersource_accept(identifier, '80.00', 'txn-unmatched')
        self.assertEqual(response.status_code, 302)
        self.assertIn('result=received_review', response['Location'])
        self.assertEqual(iac.amount_paid(), 80)
        postback = CybersourcePostback.objects.get(transaction_id='txn-unmatched')
        self.assertEqual(postback.status, 'needs_review')
        self.assertEqual((postback.user, postback.program), (iac.user, self.program))
        self.assertEqual(postback.transfer.amount_dec, 80)
        self.assertIn('no longer has this item', postback.status_detail)
        self.assertEqual(len(self._treasury_mail('[ESP CC] Payment needs manual review')), 1)
        #   Nothing was marked paid, since matching failed
        self.assertFalse(Transfer.objects.filter(paid_in=postback.transfer).exists())

    def test_cybersource_second_payment_is_recorded_for_review(self):
        """ Paying twice (e.g. from two tabs) records both payments; the
        second is flagged for review, leaving the student overpaid. """
        iac = self._setup_shirt_program()
        identifier = iac.get_identifier()
        self._post_cybersource_accept(identifier, '70.00', 'txn-first')
        mail.outbox = []
        response = self._post_cybersource_accept(identifier, '70.00', 'txn-second')
        self.assertIn('result=received_review', response['Location'])
        self.assertEqual(iac.amount_paid(), 140)
        self.assertEqual(iac.amount_due(), -70)
        self.assertEqual(CybersourcePostback.objects.get(transaction_id='txn-first').status, 'processed')
        self.assertEqual(CybersourcePostback.objects.get(transaction_id='txn-second').status, 'needs_review')
        self.assertEqual(len(self._treasury_mail('[ESP CC] Payment needs manual review')), 1)

    def test_cybersource_repeated_postback_not_double_recorded(self):
        """ The same postback arriving twice (e.g. a refresh) records one
        payment. """
        iac = self._setup_shirt_program()
        identifier = iac.get_identifier()
        self._post_cybersource_accept(identifier, '70.00', 'txn-repeat')
        response = self._post_cybersource_accept(identifier, '70.00', 'txn-repeat')
        self.assertIn('result=success', response['Location'])
        self.assertEqual(iac.amount_paid(), 70)
        self.assertEqual(Transfer.objects.filter(transaction_id='txn-repeat').count(), 1)
        self.assertEqual(
            list(CybersourcePostback.objects.filter(transaction_id='txn-repeat').values_list('status', flat=True)),
            ['processed', 'processed'])

    def test_cybersource_quantity_more_than_one(self):
        """ An item bought in a quantity above one reconciles (each unit is
        its own transfer). """
        iac = self._setup_shirt_program(shirt_max=3)
        iac.set_preference('Shirt', 2)
        response = self._post_cybersource_accept(iac.get_identifier(), '90.00', 'txn-qty')
        self.assertIn('result=success', response['Location'])
        self.assertEqual(iac.amount_due(), 0)
        self.assertEqual(Transfer.objects.filter(line_item__text='Shirt', paid_in__isnull=False).count(), 2)

    def test_cybersource_non_accept_decisions(self):
        """ Every non-ACCEPT decision is handled without an error, records no
        payment, and tells the student what happened. """
        iac = self._setup_shirt_program()
        identifier = iac.get_identifier()
        cases = [
            # decision, reason, expected result, expected status, emails treasury
            ('DECLINE', '203', 'declined', 'not_paid', False),
            ('REVIEW', '201', 'bank_verify', 'not_paid', False),
            ('REVIEW', '480', 'under_review', 'review_hold', True),
            ('ERROR', '104', 'possible_duplicate', 'not_paid', False),
            ('ERROR', '150', 'error', 'not_paid', False),
            ('CANCEL', '', 'cancelled', 'not_paid', False),
            ('SOMETHING_NEW', '999', 'error', 'failed', True),
        ]
        for i, (decision, reason, result, status, emails) in enumerate(cases):
            mail.outbox = []
            txn = 'txn-decision-%d' % i
            response = self._post_cybersource({
                'decision': decision, 'reason_code': reason,
                'req_merchant_defined_data1': identifier,
                'req_amount': '70.00', 'transaction_id': txn,
            })
            self.assertEqual(response.status_code, 302, decision)
            self.assertIn('result=%s' % result, response['Location'], decision)
            postback = CybersourcePostback.objects.get(transaction_id=txn)
            self.assertEqual(postback.status, status, decision)
            self.assertEqual((postback.user, postback.program), (iac.user, self.program), decision)
            self.assertEqual(bool(self._treasury_mail('[ESP CC]')), emails, decision)
        self.assertEqual(iac.amount_paid(), 0)

    def test_cybersource_unusable_identifier(self):
        """ An accepted payment we can't attribute to anyone is flagged as
        failed and reported to treasury, and the student is told not to pay
        again. """
        mail.outbox = []
        response = self._post_cybersource_accept('garbage', '70.00', 'txn-garbage')
        self.assertContains(response, 'Please do not pay again', status_code=response.status_code)
        postback = CybersourcePostback.objects.get(transaction_id='txn-garbage')
        self.assertEqual(postback.status, 'failed')
        self.assertEqual((postback.user, postback.program), (None, None))
        self.assertEqual(len(self._treasury_mail('[ESP CC] Failed to process')), 1)
        self.assertFalse(Transfer.objects.filter(transaction_id='txn-garbage').exists())

    def _approval_email_body(self, iac, **approve_kwargs):
        mail.outbox = []
        FinancialAidRequest.objects.create(user=iac.user, program=self.program).approve(**approve_kwargs)
        sent = [m for m in mail.outbox if m.subject.startswith('Financial Aid Approved')]
        self.assertEqual(len(sent), 1)
        body = sent[0].body
        #   Compare from the grant description up to the closing lines
        return body[body.index('\n\n', body.index('was approved on')) + 2:body.index('Questions?')]

    def test_finaid_approval_email_full_grant(self):
        """ Splash 2026 shape: full aid for admission, an uncovered optional
        extra that the student selected. """
        iac = self._setup_shirt_program()
        LineItemType.objects.filter(text='Shirt', program=self.program).update(text="Kids' Shirt")
        iac.set_preference("Kids' Shirt", 1)
        body = self._approval_email_body(iac)
        self.assertTrue(body.startswith(
            "Your grant covers the full cost of:\n"
            "  - Program admission ($70.00)\n"
            "\n"
            "Based on what you've selected so far, that's $70.00 off.\n"
            "\n"
            "Not covered by financial aid:\n"
            "  - Kids' Shirt ($10.00, optional) - selected\n"
            "You're only charged for optional items you select.\n"
            "\n"
            "Your current balance is $10.00. You can pay online at: https://"), body)

    def test_finaid_approval_email_partial_grant_many_items(self):
        """ Percentage grant covering several kinds of items, selected and
        not: priced per unit, with options, and not chosen. """
        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(70, [('Food', 5, 3), ('Bus pass', 15, 1), ('Shirt', 10, 1)],
                                [('Lunch', [('Small', 3), ('Large', 7)])])
        LineItemType.objects.filter(program=self.program, text__in=['Food', 'Bus pass', 'Lunch']).update(for_finaid=True)
        iac = IndividualAccountingController(self.program, random.choice(self.students))
        iac.ensure_required_transfers()
        iac.set_preference('Food', 2)
        lunch = LineItemType.objects.get(program=self.program, text='Lunch')
        large = [x for x in lunch.options if x[2] == 'Large'][0]
        iac.set_preference('Lunch', 1, option_id=large[0])
        body = self._approval_email_body(iac, discount_percent=50)
        self.assertEqual(body,
            "Your grant covers 50%% of the cost of:\n"
            "  - Bus pass ($15.00, optional) - not selected\n"
            "  - Food ($5.00 each, optional) - you've selected 2 for $10.00\n"
            "  - Lunch ($3.00 to $7.00, optional) - selected, $7.00\n"
            "  - Program admission ($70.00)\n"
            "\n"
            "Based on what you've selected so far, that's $43.50 off.\n"
            "\n"
            "Not covered by financial aid:\n"
            "  - Shirt ($10.00, optional) - not selected\n"
            "You're only charged for optional items you select.\n"
            "\n"
            "Your current balance is $43.50. You can pay online at: "
            "https://%s/learn/%s/cybersource\n"
            "\n" % (settings.DEFAULT_HOST, self.program.getUrlBase()))

    def test_finaid_approval_email_dollars_plus_percent(self):
        iac = self._setup_shirt_program()
        body = self._approval_email_body(iac, dollar_amount=Decimal('40.00'), discount_percent=50)
        self.assertTrue(body.startswith(
            "Your grant covers up to $40.00 of the cost of the items below, plus 50% of whatever remains:\n"
            "  - Program admission ($70.00)\n"
            "\n"
            "Based on what you've selected so far, that's $55.00 off.\n"), body)
        self.assertIn("Your current balance is $15.00.", body)

    def test_finaid_approval_email_nothing_covered(self):
        iac = self._setup_shirt_program()
        LineItemType.objects.filter(program=self.program).update(for_finaid=False)
        body = self._approval_email_body(iac)
        self.assertTrue(body.startswith("Your grant doesn't currently apply to any costs for this program."), body)
        self.assertIn("Costs for this program:\n  - Program admission ($70.00)\n", body)
        self.assertNotIn("Not covered by financial aid", body)
        self.assertIn("Your current balance is $70.00.", body)

    def test_finaid_approval_email_nothing_owed(self):
        """ With nothing owed, the email still warns that uncovered optional
        items would cost extra. """
        iac = self._setup_shirt_program()
        body = self._approval_email_body(iac)
        self.assertIn("  - Shirt ($10.00, optional) - not selected\n", body)
        self.assertIn(
            "You don't owe anything for %s right now. If you select any optional items "
            "not covered by financial aid, you'll need to pay for those.\n" % self.program.niceName(), body)

    @override_settings(CYBERSOURCE_CONFIG={'post_url': 'https://pay.example.com/', 'merchant_id': 'test_merchant'})
    def test_cybersource_checkout_rechecks_amount(self):
        """ Continuing to payment re-checks the amount due: forward to the
        processor only if it still matches what the student was shown. """
        iac = self._setup_shirt_program()
        self.assertTrue(self.client.login(username=iac.user.username, password='password'))
        payment_page = '/learn/%s/cybersource' % self.program.getUrlBase()
        checkout = '/learn/%s/cybersource_checkout' % self.program.getUrlBase()

        #   The payment page sends the shown amount to the re-check step
        response = self.client.get(payment_page)
        self.assertContains(response, 'action="%s"' % checkout)
        self.assertContains(response, 'name="expected_amount" value="70.00"')

        #   Same amount: forward to the processor with a fresh identifier
        iac.set_preference('Shirt', 1)
        response = self.client.post(checkout, {'expected_amount': '80.00'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'action="https://pay.example.com/"')
        self.assertContains(response, 'name="amount" value="80.00"')
        self.assertContains(response, 'name="merchantDefinedData1" value="%s"' % iac.get_identifier())

        #   Different amount (e.g. the page was opened before adding the shirt)
        response = self.client.post(checkout, {'expected_amount': '70.00'})
        self.assertRedirects(response, payment_page + '?result=balance_changed', fetch_redirect_response=False)

        #   Nothing owed (e.g. already paid in another tab): don't send them
        iac.grant_full_financial_aid()
        iac.set_preference('Shirt', 0)
        response = self.client.post(checkout, {'expected_amount': '70.00'})
        self.assertRedirects(response, payment_page, fetch_redirect_response=False)

        #   Visiting the step directly just goes back to the payment page
        response = self.client.get(checkout)
        self.assertRedirects(response, payment_page, fetch_redirect_response=False)

    def test_finaid_approval_email_string_inputs(self):
        """ The approval page passes the grant amounts as strings; a $0 cap
        with 100% must still read as covering the full cost. """
        iac = self._setup_shirt_program()
        body = self._approval_email_body(iac, dollar_amount='0', discount_percent='100')
        self.assertTrue(body.startswith("Your grant covers the full cost of:\n"), body)

    def test_finaid_approval_page_blank_amounts(self):
        """ On the approval page, a blank dollar amount means $0 (so 100%
        still reads as the full cost); with both blank nothing is granted. """
        iac = self._setup_shirt_program()
        request = FinancialAidRequest.objects.create(user=iac.user, program=self.program,
                                                     extra_explaination='Please')
        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'))
        url = '/manage/%s/finaidapprove' % self.program.getUrlBase()

        response = self.client.post(url, {'user': [str(iac.user.id)], 'amount_max_dec': '', 'percent': ''})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FinancialAidGrant.objects.filter(request=request).exists())

        mail.outbox = []
        response = self.client.post(url, {'user': [str(iac.user.id)], 'amount_max_dec': '', 'percent': '100'})
        self.assertEqual(response.status_code, 200)
        grant = FinancialAidGrant.objects.get(request=request)
        self.assertEqual((grant.amount_max_dec, grant.percent), (Decimal('0.00'), 100))
        sent = [m for m in mail.outbox if m.subject.startswith('Financial Aid Approved')]
        self.assertEqual(len(sent), 1)
        self.assertIn("Your grant covers the full cost of:\n", sent[0].body)

    def test_finaid_approved_after_payment_notices_disabled(self):
        """ While the refund notices are disabled, a student who paid before
        their aid was approved gets the ordinary approval email, and treasury
        isn't emailed. Remove this test when enabling them. """
        iac = self._setup_shirt_program()
        iac.set_preference('Shirt', 1)
        iac.submit_payment(Decimal('80.00'), 'txn-before-aid')
        body = self._approval_email_body(iac)
        self.assertEqual(iac.amount_due(), -70)
        self.assertNotIn('refund', body)
        self.assertNotIn('DISABLED', body)
        self.assertEqual(self._treasury_mail('[ESP CC]'), [])

    @unittest.skip('refund notices are disabled pending review; see FinancialAidRequest.approve()')
    def test_finaid_approved_after_payment(self):
        """ A student who paid before their aid was approved is told what
        refund they can ask for, and treasury is told for information. """
        iac = self._setup_shirt_program()
        iac.set_preference('Shirt', 1)
        iac.submit_payment(Decimal('80.00'), 'txn-before-aid')
        request = FinancialAidRequest.objects.create(user=iac.user, program=self.program)
        refund_text = (
            "You don't owe anything for %s right now. If you select any optional items "
            "not covered by financial aid, you'll need to pay for those.\n"
            "\n"
            "You already paid $80.00 before your financial aid was approved, so you're now "
            "eligible for a refund of $70.00. If you would like us to process a refund, "
            "please send us an email at %s.\n"
            "\n"
            "Questions?" % (self.program.niceName(), self.program.director_email))

        #   The preview shows the refund, and emails nobody
        mail.outbox = []
        self.assertIn(refund_text, request.preview_approval_email()['body'])
        self.assertEqual(mail.outbox, [])

        request.approve()
        self.assertEqual(iac.amount_due(), -70)
        sent = [m for m in mail.outbox if m.subject.startswith('Financial Aid Approved')]
        self.assertEqual(len(sent), 1)
        self.assertIn(refund_text, sent[0].body)
        treasury = self._treasury_mail('[ESP CC] FYI: financial aid approved after payment')
        self.assertEqual(len(treasury), 1)
        self.assertEqual(treasury[0].to, [settings.DEFAULT_EMAIL_ADDRESSES['treasury']])
        self.assertIn(iac.user.username, treasury[0].body)
        self.assertIn('after already paying $80.00, so they have now paid $70.00 more than they owe', treasury[0].body)
        self.assertIn('No action is needed right now.', treasury[0].body)
        self.assertIn(self.program.director_email, treasury[0].body)

    def test_finaid_approved_after_payment_nothing_to_refund(self):
        """ No refund is mentioned, and treasury isn't emailed, when the
        student hasn't paid. """
        iac = self._setup_shirt_program()
        body = self._approval_email_body(iac)
        self.assertNotIn('refund', body)
        self.assertEqual(self._treasury_mail('[ESP CC]'), [])

    def test_finaid_approved_after_exact_payment(self):
        """ Paid for the shirt only; full aid then covers admission exactly,
        so there's nothing to refund. """
        iac = self._setup_shirt_program()
        iac.set_preference('Shirt', 1)
        iac.submit_payment(Decimal('10.00'), 'txn-shirt-only', link_transfers=False)
        body = self._approval_email_body(iac)
        self.assertEqual(iac.amount_due(), 0)
        self.assertNotIn('refund', body)
        self.assertIn("You don't owe anything for %s right now." % self.program.niceName(), body)
        self.assertEqual(self._treasury_mail('[ESP CC]'), [])

    def test_finaid_approval_email_preview(self):
        """ The preview is the email approve() then sends, and saves nothing. """
        iac = self._setup_shirt_program()
        iac.set_preference('Shirt', 1)
        request = FinancialAidRequest.objects.create(user=iac.user, program=self.program)
        transfers = list(Transfer.objects.filter(user=iac.user).values_list('id', 'amount_dec'))

        preview = request.preview_approval_email(dollar_amount=Decimal('40.00'), discount_percent=50)
        self.assertIn("Your grant covers up to $40.00", preview['body'])
        self.assertIn("Your current balance is $25.00.", preview['body'])
        self.assertFalse(FinancialAidGrant.objects.filter(request=request).exists())
        self.assertEqual(list(Transfer.objects.filter(user=iac.user).values_list('id', 'amount_dec')), transfers)
        request.refresh_from_db()
        self.assertFalse(request.done)
        self.assertEqual(iac.amount_due(), 80)

        mail.outbox = []
        request.approve(dollar_amount=Decimal('40.00'), discount_percent=50)
        sent = [m for m in mail.outbox if m.subject.startswith('Financial Aid Approved')]
        self.assertEqual(len(sent), 1)
        self.assertEqual((sent[0].subject, sent[0].to), (preview['subject'], preview['to']))
        #   Identical apart from the approval time, which can tick over
        strip_time = lambda body: body[body.index('\n\n', body.index('was approved on')):]
        self.assertEqual(strip_time(sent[0].body), strip_time(preview['body']))
        with self.assertRaises(ESPError_NoLog):
            request.preview_approval_email()

    def test_finaid_approval_page_preview(self):
        """ The approval page's preview endpoint reports who would be approved
        or skipped, and picks whose email to show by criteria or by choice. """
        self._setup_shirt_program()
        (paid, unpaid, blank, approved) = self.students[:4]
        for student in [paid, unpaid, approved]:
            FinancialAidRequest.objects.create(user=student, program=self.program, extra_explaination='Please')
        FinancialAidRequest.objects.create(user=blank, program=self.program)
        FinancialAidRequest.objects.get(user=approved, program=self.program).approve()
        IndividualAccountingController(self.program, paid).submit_payment(Decimal('70.00'))
        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'))
        url = '/manage/%s/finaidapprovepreview' % self.program.getUrlBase()
        all_users = [str(s.id) for s in [paid, unpaid, blank, approved]]

        def preview(**extra):
            data = {'user': all_users, 'amount_max_dec': '0', 'percent': '100'}
            data.update(extra)
            mail.outbox = []
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mail.outbox, [])
            return json.loads(response.content.decode('utf-8'))

        result = preview()
        #   Page order is newest request first
        self.assertEqual([s['id'] for s in result['to_approve']], [unpaid.id, paid.id])
        self.assertEqual((result['already_approved'], result['blank']), ([approved.name()], [blank.name()]))
        self.assertEqual(result['already_paid'], ['%s ($70.00)' % paid.name()])
        self.assertEqual(result['student']['id'], unpaid.id)
        self.assertIn("Your grant covers the full cost of:\n", result['email']['body'])

        self.assertEqual(preview(payment='paid')['student']['id'], paid.id)
        self.assertEqual(preview(payment='unpaid')['student']['id'], unpaid.id)
        self.assertEqual(preview(preview_user=str(paid.id))['student']['id'], paid.id)
        self.assertIsNone(preview(extracosts='yes')['email'])
        result = preview(approve_blanks='on')
        self.assertEqual([s['id'] for s in result['to_approve']], [blank.id, unpaid.id, paid.id])
        result = preview(amount_max_dec='', percent='')
        self.assertIsNone(result['email'])
        self.assertTrue(result['error'])
        result = preview(percent='lots')
        self.assertIsNone(result['email'])
        self.assertEqual(result['error'], 'The dollar amount and percent must be numbers.')
        self.assertFalse(FinancialAidGrant.objects.filter(request__user__in=[paid, unpaid, blank]).exists())

    def test_finaid_approval_survives_email_failure(self):
        """ If the approval email can't be built or sent, the grant stays
        approved and approve() doesn't raise. """
        iac = self._setup_shirt_program()
        request = FinancialAidRequest.objects.create(user=iac.user, program=self.program)
        with mock.patch('esp.program.models.render_to_string', side_effect=Exception('boom')):
            request.approve()
        request.refresh_from_db()
        self.assertTrue(request.done)
        self.assertTrue(request.approved)
        self.assertEqual(iac.amount_due(), 0)

    def test_finaid_approval_email_option_prices(self):
        """ An item whose options all cost the same (e.g. shirt sizes) shows
        that price; options with different prices show a range. """
        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(70, [], [('Shirt', [('Small', 10), ('Large', 10)])])
        iac = IndividualAccountingController(self.program, random.choice(self.students))
        iac.ensure_required_transfers()
        shirt = LineItemType.objects.get(program=self.program, text='Shirt')
        shirt.lineitemoptions_set.update(amount_dec=None)   # sizes inherit the shirt's price
        LineItemType.objects.filter(id=shirt.id).update(amount_dec=10)
        body = self._approval_email_body(iac)
        self.assertIn("  - Shirt ($10.00, optional) - not selected\n", body)

    def test_options_cost_range(self):
        """ The range covers each option's real price (inheriting the item's
        amount when unset) and leaves out custom-amount options. """
        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(70, [], [('Lunch', [('Small', 3), ('Large', 7), ('Medium', 5)])])
        lunch = LineItemType.objects.get(program=self.program, text='Lunch')
        self.assertEqual(lunch.options_cost_range, (Decimal('3'), Decimal('7')))

        #   An option with no amount of its own inherits the item's amount
        LineItemType.objects.filter(id=lunch.id).update(amount_dec=Decimal('9'))
        lunch.lineitemoptions_set.filter(description='Medium').update(amount_dec=None)
        lunch = LineItemType.objects.get(id=lunch.id)
        self.assertEqual(lunch.options_cost_range, (Decimal('3'), Decimal('9')))

        #   Custom-amount options are left out
        lunch.lineitemoptions_set.filter(description='Large').update(is_custom=True)
        self.assertEqual(lunch.options_cost_range, (Decimal('3'), Decimal('9')))
        lunch.lineitemoptions_set.update(is_custom=True)
        self.assertIsNone(lunch.options_cost_range)
