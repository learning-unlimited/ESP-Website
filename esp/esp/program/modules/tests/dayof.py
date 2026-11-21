""" Tests for day-of operations: who recorded something,
and check-ins recording the cash/check payment they imply. """
from __future__ import absolute_import

import importlib
import json
import os
import random
from decimal import Decimal

from unittest import mock

from django.apps import apps as django_apps
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from datetime import timedelta

from esp.accounting.controllers import IndividualAccountingController, ProgramAccountingController
from esp.accounting.models import (CybersourcePostback, DayOfCardCheckout, HelpdeskPriceChange, OnsiteSale,
                                   Receipt, Transfer)
from esp.program.controllers import dayof, dayof_payments, printing
from esp.utils import print_server
from esp.program.models import FinancialAidRequest
from esp.program.modules.handlers.creditcardmodule_cybersource import CreditCardModule_Cybersource
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, Record, RecordType


class DayOfTestBase(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super(DayOfTestBase, self).setUp(*args, **kwargs)
        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(70, [('Shirt', 10, 1)], [])
        self.student = random.choice(self.students)
        self.iac = IndividualAccountingController(self.program, self.student)
        self.iac.ensure_required_transfers()
        self.iac.set_preference('Shirt', 1)
        self.admin = self.admins[0]
        self.onsite, _ = ESPUser.objects.get_or_create(username='onsite')
        self.onsite.set_password('password')
        self.onsite.save()
        self.onsite.makeRole('Administrator')

    def checkin_payments(self):
        return Transfer.objects.filter(user=self.student, line_item__for_payments=True,
                                       checkin_record__isnull=False)

    def onsite_url(self, view):
        return '/onsite/%s/%s' % (self.program.getUrlBase(), view)


class CheckInStudentTest(DayOfTestBase):
    def test_records_balance_as_cash_check(self):
        (record, payment) = dayof.check_in_student(self.program, self.student, self.admin)
        self.assertIsNotNone(record)
        self.assertEqual(payment.amount_dec, Decimal('80.00'))
        self.assertEqual(payment.payment_method, 'cash_check')
        self.assertEqual(payment.checkin_record, record)
        self.assertEqual(payment.recorded_by, self.admin)
        self.assertEqual(self.iac.amount_due(), 0)
        self.assertTrue(self.program.isCheckedIn(self.student))
        #   The items it paid for are marked paid by it
        self.assertFalse(self.iac.get_transfers().filter(
            line_item__for_payments=False, paid_in__isnull=True).exclude(
            line_item__text__in=self.iac.finaid_items).exists())

    def test_no_payment_when_nothing_owed(self):
        self.iac.submit_payment(Decimal('80.00'), 'txn-prepaid')
        (record, payment) = dayof.check_in_student(self.program, self.student, self.admin)
        self.assertIsNotNone(record)
        self.assertIsNone(payment)

    def test_aid_covers_fee_shirt_still_owed(self):
        """ Aid covering the program fee but not the shirt: they paid $10. """
        request = FinancialAidRequest.objects.create(user=self.student, program=self.program)
        request.approve(dollar_amount=None, discount_percent=100)
        (record, payment) = dayof.check_in_student(self.program, self.student, self.admin)
        self.assertEqual(payment.amount_dec, Decimal('10.00'))
        self.assertEqual(self.iac.amount_due(), 0)

    def test_already_checked_in(self):
        dayof.check_in_student(self.program, self.student, self.admin)
        (record, payment) = dayof.check_in_student(self.program, self.student, self.admin)
        self.assertIsNone(record)
        self.assertIsNone(payment)
        self.assertEqual(self.checkin_payments().count(), 1)

    def test_recheck_in_after_checkout_records_nothing(self):
        dayof.check_in_student(self.program, self.student, self.admin)
        Record.objects.create(user=self.student, program=self.program,
                              event=RecordType.objects.get(name='checked_out'))
        self.iac.set_preference('Shirt', 0)
        self.iac.set_preference('Shirt', 1)     # an unpaid item after check-in
        (record, payment) = dayof.check_in_student(self.program, self.student, self.admin)
        self.assertIsNotNone(record)
        self.assertIsNone(payment)
        self.assertEqual(self.checkin_payments().count(), 1)

    def test_undo_deletes_payment_and_unmarks_items(self):
        (record, payment) = dayof.check_in_student(self.program, self.student, self.admin)
        dayof.undo_check_in(record)
        self.assertFalse(Record.objects.filter(id=record.id).exists())
        self.assertFalse(Transfer.objects.filter(id=payment.id).exists())
        self.assertFalse(Transfer.objects.filter(paid_in=payment.id).exists())
        self.assertEqual(self.iac.amount_due(), Decimal('80.00'))
        self.assertFalse(self.program.isCheckedIn(self.student))

    def test_card_students_exclude_cash_payers(self):
        dayof.check_in_student(self.program, self.student, self.admin)
        module = CreditCardModule_Cybersource()
        module.program = self.program
        self.assertNotIn(self.student, module.students()['creditcard'])
        other = [s for s in self.students if s != self.student][0]
        IndividualAccountingController(self.program, other).submit_payment(Decimal('5.00'), 'txn-card', link_transfers=False)
        self.assertIn(other, module.students()['creditcard'])


class RecorderTest(DayOfTestBase):
    def _request(self, user, morph_from=None):
        request = RequestFactory().post('/')
        request.user = user
        request.session = {}
        if morph_from is not None:
            request.session['user_morph'] = {'olduser_id': morph_from.id, 'onsite': False}
        return request

    def test_real_user_is_the_account_behind_the_request(self):
        self.assertEqual(dayof.real_user(self._request(self.admin)), self.admin)
        self.assertEqual(dayof.real_user(self._request(self.onsite)), self.onsite)

    def test_morphed_admin_is_recorded_as_admin(self):
        self.assertEqual(dayof.real_user(self._request(self.onsite, morph_from=self.admin)), self.admin)


class CheckInViewsTest(DayOfTestBase):
    def test_ajax_barcode_checkin_records_payment(self):
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        response = self.client.post(self.onsite_url('ajaxbarcodecheckin'), {'code': self.student.id})
        message = json.loads(response.content.decode('utf-8'))['message']
        self.assertIn('Recorded $80.00 paid in cash/check', message)
        payment = self.checkin_payments().get()
        self.assertEqual(payment.recorded_by, self.admin)
        #   Scanning again says they're checked in, and what they still owe
        self.iac.set_preference('Shirt', 0)
        self.iac.set_preference('Shirt', 1)
        response = self.client.post(self.onsite_url('ajaxbarcodecheckin'), {'code': self.student.id})
        message = json.loads(response.content.decode('utf-8'))['message']
        self.assertIn('already checked in', message)

    def test_barcode_form_checkin(self):
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        self.client.post(self.onsite_url('barcodecheckin'), {'uids': str(self.student.id)})
        self.assertTrue(self.program.isCheckedIn(self.student))
        self.assertEqual(self.checkin_payments().get().amount_dec, Decimal('80.00'))

    def test_checkin_page_and_undo(self):
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        self.client.post(self.onsite_url('checkin'), {'userid': self.student.id, 'attended': 'on'})
        self.assertEqual(self.checkin_payments().count(), 1)
        self.client.post(self.onsite_url('checkin'), {'userid': self.student.id, 'attended': 'on',
                                                     'undocheckin': 'on'})
        self.assertFalse(self.checkin_payments().exists())
        self.assertFalse(Record.objects.filter(user=self.student, program=self.program,
                                               event__name='attended').exists())

    def test_grid_schedule_change_checkin(self):
        """ The class-change grid's "check in" option used to crash (it passed
        a string as the record type). """
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        data = {'user': self.student.id, 'sections': '[]', 'check_in': 'true'}
        #   Not by GET (anything could trigger that cross-site)
        self.assertEqual(self.client.get(self.onsite_url('update_schedule_json'), data).status_code, 405)
        self.assertEqual(self.client.get(self.onsite_url('printschedule_status'), data).status_code, 405)
        self.assertFalse(self.program.isCheckedIn(self.student))
        response = self.client.post(self.onsite_url('update_schedule_json'), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.program.isCheckedIn(self.student))
        self.assertEqual(self.checkin_payments().count(), 1)

    def test_grid_refuses_changes_for_students_not_checked_in(self):
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        section = self.program.sections()[0]
        data = {'user': self.student.id, 'sections': '[%d]' % section.id}
        response = self.client.post(self.onsite_url('update_schedule_json'), data).json()
        self.assertIn("isn't checked in", ' '.join(response['messages']))
        self.assertNotIn(section.id, response['sections'])
        self.assertFalse(self.program.isCheckedIn(self.student))
        self.assertFalse(self.checkin_payments().exists())
        #   The grid's "check in" box starts unticked
        self.assertNotContains(self.client.get(self.onsite_url('classchange_grid')), 'id="check_in_student" checked')

    def test_grid_print_checks_in_only_when_asked(self):
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        #   Nothing connected: refused before checking anyone in
        response = self.client.post(self.onsite_url('printschedule_status'),
                                   {'user': self.student.id, 'check_in': 'true'})
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('Nothing is printing', data['message'])
        self.assertNotIn('checked_in', data)       # so the grid keeps its "Check in & print" button
        self.assertFalse(self.program.isCheckedIn(self.student))
        printing.claim_for_laptop(printing.default_location(), self.admin)
        self.client.post(self.onsite_url('printschedule_status'), {'user': self.student.id})
        self.assertFalse(self.program.isCheckedIn(self.student))
        response = self.client.post(self.onsite_url('printschedule_status'),
                                   {'user': self.student.id, 'check_in': 'true'})
        self.assertTrue(self.program.isCheckedIn(self.student))
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('Recorded $80.00', data['message'])
        self.assertTrue(data['checked_in'])

    def test_grid_register_ties_payment_to_checkin(self):
        """ Registering a student from the class change grid checks them in
        like check-in does, so undoing the check-in removes the payment. """
        from esp.program.models import RegistrationProfile
        from esp.users.models import StudentInfo
        profile = RegistrationProfile.getLastForProgram(self.student, self.program)
        profile.student_info = StudentInfo.objects.create(user=self.student)
        profile.save()
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        self.client.post(self.onsite_url('register_student'), {'student_id': self.student.id})
        self.assertTrue(self.program.isCheckedIn(self.student))
        self.assertEqual(self.checkin_payments().get().amount_dec, Decimal('80.00'))
        dayof.undo_check_in(Record.objects.get(user=self.student, program=self.program, event__name='attended'))
        self.assertEqual(self.iac.amount_due(), Decimal('80.00'))


class BackfillPaymentMethodTest(DayOfTestBase):
    def test_old_payments_become_card(self):
        payment = self.iac.submit_payment(Decimal('80.00'), 'old', payment_method='cash_check')
        Transfer.objects.filter(id=payment.id).update(payment_method='')
        migration = importlib.import_module('esp.accounting.migrations.0022_backfill_payment_method')
        migration.backfill_payment_method(django_apps, None)
        payment.refresh_from_db()
        self.assertEqual(payment.payment_method, 'card')
        #   Non-payment transfers are left alone
        self.assertFalse(Transfer.objects.filter(user=self.student, line_item__for_payments=False)
                         .exclude(payment_method='').exists())


CYBERSOURCE = {'post_url': 'https://pay.example.com/', 'merchant_id': 'test_merchant'}


class TroubleshootingTest(DayOfTestBase):
    def setUp(self, *args, **kwargs):
        super(TroubleshootingTest, self).setUp(*args, **kwargs)
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))

    def page(self, view='troubleshooting'):
        return '%s?user=%d' % (self.onsite_url(view), self.student.id)

    def post(self, view, data):
        data = dict(data, user=self.student.id)
        data.setdefault('expected_balance', '%.2f' % self.iac.amount_due())
        return self.client.post(self.onsite_url(view), data)

    def test_pages_render(self):
        self.assertEqual(self.client.get(self.onsite_url('troubleshooting')).status_code, 200)
        response = self.client.get(self.page())
        self.assertContains(response, self.student.name())
        status = json.loads(self.client.get(self.page('troubleshooting_status')).content.decode('utf-8'))
        self.assertEqual(status['balance'], '80.00')
        response = self.client.get(self.onsite_url('troubleshooting'), {'userid': self.student.id, 'op': 'usersearch'})
        self.assertRedirects(response, self.page(), fetch_redirect_response=False)

    def test_finaid_grant(self):
        preview = json.loads(self.client.get(self.onsite_url('troubleshooting_finaid_preview'), {
            'user': self.student.id, 'amount_max': '0', 'percent': '100'}).content.decode('utf-8'))
        self.assertEqual((preview['before'], preview['after']), ('80.00', '10.00'))
        self.assertTrue(any('Shirt' in w for w in preview['warnings']))
        from django.core import mail
        mail.outbox = []
        self.post('troubleshooting_finaid', {'amount_max': '0.00', 'percent': '100', 'reason': 'Lost the form'})
        self.assertEqual(self.iac.amount_due(), Decimal('10.00'))
        grant = self.iac.latest_finaid_grant()
        self.assertEqual((grant.percent, grant.granted_by), (100, self.admin))
        self.assertIn('Lost the form', grant.request.extra_explaination)
        self.assertFalse([m for m in mail.outbox if 'Financial Aid' in m.subject])
        #   Changing it edits the same grant
        self.post('troubleshooting_finaid', {'amount_max': '35', 'percent': '0', 'reason': 'Half'})
        self.assertEqual(self.iac.amount_due(), Decimal('45.00'))
        self.assertEqual(FinancialAidRequest.objects.filter(user=self.student, program=self.program).count(), 1)

    def test_finaid_requires_reason_and_fresh_balance(self):
        self.post('troubleshooting_finaid', {'amount_max': '0', 'percent': '100', 'reason': ''})
        self.assertIsNone(self.iac.latest_finaid_grant())
        self.post('troubleshooting_finaid', {'amount_max': '0', 'percent': '100', 'reason': 'x',
                                             'expected_balance': '70.00'})
        self.assertIsNone(self.iac.latest_finaid_grant())

    def test_paid_less_at_checkin_and_money_owed(self):
        dayof.check_in_student(self.program, self.student, self.admin)
        self.post('troubleshooting_checkin_adjust', {'actually_paid': '50'})
        self.assertEqual(self.iac.amount_due(), Decimal('30.00'))
        self.assertEqual(self.checkin_payments().get().amount_dec, Decimal('50.00'))
        owed = dayof.owed_after_checkin(self.program)
        self.assertEqual([(r['student'], r['amount_due']) for r in owed], [(self.student, Decimal('30.00'))])
        self.assertContains(self.client.get(self.onsite_url('troubleshooting')), self.student.name())
        #   They bring the rest
        self.post('troubleshooting_record_payment', {'amount': '30.00'})
        self.assertEqual(self.iac.amount_due(), 0)
        self.assertEqual(dayof.owed_after_checkin(self.program), [])

    def test_record_payment_refuses_overpaying_unless_ticked(self):
        dayof.check_in_student(self.program, self.student, self.admin)
        #   Something added after check-in
        from esp.accounting.models import LineItemType
        LineItemType.objects.create(program=self.program, text='Lunch', amount_dec=Decimal('10'))
        self.iac.set_preference('Lunch', 1)
        self.post('troubleshooting_record_payment', {'amount': '20.00'})
        self.assertEqual(self.iac.amount_due(), Decimal('10.00'))
        self.post('troubleshooting_record_payment', {'amount': '20.00', 'overpay': '1'})
        self.assertEqual(self.iac.amount_due(), Decimal('-10.00'))

    def test_checkin_button(self):
        page = self.client.get(self.onsite_url('troubleshooting'), {'user': self.student.id})
        self.assertContains(page, 'troubleshooting_checkin')
        self.post('troubleshooting_checkin', {})
        self.assertTrue(self.program.isCheckedIn(self.student))
        #   As at check-in, their balance is recorded as paid in cash/check
        self.assertEqual(self.iac.amount_due(), 0)
        self.assertEqual(self.checkin_payments().get().amount_dec, Decimal('80.00'))
        page = self.client.get(self.onsite_url('troubleshooting'), {'user': self.student.id})
        self.assertNotContains(page, 'troubleshooting_checkin"')
        #   Nothing owed: a card payment can still be started (a custom amount)
        self.assertContains(page, 'id="card-form"')
        self.assertContains(page, 'data-channel="qr"')
        self.assertContains(page, '/admin/accounting/transfer/?user__id__exact=%d' % self.student.id)
        #   The admin lists accept those filters (rather than redirecting with ?e=1)
        ESPUser.objects.filter(id=self.admin.id).update(is_staff=True, is_superuser=True)
        self.assertEqual(self.client.get('/admin/accounting/transfer/', {
            'user__id__exact': self.student.id, 'line_item__program__id__exact': self.program.id}).status_code, 200)
        self.assertEqual(self.client.get('/admin/accounting/cybersourcepostback/', {
            'user__id__exact': self.student.id, 'program__id__exact': self.program.id}).status_code, 200)
        #   Undo: not checked in, and the payment check-in recorded is gone
        self.post('troubleshooting_undo_checkin', {})
        self.assertFalse(self.program.isCheckedIn(self.student))
        self.assertFalse(self.checkin_payments().exists())
        self.assertEqual(self.iac.amount_due(), Decimal('80.00'))

    def test_record_payment_any_amount_before_checkin(self):
        from esp.accounting.models import Transfer
        self.post('troubleshooting_record_payment', {'amount': '12.50', 'method': 'card', 'reference': 'TX 99'})
        self.assertEqual(self.iac.amount_due(), Decimal('67.50'))
        payment = Transfer.objects.get(user=self.student, amount_dec=Decimal('12.50'))
        self.assertEqual((payment.payment_method, payment.transaction_id, payment.recorded_by),
                         ('card', 'TX 99', self.admin))
        self.post('troubleshooting_record_payment', {'amount': '1', 'method': 'bitcoin'})
        self.assertEqual(self.iac.amount_due(), Decimal('67.50'))

    def _extracosts_post(self, shirt, **extra):
        shirt_item = self.iac.get_lineitemtypes().get(text='Shirt')
        data = {'expected_balance': '%.2f' % self.iac.amount_due()}
        if shirt:
            data['%d-cost' % shirt_item.id] = 'on'
        data.update(extra)
        return self.client.post(self.page('troubleshooting_extracosts'), data)

    def test_extracosts_remove_paid_item_needs_confirm(self):
        self.iac.submit_payment(Decimal('80.00'), 'txn-paid')
        response = self._extracosts_post(False)
        self.assertContains(response, 'overpaid by $10.00; proceed anyways?')
        self.assertEqual(self.iac.amount_due(), 0)
        self._extracosts_post(False, confirm_overpaid='1')
        self.assertEqual(self.iac.amount_due(), Decimal('-10.00'))
        #   and adding it back
        self._extracosts_post(True)
        self.assertEqual(self.iac.amount_due(), 0)

    def test_onsite_only_items_hidden_from_students(self):
        from esp.accounting.models import LineItemType
        LineItemType.objects.create(program=self.program, text='Plushie', amount_dec=Decimal('5'),
                                    onsite_only=True)
        module = self.program.getModule('StudentExtraCosts')
        self.assertFalse(module.lineitemtypes().filter(text='Plushie').exists())
        response = self.client.get(self.page('troubleshooting_extracosts'))
        self.assertNotContains(response, 'Plushie')

    def test_extracosts_leave_help_desk_only_items_alone(self):
        from esp.accounting.models import LineItemType
        plushie = LineItemType.objects.create(program=self.program, text='Plushie', amount_dec=Decimal('5'),
                                              onsite_only=True)
        self.iac.set_preference('Plushie', 1)
        self._extracosts_post(True)
        self.assertTrue(self.iac.get_transfers().filter(line_item=plushie).exists())


@override_settings(CYBERSOURCE_CONFIG=CYBERSOURCE)
class DayOfCardTest(DayOfTestBase):
    def setUp(self, *args, **kwargs):
        super(DayOfCardTest, self).setUp(*args, **kwargs)
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))

    def postback(self, data):
        with mock.patch('esp.program.views.transaction.commit'):
            response = self.client.post('/manage/submit_transaction/', data)
        #   ...which sends the browser through payment_return (see views._redirect_from_identifier)
        self.assertTrue(response['Location'].startswith('/manage/payment_return?'))
        return self.client.get(response['Location'])

    def accept(self, identifier, amount, txn):
        return self.postback({'decision': 'ACCEPT', 'reason_code': '100', 'req_merchant_defined_data1': identifier,
                              'req_amount': amount, 'transaction_id': txn})

    def test_return_page_found_without_cookies_on_the_postback(self):
        """ Browsers send CyberSource's return POST without our session
        cookie (SameSite=Lax); the GET it's redirected to has it. """
        from django.test import Client
        self.start()
        checkout = DayOfCardCheckout.objects.get()
        with mock.patch('esp.program.views.transaction.commit'):
            response = Client().post('/manage/submit_transaction/', {
                'decision': 'ACCEPT', 'reason_code': '100', 'req_merchant_defined_data1': checkout.identifier,
                'req_amount': '80.00', 'transaction_id': 'txn-nocookie'})
        self.assertEqual(self.iac.amount_due(), 0)     # recorded regardless
        response = self.client.get(response['Location'])
        self.assertIn('/troubleshooting?user=%d&card_result=success' % self.student.id, response['Location'])
        #   A hand-made return URL only ever redirects to our own pages
        response = self.client.get('/manage/payment_return', {'id': 'junk', 'result': '<script>'})
        self.assertEqual(response['Location'], '/')

    def start(self, **data):
        data.setdefault('user', self.student.id)
        data.setdefault('expected_balance', '%.2f' % self.iac.amount_due())
        data.setdefault('channel', 'laptop')
        return self.client.post(self.onsite_url('troubleshooting_card'), data)

    def test_student_balance_on_laptop(self):
        response = self.start()
        checkout = DayOfCardCheckout.objects.get()
        self.assertEqual((checkout.amount, checkout.recorded_by, checkout.channel),
                         (Decimal('80.00'), self.admin, 'laptop'))
        self.assertContains(response, checkout.identifier)
        response = self.accept(checkout.identifier, '80.00', 'txn-desk')
        #   The admin's browser goes back to the student's troubleshooting page
        self.assertIn('/troubleshooting?user=%d&card_result=success' % self.student.id, response['Location'])
        self.assertEqual(self.iac.amount_due(), 0)
        self.assertEqual(CybersourcePostback.objects.get(transaction_id='txn-desk').status, 'processed')

    def test_custom_amount_reconciles_without_items(self):
        self.start(custom='1', amount='30', description='part payment')
        checkout = DayOfCardCheckout.objects.get()
        self.assertTrue(checkout.custom_amount)
        self.assertIsNone(dayof_payments.checkout_still_valid(checkout))
        self.accept(checkout.identifier, '30.00', 'txn-part')
        self.assertEqual(CybersourcePostback.objects.get(transaction_id='txn-part').status, 'processed')
        self.assertEqual(self.iac.amount_due(), Decimal('50.00'))
        #   Its QR link can't be paid again
        self.assertEqual(dayof_payments.checkout_still_valid(checkout), 'This payment has already been made.')

    def test_card_minimum(self):
        self.start(custom='1', amount='3', description='sticker')
        self.assertFalse(DayOfCardCheckout.objects.exists())
        self.start(custom='1', amount='3', description='sticker', below_minimum='1',
                   below_minimum_reason='they insisted')
        self.assertEqual(DayOfCardCheckout.objects.get().below_minimum_reason, 'they insisted')

    def test_stale_balance_refused(self):
        self.start(expected_balance='70.00')
        self.assertFalse(DayOfCardCheckout.objects.exists())

    def test_student_paying_for_themselves_unchanged(self):
        """ A student's own payment still returns to the usual payment page. """
        self.client.logout()
        self.assertTrue(self.client.login(username=self.student.username, password='password'))
        response = self.accept(self.iac.get_identifier(), '80.00', 'txn-self')
        self.assertIn('/learn/%s/cybersource?result=success' % self.program.getUrlBase(), response['Location'])

    def test_qr_pay_link(self):
        self.start(channel='qr')
        checkout = DayOfCardCheckout.objects.get()
        token = dayof_payments.make_pay_token(checkout)
        self.client.logout()
        response = self.client.get('/onsite_pay/%s' % token)
        self.assertContains(response, checkout.identifier)
        self.assertNotContains(response, self.student.last_name + '<')
        response = self.accept(checkout.identifier, '80.00', 'txn-phone')
        self.assertIn('/onsite_pay/%s?card_result=success' % token, response['Location'])
        response = self.client.get('/onsite_pay/%s' % token)
        self.assertContains(response, 'Nothing is owed')
        response = self.client.get('/onsite_pay/garbage')
        self.assertContains(response, 'expired')


@override_settings(CYBERSOURCE_CONFIG=CYBERSOURCE)
class HelpDeskSalesTest(DayOfTestBase):
    def setUp(self, *args, **kwargs):
        super(HelpDeskSalesTest, self).setUp(*args, **kwargs)
        from esp.accounting.models import LineItemType
        self.plushie = LineItemType.objects.create(program=self.program, text='Plushie',
                                                   amount_dec=Decimal('5'), onsite_only=True)
        self.shirt = LineItemType.objects.get(program=self.program, text='Shirt')
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))

    def sell(self, action, total, **data):
        data.update({'action': action, 'expected_total': total})
        return self.client.post(self.onsite_url('helpdesk_sales'), data)

    def test_cash_sale_and_prices(self):
        self.assertContains(self.client.get(self.onsite_url('helpdesk_sales')), 'data-channel="qr"')
        self.sell('cash', '20.00', **{'q_%d_0' % self.plushie.id: '2', 'q_%d_0' % self.shirt.id: '1'})
        sale = OnsiteSale.objects.get()
        self.assertEqual((sale.total_dec, sale.status, sale.method), (Decimal('20.00'), 'paid', 'cash_check'))
        self.assertEqual(sale.lines.count(), 2)
        #   Discount the shirt; the old sale keeps its price, and a stale total is refused
        self.client.post(self.onsite_url('helpdesk_prices'),
                         {'key': '%d_0' % self.shirt.id, 'price': '8', 'expected_old': ''})
        self.shirt.refresh_from_db()
        self.assertEqual(self.shirt.helpdesk_price, Decimal('8.00'))
        self.assertEqual(HelpdeskPriceChange.objects.get().new_amount, Decimal('8.00'))
        self.sell('cash', '10.00', **{'q_%d_0' % self.shirt.id: '1'})
        self.assertEqual(OnsiteSale.objects.count(), 1)
        self.sell('cash', '8.00', **{'q_%d_0' % self.shirt.id: '1'})
        self.assertEqual(OnsiteSale.objects.count(), 2)
        self.assertEqual(sale.lines.get(line_item=self.shirt).unit_price_dec, Decimal('10.00'))
        self.assertEqual(self.client.get(self.onsite_url('helpdesk_prices')).status_code, 200)

    def test_card_sale_postbacks(self):
        response = self.sell('card', '10.00', **{'q_%d_0' % self.plushie.id: '2', 'channel': 'laptop'})
        sale = OnsiteSale.objects.get()
        self.assertEqual(sale.status, 'pending')
        identifier = '%d/onsite-%d:10.00' % (self.program.id, sale.id)
        self.assertContains(response, identifier)
        #   Declined: nothing changes
        self.postback({'decision': 'DECLINE', 'reason_code': '203', 'req_merchant_defined_data1': identifier,
                       'transaction_id': 'txn-no'})
        sale.refresh_from_db()
        self.assertEqual(sale.status, 'pending')
        response = self.accept(identifier, '10.00', 'txn-sale')
        self.assertIn('helpdesk_sales?sale=%d&card_result=success' % sale.id, response['Location'])
        sale.refresh_from_db()
        self.assertEqual((sale.status, sale.transaction_id), ('paid', 'txn-sale'))
        postback = CybersourcePostback.objects.get(transaction_id='txn-sale')
        self.assertEqual((postback.status, postback.onsite_sale, postback.program, postback.user),
                         ('processed', sale, self.program, None))
        #   A repeat is fine; a second, different charge is flagged
        self.accept(identifier, '10.00', 'txn-sale')
        self.assertEqual(CybersourcePostback.objects.filter(transaction_id='txn-sale').last().status, 'processed')
        self.accept(identifier, '10.00', 'txn-again')
        self.assertEqual(CybersourcePostback.objects.get(transaction_id='txn-again').status, 'needs_review')
        #   No student was credited
        self.assertEqual(self.iac.amount_paid(), 0)

    def test_sale_amount_mismatch_and_unknown_sale(self):
        self.sell('card', '10.00', **{'q_%d_0' % self.plushie.id: '2'})
        sale = OnsiteSale.objects.get()
        self.accept('%d/onsite-%d:10.00' % (self.program.id, sale.id), '9.00', 'txn-short')
        self.assertEqual(CybersourcePostback.objects.get(transaction_id='txn-short').status, 'needs_review')
        #   Not "paid": the QR page must not say Paid
        sale.refresh_from_db()
        self.assertEqual((sale.status, sale.transaction_id), ('review', 'txn-short'))
        status = self.client.get(self.onsite_url('helpdesk_sale_status'), {'sale': sale.id}).json()
        self.assertEqual((status['status'], status['transaction_id']), ('review', 'txn-short'))
        self.accept('%d/onsite-99999:5.00' % self.program.id, '5.00', 'txn-ghost')
        self.assertEqual(CybersourcePostback.objects.get(transaction_id='txn-ghost').status, 'failed')
        self.accept('%d/onsite-x:5.00' % self.program.id, '5.00', 'txn-junk')
        self.assertEqual(CybersourcePostback.objects.get(transaction_id='txn-junk').status, 'failed')

    def accept(self, identifier, amount, txn):
        return self.postback({'decision': 'ACCEPT', 'reason_code': '100', 'req_merchant_defined_data1': identifier,
                              'req_amount': amount, 'transaction_id': txn})

    def postback(self, data):
        with mock.patch('esp.program.views.transaction.commit'):
            response = self.client.post('/manage/submit_transaction/', data)
        #   ...which sends the browser through payment_return (see views._redirect_from_identifier)
        self.assertTrue(response['Location'].startswith('/manage/payment_return?'))
        return self.client.get(response['Location'])

    def test_void(self):
        self.sell('cash', '5.00', **{'q_%d_0' % self.plushie.id: '1'})
        sale = OnsiteSale.objects.get()
        self.client.post(self.onsite_url('helpdesk_sale_void'), {'sale': sale.id})
        sale.refresh_from_db()
        self.assertEqual(sale.status, 'void')


class ReceiptTest(DayOfTestBase):
    def setUp(self, *args, **kwargs):
        super(ReceiptTest, self).setUp(*args, **kwargs)
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))

    def test_aid_and_cash_allocation(self):
        """ Aid covers the $70 fee, the $10 shirt was paid at check-in. """
        from esp.program.controllers import receipts
        request = FinancialAidRequest.objects.create(user=self.student, program=self.program)
        request.approve(dollar_amount=None, discount_percent=100)
        self.assertFalse(receipts.can_have_receipt(self.program, self.student))
        dayof.check_in_student(self.program, self.student, self.admin)
        self.assertTrue(receipts.can_have_receipt(self.program, self.student))
        items = receipts.student_items(self.program, self.student)
        content = receipts.student_receipt_content(self.program, self.student, [t.id for t in items])
        self.assertEqual(content['subtotal'], '80.00')
        self.assertEqual(content['adjustments'], [{'label': 'Financial aid', 'amount': '-70.00'}])
        self.assertEqual(len(content['payments']), 1)
        self.assertIn('cash/check', content['payments'][0]['label'])
        self.assertEqual((content['paid'], content['amount_due']), ('10.00', '0.00'))
        #   A shirt-only receipt shows no aid
        shirt = [t for t in items if t.line_item.text == 'Shirt']
        content = receipts.student_receipt_content(self.program, self.student, [t.id for t in shirt])
        self.assertEqual((content['subtotal'], content['adjustments'], content['paid']), ('10.00', [], '10.00'))

    def test_receipt_views_and_pdf(self):
        dayof.check_in_student(self.program, self.student, self.admin)
        items = [t.id for t in self.iac.get_transfers().filter(line_item__for_payments=False)]
        response = self.client.post(self.onsite_url('troubleshooting_receipt'),
                                    {'user': self.student.id, 'items': items})
        receipt = Receipt.objects.get()
        self.assertEqual((receipt.number, receipt.user), (1, self.student))
        self.assertRedirects(response, '%s?receipt=%d' % (self.onsite_url('troubleshooting_receipt_view'), receipt.id),
                             fetch_redirect_response=False)
        self.assertContains(self.client.get(response['Location']), 'MIT ESP')
        pdf = self.client.get('%s?receipt=%d' % (self.onsite_url('troubleshooting_receipt_pdf'), receipt.id))
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.client.post(self.onsite_url('troubleshooting_receipt_void'), {'receipt': receipt.id})
        receipt.refresh_from_db()
        self.assertIsNotNone(receipt.voided_at)
        #   Numbers count up
        self.client.post(self.onsite_url('troubleshooting_receipt'), {'user': self.student.id, 'items': items})
        self.assertEqual(Receipt.objects.order_by('-id').first().number, 2)

    def test_remake_receipt(self):
        dayof.check_in_student(self.program, self.student, self.admin)
        transfers = list(self.iac.get_transfers().filter(line_item__for_payments=False).order_by('id'))
        self.client.post(self.onsite_url('troubleshooting_receipt'),
                         {'user': self.student.id, 'items': [transfers[0].id], 'payer_name': 'A Parent'})
        first = Receipt.objects.get()
        view = self.client.get(self.onsite_url('troubleshooting_receipt_view'), {'receipt': first.id})
        self.assertContains(view, 'Remake this receipt')
        #   The form comes back with the first receipt's choices
        page = self.client.get(self.onsite_url('troubleshooting'), {'user': self.student.id, 'remake': first.id})
        self.assertContains(page, 'Remaking receipt %d' % first.number)
        self.assertContains(page, 'value="%d" checked="checked"' % transfers[0].id)
        self.assertNotContains(page, 'value="%d" checked="checked"' % transfers[1].id)
        self.assertContains(page, 'value="A Parent"')
        self.client.post(self.onsite_url('troubleshooting_receipt'),
                         {'user': self.student.id, 'items': [t.id for t in transfers], 'replaces': first.id})
        first.refresh_from_db()
        second = Receipt.objects.exclude(id=first.id).get()
        self.assertIsNotNone(first.voided_at)
        self.assertEqual((second.number, second.voided_at), (2, None))
        #   Remaking still works after their check-in is undone
        dayof.undo_check_in(Record.objects.get(user=self.student, program=self.program, event__name='attended'))
        self.client.post(self.onsite_url('troubleshooting_receipt'),
                         {'user': self.student.id, 'items': [transfers[0].id], 'replaces': second.id})
        second.refresh_from_db()
        self.assertIsNotNone(second.voided_at)
        self.assertEqual(Receipt.objects.count(), 3)
        #   A void receipt can't be replaced again
        self.client.post(self.onsite_url('troubleshooting_receipt'),
                         {'user': self.student.id, 'items': [transfers[0].id], 'replaces': first.id})
        self.assertEqual(Receipt.objects.count(), 3)

    def test_no_receipt_before_checkin(self):
        items = [t.id for t in self.iac.get_transfers().filter(line_item__for_payments=False)]
        self.client.post(self.onsite_url('troubleshooting_receipt'), {'user': self.student.id, 'items': items})
        self.assertFalse(Receipt.objects.exists())

    def test_help_desk_cash_receipt(self):
        from esp.accounting.models import LineItemType
        plushie = LineItemType.objects.create(program=self.program, text='Plushie', amount_dec=Decimal('5'),
                                              onsite_only=True)
        response = self.client.post(self.onsite_url('helpdesk_sales'), {
            'action': 'cash_receipt', 'expected_total': '10.00', 'q_%d_0' % plushie.id: '2',
            'payer_name': 'A Parent'})
        receipt = Receipt.objects.get()
        self.assertEqual((receipt.sale.total_dec, receipt.payer_name), (Decimal('10.00'), 'A Parent'))
        page = self.client.get(response['Location'])
        self.assertContains(page, 'Plushie')
        pdf = self.client.get('%s?receipt=%d' % (self.onsite_url('helpdesk_receipt_pdf'), receipt.id))
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertEqual(self.client.get(self.onsite_url('helpdesk_sales')).status_code, 200)


FAKE_PRINT_SERVER = {'url': 'https://print.example:8631', 'token': 'secret'}


@override_settings(PRINT_SERVER=FAKE_PRINT_SERVER)
class PrintingTest(DayOfTestBase):
    def setUp(self, *args, **kwargs):
        super(PrintingTest, self).setUp(*args, **kwargs)
        from esp.utils.models import Printer
        self.default = printing.default_location()
        self.desk = Printer.objects.create(name='Help desk')
        self.other = Printer.objects.create(name='Check-in A')
        #   Never touch a real print server: _request(method, path, timeout, **kwargs) is faked
        self.server = mock.patch('esp.utils.print_server._request', return_value={'job': 'esp-location-1-3'}).start()
        self.addCleanup(mock.patch.stopall)
        #   Uploads go to a scratch directory (the real one needn't exist, e.g. in CI)
        import shutil
        import tempfile
        upload_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, upload_dir, True)
        uploads = override_settings(PRINT_UPLOAD_DIR=upload_dir)
        uploads.enable()
        self.addCleanup(uploads.disable)

    def test_one_connection_per_location_and_take_over(self):
        token = printing.claim_for_laptop(self.desk, self.admin)
        self.desk.refresh_from_db()
        with self.assertRaises(printing.PrintingError):
            printing.claim_for_laptop(self.desk, self.onsite)
        with self.assertRaises(printing.PrintingError):
            printing.connect_network(self.desk, '10.0.0.9', {'model': 'X'},
                                     'ipp://10.0.0.9/ipp/print', self.admin)
        new_token = printing.claim_for_laptop(self.desk, self.onsite, take_over=True)
        self.assertNotEqual(token, new_token)
        #   The old laptop is told who took over (by recorded_by's username)
        with self.assertRaisesRegex(printing.PrintingError, 'onsite'):
            printing.next_job_for_laptop(self.desk, token)
        self.assertIsNone(printing.next_job_for_laptop(self.desk, new_token))

    def test_stale_laptop_is_released(self):
        from esp.utils.models import Printer
        token = printing.claim_for_laptop(self.desk, self.admin)
        Printer.objects.filter(id=self.desk.id).update(
            laptop_last_seen=timezone.now() - printing.LAPTOP_TIMEOUT - timedelta(seconds=5))
        self.desk.refresh_from_db()
        self.assertFalse(printing.is_connected(self.desk))
        #   Someone else can claim it without taking over
        printing.claim_for_laptop(self.desk, self.onsite)
        with self.assertRaises(printing.PrintingError):
            printing.next_job_for_laptop(self.desk, token)

    def test_release(self):
        token = printing.claim_for_laptop(self.desk, self.admin)
        self.assertTrue(printing.release_laptop(self.desk, token))
        self.desk.refresh_from_db()
        self.assertEqual(self.desk.mode, 'none')

    def test_default_takes_unattended_jobs_only(self):
        printing.claim_for_laptop(self.desk, self.admin)
        default_token = printing.claim_for_laptop(self.default, self.admin)
        desk_job = printing.queue('schedule', self.program, self.desk, user=self.student)
        other_job = printing.queue('schedule', self.program, self.other, user=self.student)
        default_job = printing.queue('schedule', self.program, None, user=self.student)
        got = []
        while True:
            job = printing.next_job_for_laptop(self.default, default_token)
            if job is None:
                break
            got.append(job.id)
        self.assertEqual(sorted(got), sorted([other_job.id, default_job.id]))
        desk_job.refresh_from_db()
        self.assertEqual(desk_job.status, 'queued')

    def test_laptop_only_gets_its_own_jobs_once(self):
        token = printing.claim_for_laptop(self.desk, self.admin)
        printing.claim_for_laptop(self.default, self.admin)
        job = printing.queue('schedule', self.program, self.desk, user=self.student)
        printing.queue('schedule', self.program, self.other, user=self.student)
        self.assertEqual(printing.next_job_for_laptop(self.desk, token), job)
        self.assertIsNone(printing.next_job_for_laptop(self.desk, token))

    def test_laptop_protocol_views(self):
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        self.assertEqual(self.client.get(self.onsite_url('printschedules')).status_code, 200)
        self.assertEqual(self.client.get(self.onsite_url('printers_laptop'),
                                         {'location': self.desk.id}).status_code, 200)
        token = json.loads(self.client.post(self.onsite_url('printers_claim'),
                                            {'location': self.desk.id}).content.decode('utf-8'))['token']
        self.assertContains(self.client.get(self.onsite_url('printers_laptop_run'), {'location': self.desk.id}),
                            "I AM THE THING THAT MAKES SCHEDULE PRINTING WORK, DON'T TOUCH ME")
        printing.queue('receipt', self.program, self.desk, receipt=self._receipt())
        data = json.loads(self.client.post(self.onsite_url('printers_poll'),
                                           {'location': self.desk.id, 'token': token}).content.decode('utf-8'))
        pdf = self.client.get(data['pdf'])
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        from esp.utils.models import PrintRequest
        #   Only that laptop (with its token) can fetch it or say it's done
        pdf_url = self.onsite_url('printers_job_pdf')
        self.assertEqual(self.client.get(pdf_url, {'location': self.desk.id, 'job': data['job']}).status_code, 404)
        self.assertEqual(self.client.get(pdf_url, {'location': self.other.id, 'job': data['job'],
                                                   'token': token}).status_code, 404)
        self.client.post(self.onsite_url('printers_done'), {'location': self.desk.id, 'job': data['job'], 'ok': '1'})
        self.assertEqual(PrintRequest.objects.get(id=data['job']).status, 'sent')
        self.client.post(self.onsite_url('printers_done'), {'location': self.desk.id, 'job': data['job'], 'ok': '1',
                                                            'token': token})
        self.assertEqual(PrintRequest.objects.get(id=data['job']).status, 'printed')
        #   Someone else takes over: this laptop is told to stop
        self.client.post(self.onsite_url('printers_claim'), {'location': self.desk.id, 'take_over': '1'})
        response = self.client.post(self.onsite_url('printers_poll'), {'location': self.desk.id, 'token': token})
        self.assertEqual(response.status_code, 409)

    def _receipt(self):
        from esp.program.controllers import receipts
        dayof.check_in_student(self.program, self.student, self.admin)
        items = [t.id for t in receipts.student_items(self.program, self.student)]
        return receipts.create_receipt(self.program, receipts.student_receipt_content(
            self.program, self.student, items), self.admin, user=self.student)

    def test_printschedule_security(self):
        """ LU #6280: POST only, no printing for others without onsite
        access, no open redirect, unknown printer is a 404. """
        from esp.utils.models import PrintRequest
        url = self.onsite_url('printschedule')
        #   Nothing connected: refused, saying so
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        self.assertIn(b'Nothing is printing for Default', self.client.post(url, {'user': self.student.id}).content)
        response = self.client.post(self.onsite_url('printers_queue'), {'kind': 'schedule', 'user': self.student.id})
        self.assertEqual(response.status_code, 409)
        self.assertIn('Nothing is printing for Default', response.json()['error'])
        self.assertFalse(PrintRequest.objects.exists())
        self.client.logout()
        printing.claim_for_laptop(self.default, self.admin)
        self.assertTrue(self.client.login(username=self.student.username, password='password'))
        self.assertEqual(self.client.get(url, {'user': self.admin.id}).status_code, 405)
        other = [s for s in self.students if s != self.student][0]
        self.assertEqual(self.client.post(url, {'user': other.id}).status_code, 404)
        self.assertEqual(self.client.post(url, {'printer': 'nonexistent'}).status_code, 404)
        response = self.client.post(url, {'next': 'https://example.com/'})
        self.assertNotIn('example.com', response['Location'])
        self.assertEqual(PrintRequest.objects.filter(user=self.student).count(), 1)
        self.client.logout()
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        self.client.post(url, {'user': other.id, 'printer': self.desk.name})
        self.assertTrue(PrintRequest.objects.filter(user=other, printer=self.desk, program=self.program).exists())

    def test_print_pdf_page(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from esp.utils.models import PrintRequest
        url = '/manage/printpdf/'
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        self.assertContains(self.client.get(url), 'Print PDFs')

        def upload(name='notes.pdf', data=b'%PDF-1.4 test', **extra):
            return self.client.post(url, dict({'files': [SimpleUploadedFile(name, data, 'application/pdf')],
                                               'location': self.desk.id, 'copies': '2'}, **extra), follow=True)
        #   Nothing connected, or not a PDF: refused
        self.assertContains(upload(), 'Nothing is printing for Help desk or Default')
        printing.claim_for_laptop(self.desk, self.admin)
        self.assertContains(upload(name='x.pdf', data=b'hello'), "x.pdf isn&#39;t a PDF")
        self.assertFalse(PrintRequest.objects.exists())
        self.assertContains(upload(copies='1000'), 'Copies must be from 1 to 999')
        self.assertContains(upload(), 'Sent 1 file (2 copies each) to Help desk')
        job = PrintRequest.objects.get(kind='pdf')
        self.assertEqual(job.copies, 2)
        #   Kept outside the public media directory, and deleted once printed
        from django.conf import settings
        self.assertTrue(job.file.path.startswith(settings.PRINT_UPLOAD_DIR))
        self.assertEqual(printing.render(job), b'%PDF-1.4 test')
        path = job.file.path
        printing.mark_printed(job)
        job.refresh_from_db()
        self.assertFalse(os.path.exists(path))
        self.assertEqual((job.status, job.file.name, job.title), ('printed', '', 'notes.pdf'))
        self.client.logout()
        self.assertTrue(self.client.login(username=self.student.username, password='password'))
        self.assertNotEqual(self.client.get(url).status_code, 200)

    def test_print_pdf_settings(self):
        """ Printer settings for one upload: over the location's own, only
        what its printer can do, and skipped by a printer that can't. """
        from django.core.files.uploadedfile import SimpleUploadedFile
        from esp.utils.models import PrintRequest
        info = {'model': 'X', 'sides': ['one-sided', 'two-sided-long-edge'], 'color_modes': ['color', 'monochrome']}
        printing.connect_network(self.desk, 'printer.example', info, 'ipp://printer.example/ipp/print', self.admin)
        self.desk.refresh_from_db()
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        page = self.client.get('/manage/printpdf/')
        self.assertEqual(json.loads(page.context['printer_data'])[str(self.desk.id)]['settings'],
                         {'sides': 'two-sided-long-edge', 'color_mode': 'monochrome'})

        def upload(**extra):
            return self.client.post('/manage/printpdf/', dict(
                {'files': [SimpleUploadedFile('a.pdf', b'%PDF-1.4', 'application/pdf')], 'location': self.desk.id},
                **extra), follow=True)
        self.assertContains(upload(color_mode='rainbow'), 'support color_mode = rainbow')
        self.assertFalse(PrintRequest.objects.exists())
        self.assertContains(upload(sides='', color_mode='color'), 'Sent 1 file')
        job = PrintRequest.objects.get()
        self.assertEqual(printing.job_settings(job), {'color_mode': 'color'})
        printing.send_to_network_printer(self.desk, b'%PDF-1.4', 'a.pdf', settings=printing.job_settings(job))
        self.assertEqual(sorted(self.server.call_args[1]['params']['o']),
                         ['print-color-mode=color', 'sides=two-sided-long-edge'])
        #   Printed by a printer without color (e.g. Default's): skipped
        printing.connect_network(self.other, 'mono.example', {'model': 'Y', 'color_modes': ['monochrome']},
                                 'ipp://mono.example/ipp/print', self.admin)
        self.other.refresh_from_db()
        printing.send_to_network_printer(self.other, b'%PDF-1.4', 'a.pdf', settings=printing.job_settings(job))
        self.assertEqual(self.server.call_args[1]['params']['o'], ['print-color-mode=monochrome'])

    def fake_print_server(self, location):
        """ Makes the faked print server act like one: jobs get CUPS ids, and
        their state is self.job_state. """
        queue = print_server.queue_name(location)
        self.job_state = {'state': 'processing', 'reasons': [], 'printer_reasons': [], 'printer_message': ''}
        self.job_count = 0

        def request(method, path, timeout, **kwargs):
            if method == 'POST' and path == '/queues/%s/jobs' % queue:
                self.job_count += 1
                return {'job': '%s-%d' % (queue, self.job_count)}
            if method == 'GET' and path.startswith('/queues/%s/jobs/' % queue):
                if isinstance(self.job_state, Exception):
                    raise self.job_state
                return self.job_state
            return {}
        self.server.side_effect = request
        return queue

    def test_queue_names_are_per_connection_ulids(self):
        """ Each network connection gets its own queue, named by a new ULID,
        so sites sharing a print server can't collide (ids repeat across
        sites); the new queue is made before the old one goes. """
        import re
        import time
        from esp.utils.models import new_ulid
        ids = []
        for _ in range(20):
            ids.append(new_ulid())
            time.sleep(0.002)       # a later millisecond each, so they sort by creation
        self.assertTrue(all(re.match(r'^[0-9a-hjkmnp-tv-z]{26}$', i) for i in ids))
        self.assertEqual(len(set(ids)), 20)
        self.assertEqual(sorted(ids), ids)
        self.assertIsNone(self.desk.queue_id)
        with self.assertRaises(ValueError):
            print_server.queue_name(self.desk)

        def connect(location, address):
            printing.connect_network(location, address, {'model': 'X'}, 'ipp://%s/ipp/print' % address,
                                     self.admin, take_over=True)
            location.refresh_from_db()
            return print_server.queue_name(location)
        first = connect(self.desk, 'a.example')
        self.assertTrue(load_print_server_script().QUEUE.match(first))
        self.assertNotEqual(first, connect(self.other, 'a.example'))
        self.server.reset_mock()
        second = connect(self.desk, 'b.example')
        self.assertNotEqual(first, second)
        self.assertEqual([c[0][:2] for c in self.server.call_args_list if c[0][0] in ('PUT', 'DELETE')],
                         [('PUT', '/queues/%s' % second), ('DELETE', '/queues/%s' % first)])
        #   A failed connect leaves what was connected
        self.server.side_effect = print_server.PrintServerError('Couldn\'t reach the print server.')
        with self.assertRaises(printing.PrintingError):
            connect(self.desk, 'c.example')
        self.desk.refresh_from_db()
        self.assertEqual((print_server.queue_name(self.desk), self.desk.network_address), (second, 'b.example'))
        self.server.side_effect = None
        printing.disconnect(self.desk, self.admin)
        self.desk.refresh_from_db()
        self.assertIsNone(self.desk.queue_id)

    def test_copies_go_to_the_print_server_as_one_job(self):
        printing.connect_network(self.desk, 'printer.example', {'model': 'X'}, 'ipp://printer.example/ipp/print',
                                 self.admin)
        self.desk.refresh_from_db()
        printing.send_to_network_printer(self.desk, b'%PDF-1.4', 'Notes', copies=3)
        self.assertIn('copies=3', self.server.call_args[1]['params']['o'])

    def test_network_worker(self):
        from esp.utils.models import Printer, PrintRequest
        info = {'model': 'Brother X', 'sides': ['one-sided', 'two-sided-long-edge']}
        printing.connect_network(self.desk, 'printer.example', info, 'ipp://printer.example/ipp/print',
                                 self.admin)
        self.desk.refresh_from_db()
        queue = print_server.queue_name(self.desk)
        (args, kwargs) = self.server.call_args
        self.assertEqual((args[0], args[1]), ('PUT', '/queues/%s' % queue))
        self.assertEqual(kwargs['json'], {'uri': 'ipp://printer.example/ipp/print', 'description': 'Help desk',
                                          'driver': 'everywhere'})
        self.desk.refresh_from_db()
        self.assertEqual(printing.location_settings(self.desk), {'sides': 'two-sided-long-edge'})
        first = printing.queue('receipt', self.program, self.desk, receipt=self._receipt())
        second = printing.queue('receipt', self.program, self.desk, receipt=self._receipt())
        #   Print server down: the jobs wait, the location shows why, and
        #   the worker backs off before trying again
        self.server.side_effect = print_server.PrintServerError('Couldn\'t reach the print server.')
        printing.run_network_jobs_once()
        first.refresh_from_db()
        self.desk.refresh_from_db()
        self.assertEqual(first.status, 'queued')
        self.assertIn('Print server', self.desk.trouble)
        self.assertIsNotNone(self.desk.trouble_since)
        calls = self.server.call_count
        printing.run_network_jobs_once()
        self.assertEqual(self.server.call_count, calls)
        printing._retry_at.clear()
        #   Back up: one job at a time goes to the print server, and counts
        #   as printed only once CUPS says so
        self.fake_print_server(self.desk)
        self.assertEqual(printing.run_network_jobs_once(), 1)
        (args, kwargs) = [c for c in self.server.call_args_list if c[0][0] == 'POST'][-1]
        self.assertEqual(args[1], '/queues/%s/jobs' % queue)
        self.assertTrue(kwargs['data'].startswith(b'%PDF'))
        self.assertEqual(kwargs['params']['o'], ['sides=two-sided-long-edge'])
        first.refresh_from_db()
        self.desk.refresh_from_db()
        self.assertEqual((first.status, first.server_job, self.desk.trouble), ('sent', queue + '-1', ''))
        self.assertEqual(printing.run_network_jobs_once(), 0)
        #   Stuck at the printer: shown as the printer's trouble
        PrintRequest.objects.filter(id=first.id).update(time_executed=timezone.now() - timedelta(minutes=5))
        self.job_state['printer_message'] = 'Out of paper'
        self.assertEqual(printing.run_network_jobs_once(), 0)
        self.desk.refresh_from_db()
        self.assertEqual(self.desk.trouble, 'Printer: Out of paper')
        #   Printed: the next one goes, and the trouble clears
        self.job_state = {'state': 'completed', 'reasons': []}
        self.assertEqual(printing.run_network_jobs_once(), 1)
        first.refresh_from_db()
        second.refresh_from_db()
        self.desk.refresh_from_db()
        self.assertEqual((first.status, second.status, second.server_job, self.desk.trouble),
                         ('printed', 'sent', queue + '-2', ''))
        #   CUPS lost it: sent again; CUPS gave up: failed
        self.job_state = print_server.PrintServerError('CUPS has no job %s-2.' % queue)
        self.assertEqual(printing.run_network_jobs_once(), 1)
        second.refresh_from_db()
        self.assertEqual((second.status, second.server_job, second.attempts), ('sent', queue + '-3', 2))
        self.job_state = {'state': 'aborted', 'reasons': ['job-aborted-by-system']}
        printing.run_network_jobs_once()
        second.refresh_from_db()
        self.assertEqual(second.status, 'failed')
        self.assertIn('job-aborted-by-system', second.error)
        self.assertEqual(Printer.objects.get(id=self.desk.id).trouble, '')

    def test_refused_job_fails_and_the_next_prints(self):
        from esp.utils.models import Printer
        printing.connect_network(self.desk, 'printer.example', {'model': 'X', 'media': ['na_letter_8.5x11in', 'odd size']},
                                 'ipp://printer.example/ipp/print', self.admin)
        self.desk.refresh_from_db()
        queue = print_server.queue_name(self.desk)
        bad = printing.queue('receipt', self.program, self.desk, receipt=self._receipt())
        good = printing.queue('receipt', self.program, self.desk, receipt=self._receipt())
        sent = []

        def request(method, path, timeout, **kwargs):
            if method == 'POST':
                if not sent:
                    sent.append('refused')
                    raise print_server.PrintServerError('Bad title or option.', 400)
                sent.append('ok')
                return {'job': queue + '-1'}
            return {}
        self.server.side_effect = request
        self.assertEqual(printing.run_network_jobs_once(), 1)
        bad.refresh_from_db()
        good.refresh_from_db()
        self.assertEqual((bad.status, good.status), ('failed', 'sent'))
        self.assertIn('Bad title or option', bad.error)
        self.assertIn('refused', Printer.objects.get(id=self.desk.id).last_error)
        #   An outage (unreachable, 5xx) or a wrong token still keeps jobs waiting
        for error in (print_server.PrintServerError("Couldn't reach the print server."),
                      print_server.PrintServerError('CUPS failed', 502), print_server.PrintServerError('token', 401)):
            self.assertFalse(error.job_refused)
        self.assertTrue(print_server.PrintServerError('x', 400).job_refused)
        #   Settings the print server wouldn't accept are refused when saved
        with self.assertRaisesRegex(printing.PrintingError, "can't be sent"):
            printing.save_settings(self.desk, {'media': 'odd size'}, self.admin)
        printing.save_settings(self.desk, {'media': 'na_letter_8.5x11in'}, self.admin)

    def test_network_jobs_recalled(self):
        printing.connect_network(self.desk, 'printer.example', {'model': 'X'}, 'ipp://printer.example/ipp/print',
                                 self.admin)
        self.desk.refresh_from_db()
        queue = self.fake_print_server(self.desk)
        job = printing.queue('receipt', self.program, self.desk, receipt=self._receipt())
        printing.run_network_jobs_once()
        job.refresh_from_db()
        self.assertEqual(job.status, 'sent')
        #   A laptop taking over gets the job the printer was stuck on
        token = printing.claim_for_laptop(self.desk, self.admin, take_over=True)
        self.assertIn(mock.call('DELETE', '/queues/%s/jobs/%s-1' % (queue, queue), print_server.TIMEOUT),
                      self.server.call_args_list)
        job.refresh_from_db()
        self.assertEqual((job.status, job.server_job), ('queued', ''))
        self.assertEqual(printing.next_job_for_laptop(self.desk, token), job)
        #   "Cancel all waiting" cancels the one at the print server too
        printing.connect_network(self.desk, 'printer.example', {'model': 'X'}, 'ipp://printer.example/ipp/print',
                                 self.admin)
        self.desk.refresh_from_db()
        self.fake_print_server(self.desk)      # (a new connection: a new queue)
        job = printing.queue('receipt', self.program, self.desk, receipt=self._receipt())
        printing.run_network_jobs_once()
        self.assertEqual(printing.discard_waiting(self.desk, self.admin), 1)
        job.refresh_from_db()
        self.assertEqual(job.status, 'cancelled')

    def test_trouble_shown(self):
        printing.connect_network(self.desk, 'printer.example', {'model': 'X'}, 'ipp://printer.example/ipp/print',
                                 self.admin)
        printing._set_trouble(self.desk, 'Printer: Out of paper')
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        response = self.client.post(self.onsite_url('printers_queue'), {'location': self.desk.id, 'kind': 'schedule',
                                                                          'user': self.student.id})
        self.assertIn('Out of paper', response.json()['message'])
        printing.queue('receipt', self.program, self.desk, receipt=self._receipt())
        response = self.client.get(self.onsite_url('printschedules'))
        self.assertContains(response, 'Not printing')
        self.assertContains(response, 'Oldest waiting job')

    def test_queue_remade_if_missing_and_removed_on_take_over(self):
        printing.connect_network(self.desk, 'printer.example', {'model': 'X'}, 'ipp://printer.example/ipp/print',
                                 self.admin)
        self.desk.refresh_from_db()
        self.server.side_effect = [print_server.PrintServerError('lp: The printer or class does not exist.'),
                                   {}, {'job': 'x-1'}]
        self.assertEqual(printing.send_to_network_printer(self.desk, b'%PDF-1.4', 'Test'), 'x-1')
        self.assertEqual([c[0][0] for c in self.server.call_args_list[-3:]], ['POST', 'PUT', 'POST'])
        self.server.side_effect = None
        #   A laptop taking over from the network printer (the setup page's
        #   view) drops the print server's queue
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        response = self.client.post(self.onsite_url('printers_claim'), {'location': self.desk.id, 'take_over': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.server.call_args[0][:2],
                         ('DELETE', '/queues/%s' % print_server.queue_name(self.desk)))
        self.desk.refresh_from_db()
        self.assertEqual(self.desk.mode, 'laptop')

    def test_connect_older_printers(self):
        #   The driver probe() chose goes to the print server...
        printing.connect_network(self.desk, 'old.example', {'model': 'Old', 'driver': 'postscript'},
                                 'ipp://old.example/ipp', self.admin)
        self.assertEqual(self.server.call_args[1]['json']['driver'], 'postscript')
        #   ...and a printer that takes nothing it can send is refused
        with self.assertRaisesRegex(printing.PrintingError, "doesn't take anything"):
            printing.connect_network(self.other, 'odd.example', {'driver': None, 'formats': ['text/plain']},
                                     'ipp://odd.example/ipp', self.admin)

    def test_connect_fails_cleanly(self):
        self.server.side_effect = print_server.PrintServerError('lpadmin: Unable to query printer')
        with self.assertRaisesRegex(printing.PrintingError, 'Unable to query printer'):
            printing.connect_network(self.desk, 'printer.example', {'model': 'X'},
                                     'ipp://printer.example/ipp/print', self.admin)
        self.desk.refresh_from_db()
        self.assertEqual(self.desk.mode, 'none')

    def test_probe_and_page_without_print_server(self):
        self.server.return_value = {'uri': 'ipp://p/ipp/print', 'info': {'model': 'X'}}
        self.assertEqual(printing.probe('p'), ('ipp://p/ipp/print', {'model': 'X'}))
        self.assertEqual(self.server.call_args[1]['params'], {'address': 'p'})
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        self.assertContains(self.client.get(self.onsite_url('printschedules')), 'Connect network printer')
        with override_settings(PRINT_SERVER=None):
            response = self.client.get(self.onsite_url('printschedules'))
            self.assertNotContains(response, 'Connect network printer')
            self.assertContains(response, 'no print server configured')

    def test_archive_and_restore(self):
        from esp.program.templatetags.printing import print_locations
        printing.connect_network(self.other, 'printer.example', {'model': 'X'}, 'ipp://printer.example/ipp/print',
                                 self.admin)
        self.other.refresh_from_db()
        queue = print_server.queue_name(self.other)
        job = printing.queue('receipt', self.program, self.other, receipt=self._receipt())
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        archive = {'location': self.other.id, 'action': 'archive'}
        self.client.post(self.onsite_url('printers_action'), archive)
        self.other.refresh_from_db()
        self.assertFalse(self.other.archived)       # jobs waiting
        job.status = 'cancelled'
        job.save()
        self.client.post(self.onsite_url('printers_action'), archive)
        self.other.refresh_from_db()
        #   Archived: disconnected (queue removed), hidden, kept with its jobs
        self.assertEqual((self.other.archived, self.other.mode), (True, 'none'))
        self.assertEqual(self.server.call_args[0][:2], ('DELETE', '/queues/%s' % queue))
        self.assertIsNone(self.other.queue_id)
        self.assertNotIn(self.other, print_locations())
        self.assertTrue(type(job).objects.filter(id=job.id).exists())
        with self.assertRaises(printing.PrintingError):
            printing.queue('schedule', self.program, self.other, user=self.student)
        with self.assertRaises(printing.PrintingError):
            printing.claim_for_laptop(self.other, self.admin)
        response = self.client.get(self.onsite_url('printschedules'))
        self.assertContains(response, 'Archived locations (1)')
        #   A new location may reuse the name; then the old one can't come back until renamed
        self.client.post(self.onsite_url('printers_action'), {'action': 'add_location', 'name': 'Check-in A'})
        with self.assertRaisesRegex(printing.PrintingError, 'Another location'):
            printing.restore(self.other, self.admin)
        type(self.other).objects.filter(archived=False, name='Check-in A').update(name='Check-in A2')
        self.client.post(self.onsite_url('printers_action'), {'location': self.other.id, 'action': 'restore'})
        self.other.refresh_from_db()
        self.assertFalse(self.other.archived)
        with self.assertRaises(printing.PrintingError):
            printing.archive(self.default, self.admin)

    def test_test_page_pdf(self):
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        response = self.client.get(self.onsite_url('printers_test_pdf'), {'location': self.desk.id})
        self.assertTrue(response.content.startswith(b'%PDF'))


class PrintServerClientTest(TestCase):
    """ esp.utils.print_server, the website's side of the print server's API. """

    def response(self, status, data):
        reply = mock.Mock(status_code=status)
        reply.json.return_value = data
        return reply

    @override_settings(PRINT_SERVER={'url': 'https://print.example:8631/', 'token': 'secret'})
    def test_requests(self):
        with mock.patch('esp.utils.print_server.requests.request',
                        return_value=self.response(200, {'job': 'q-4'})) as call:
            self.assertEqual(print_server.print_pdf('esp-location-3', b'%PDF-1.4', 'Receipt 4',
                                                    {'sides': 'two-sided-long-edge'}), 'q-4')
        (args, kwargs) = call.call_args
        self.assertEqual(args, ('POST', 'https://print.example:8631/queues/esp-location-3/jobs'))
        self.assertEqual(kwargs['headers'], {'Authorization': 'Bearer secret'})
        self.assertEqual(kwargs['params'], {'title': 'Receipt 4', 'o': ['sides=two-sided-long-edge']})
        self.assertEqual((kwargs['data'], kwargs['verify']), (b'%PDF-1.4', True))
        #   Errors come back with the server's message, so a missing queue is recognized
        missing = self.response(404, {'error': 'lp: The printer or class does not exist.'})
        with mock.patch('esp.utils.print_server.requests.request', return_value=missing):
            with self.assertRaises(print_server.PrintServerError) as raised:
                print_server.print_pdf('esp-location-3', b'%PDF-1.4')
        self.assertTrue(print_server.queue_missing(raised.exception))
        with mock.patch('esp.utils.print_server.requests.request',
                        side_effect=print_server.requests.exceptions.ConnectionError()):
            with self.assertRaisesRegex(print_server.PrintServerError, 'reach the print server'):
                print_server.add_queue('esp-location-3', 'ipp://10.0.0.9/ipp/print')

    @override_settings(PRINT_SERVER={'url': 'https://print.example:8631/', 'token': 'secret'})
    def test_client_keeps_the_status(self):
        reply = mock.Mock(status_code=400)
        reply.json.return_value = {'error': 'Bad title or option.'}
        with mock.patch('esp.utils.print_server.requests.request', return_value=reply):
            with self.assertRaises(print_server.PrintServerError) as raised:
                print_server.print_pdf('esp-location-3', b'%PDF-1.4')
        self.assertEqual(raised.exception.status, 400)
        self.assertTrue(raised.exception.job_refused)

    @override_settings(PRINT_SERVER=None)
    def test_not_configured(self):
        self.assertFalse(print_server.configured())
        with self.assertRaisesRegex(print_server.PrintServerError, 'PRINT_SERVER'):
            print_server.probe('10.0.0.9')


def load_print_server_script():
    """ deploy/print_server/esp-print-server, which runs on the print server
    (not part of the website), loaded as a module. """
    import importlib.machinery
    import importlib.util
    import os
    path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'deploy', 'print_server',
                        'esp-print-server')
    loader = importlib.machinery.SourceFileLoader('esp_print_server', os.path.normpath(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader('esp_print_server', loader))
    loader.exec_module(module)
    return module


class PrintServerScriptTest(TestCase):
    """ The print server itself, run on localhost without TLS, with CUPS
    and printers faked. """

    def setUp(self):
        import threading
        self.script = load_print_server_script()
        self.httpd = self.script.ThreadingHTTPServer(('127.0.0.1', 0), self.script.Handler)
        self.httpd.token = 'secret'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        self.url = 'http://127.0.0.1:%d' % self.httpd.server_address[1]
        self.run_cups = mock.patch.object(self.script, 'run',
                                          return_value='request id is esp-location-2-7 (1 file(s))').start()
        #   (what a new queue supports comes from this host's CUPS)
        mock.patch.object(self.script, 'queue_info', return_value={'sides': ['one-sided']}).start()
        self.addCleanup(mock.patch.stopall)

    def call(self, method, path, token='secret', **kwargs):
        import requests
        headers = {'Authorization': 'Bearer %s' % token} if token else {}
        response = requests.request(method, self.url + path, headers=headers, timeout=10, **kwargs)
        return (response.status_code, response.json())

    def test_api(self):
        self.assertEqual(self.call('GET', '/queues/esp-location-2', token='wrong')[0], 401)
        self.assertEqual(self.call('GET', '/queues/esp-location-2', token=None)[0], 401)
        #   Only esp-<ULID> queues (or the old esp-location-<n>), printer URIs, simple options, PDFs
        self.assertEqual(self.call('DELETE', '/queues/esp-01jd3k8w6p0b2c4d5e6f7g8h9j')[0], 200)
        self.assertEqual(self.call('DELETE', '/queues/esp-01JD3K8W6P0B2C4D5E6F7G8H9J')[0], 400)
        self.assertEqual(self.call('DELETE', '/queues/esp-other')[0], 400)
        self.run_cups.reset_mock()
        self.assertEqual(self.call('DELETE', '/queues/somebody-elses-printer')[0], 400)
        self.assertEqual(self.call('PUT', '/queues/esp-location-2', json={'uri': 'file:/etc/passwd'})[0], 400)
        self.assertEqual(self.call('POST', '/queues/esp-location-2/jobs', data=b'not a pdf')[0], 400)
        self.assertEqual(self.call('POST', '/queues/esp-location-2/jobs', data=b'%PDF-1.4',
                                   params={'o': 'sides=two sided; rm -rf'})[0], 400)
        self.run_cups.assert_not_called()
        self.assertEqual(self.call('PUT', '/queues/esp-location-2', json={'uri': 'ipp://10.0.0.9/ipp/print',
                                                                          'description': 'Help desk'}),
                         (200, {'queue': 'esp-location-2', 'info': {'sides': ['one-sided']}}))
        self.assertEqual(self.run_cups.call_args[0][0],
                         ['lpadmin', '-p', 'esp-location-2', '-E', '-v', 'ipp://10.0.0.9/ipp/print', '-m',
                          'everywhere', '-D', 'Help desk', '-o', 'printer-error-policy=retry-current-job'])
        #   An older printer gets a generic driver; only known drivers
        self.call('PUT', '/queues/esp-location-2', json={'uri': 'ipp://10.0.0.9/ipp', 'driver': 'postscript'})
        self.assertIn('drv:///sample.drv/generic.ppd', [arg for c in self.run_cups.call_args_list for arg in c[0][0]])
        self.assertEqual(self.call('PUT', '/queues/esp-location-2', json={'uri': 'ipp://10.0.0.9/ipp',
                                                                          'driver': '/etc/passwd'})[0], 400)
        self.assertEqual(self.call('POST', '/queues/esp-location-2/jobs', data=b'%PDF-1.4',
                                   params={'title': 'Receipt 4', 'o': ['sides=two-sided-long-edge']}),
                         (200, {'job': 'esp-location-2-7'}))
        (args, kwargs) = self.run_cups.call_args
        self.assertEqual(args[0], ['lp', '-d', 'esp-location-2', '-t', 'Receipt 4', '-o',
                                   'sides=two-sided-long-edge'])
        self.assertEqual(kwargs['stdin'], b'%PDF-1.4')
        self.run_cups.side_effect = self.script.Refused(404, 'lp: The printer or class does not exist.')
        self.assertEqual(self.call('DELETE', '/queues/esp-location-2'),
                         (404, {'error': 'lp: The printer or class does not exist.'}))

    def test_jobs(self):
        script = self.script
        job = {script.JOB_ATTRIBUTES: {'job-state': [5], 'job-state-reasons': ['job-printing']}}
        printer = {script.PRINTER_ATTRIBUTES: {'printer-state': [4], 'printer-state-reasons': ['media-empty-error'],
                                               'printer-state-message': ['Out of paper']}}
        with mock.patch.object(script, 'ipp_post', side_effect=[(0, job), (0, printer)]) as ipp:
            self.assertEqual(self.call('GET', '/queues/esp-location-2/jobs/esp-location-2-7'), (200, {
                'state': 'processing', 'reasons': ['job-printing'], 'printer_state': 'printing',
                'printer_reasons': ['media-empty-error'], 'printer_message': 'Out of paper'}))
        self.assertEqual([c[0][0] for c in ipp.call_args_list],
                         ['http://localhost:631/jobs/7', 'http://localhost:631/printers/esp-location-2'])
        with mock.patch.object(script, 'ipp_post', return_value=(script.NOT_FOUND, {})):
            (status, data) = self.call('GET', '/queues/esp-location-2/jobs/esp-location-2-7')
        self.assertEqual(status, 404)
        self.assertIn('CUPS has no job', data['error'])
        #   Only that queue's jobs
        self.assertEqual(self.call('GET', '/queues/esp-location-2/jobs/esp-location-3-7')[0], 400)
        self.assertEqual(self.call('DELETE', '/queues/esp-location-2/jobs/7; rm')[0], 400)
        self.assertEqual(self.call('DELETE', '/queues/esp-location-2/jobs/esp-location-2-7'),
                         (200, {'job': 'esp-location-2-7'}))
        self.assertEqual(self.run_cups.call_args[0][0], ['cancel', 'esp-location-2-7'])
        #   Cancelling a finished job is fine
        self.run_cups.side_effect = script.Refused(502, 'cancel: Job #7 is already completed - can\'t cancel.')
        self.assertEqual(self.call('DELETE', '/queues/esp-location-2/jobs/esp-location-2-7')[0], 200)

    def test_model_drivers(self):
        script = self.script
        lpinfo = ('drv:///sample.drv/generic.ppd Generic PostScript Printer\n'
                  'postscript-hp:0/ppd/hplip/HP/hp-color_laserjet_cp4520_series-ps.ppd '
                  'HP Color LaserJet CP4020-CP4520 Series Postscript (recommended)\n')
        snmp = ('network socket://10.0.0.9:9100 "HP Color LaserJet CP4520 Series" "x" '
                '"MFG:Hewlett-Packard;CMD:PJL,PCL,POSTSCRIPT;MDL:HP Color LaserJet CP4520 Series;" ""\n')
        self.run_cups.side_effect = lambda args, stdin=None: lpinfo if args[0] == 'lpinfo' else snmp
        self.assertEqual(script.snmp_device_id('10.0.0.9')['MDL'], 'HP Color LaserJet CP4520 Series')
        ppd = 'postscript-hp:0/ppd/hplip/HP/hp-color_laserjet_cp4520_series-ps.ppd'
        self.assertEqual(script.model_ppd('HP Color LaserJet CP4520 Series'), ppd)
        self.assertIsNone(script.model_ppd('Canon LBP6230/6240'))
        #   An IPP 1.1 PostScript printer gets its model's driver
        reply = (0, {script.PRINTER_ATTRIBUTES: {'document-format-supported': ['application/postscript']}})
        with mock.patch.object(script, 'ipp_post', side_effect=[(script.VERSION_NOT_SUPPORTED, {}), reply]):
            info = script.probe('10.0.0.9')['info']
        self.assertEqual((info['driver'], info['model']), ('model:' + ppd, 'HP Color LaserJet CP4520 Series'))
        #   Only installed drivers; a duplex unit is marked fitted
        self.run_cups.side_effect = lambda args, stdin=None: (
            lpinfo if args[0] == 'lpinfo' else 'HPOption_Duplexer/Duplex Unit: True *False\n')
        script.create_queue('esp-location-2', 'ipp://10.0.0.9/ipp', 'Desk', 'model:' + ppd)
        self.assertIn(['lpadmin', '-p', 'esp-location-2', '-o', 'HPOption_Duplexer=True'],
                      [c[0][0] for c in self.run_cups.call_args_list])
        with self.assertRaises(script.Refused):
            script.create_queue('esp-location-2', 'ipp://10.0.0.9/ipp', 'Desk', 'model:/etc/passwd')

    def test_printer_without_ipp(self):
        """ A printer with no IPP (Canon's UFR II LT ones): SNMP says what it
        is, its maker's driver prints to it raw (port 9100), on Letter. """
        script = self.script
        lpinfo = ('drv:///sample.drv/generic.ppd Generic PostScript Printer\n'
                  'CNRCUPSLBP6230ZNK.ppd Canon LBP6230/6240\n')
        snmp = ('network socket://10.31.171.64 "Canon LBP6230/6240" "Canon LBP6230dw" '
                '"MFG:Canon;MDL:LBP6230/6240;CLS:PRINTER;CID:CA_UFRIILT_OIP;CMD:LIPSLX,CPCA;" ""\n')
        self.run_cups.side_effect = lambda args, stdin=None: lpinfo if args[0] == 'lpinfo' else snmp
        unreachable = script.Refused(502, 'Couldn\'t reach http://10.31.171.64:631/ipp/print (refused).')
        with mock.patch.object(script, 'ipp_post', side_effect=unreachable), \
                mock.patch.object(script, 'port_open', return_value=True):
            result = script.probe('10.31.171.64')
        self.assertEqual(result['uri'], 'socket://10.31.171.64:9100')
        self.assertEqual((result['info']['driver'], result['info']['model']),
                         ('model:CNRCUPSLBP6230ZNK.ppd', 'Canon LBP6230/6240'))
        self.assertEqual(result['info']['sides'], [])       # from the queue, once made
        #   No 9100: LPD; neither: refused
        with mock.patch.object(script, 'ipp_post', side_effect=unreachable), \
                mock.patch.object(script, 'port_open', side_effect=lambda host, port: port == 515):
            self.assertEqual(script.probe('10.31.171.64')['uri'], 'lpd://10.31.171.64/')
        with mock.patch.object(script, 'ipp_post', side_effect=unreachable), \
                mock.patch.object(script, 'port_open', return_value=False):
            with self.assertRaisesRegex(script.Refused, 'port 9100 or 515'):
                script.probe('10.31.171.64')
        #   No driver installed for it, or SNMP doesn't answer: says why
        self.run_cups.side_effect = lambda args, stdin=None: (
            'drv:///sample.drv/generic.ppd Generic PostScript Printer\n' if args[0] == 'lpinfo' else snmp)
        with mock.patch.object(script, 'ipp_post', side_effect=unreachable):
            with self.assertRaisesRegex(script.Refused, 'no driver for it'):
                script.probe('10.31.171.64')
        self.run_cups.side_effect = script.Refused(502, 'snmp: no reply')
        with mock.patch.object(script, 'ipp_post', side_effect=unreachable):
            with self.assertRaisesRegex(script.Refused, 'Couldn\'t reach'):
                script.probe('10.31.171.64')
        #   The queue takes raw URIs and defaults to Letter
        self.run_cups.side_effect = lambda args, stdin=None: (
            lpinfo if args[0] == 'lpinfo' else 'PageSize/Page Size: Letter Legal *A4\nDuplex/Duplex: *None DuplexNoTumble\n')
        with mock.patch.object(script, 'queue_info', return_value={}):
            script.create_queue('esp-location-3', 'socket://10.31.171.64:9100', 'Canon', 'model:CNRCUPSLBP6230ZNK.ppd')
        calls = [c[0][0] for c in self.run_cups.call_args_list]
        self.assertIn(['lpadmin', '-p', 'esp-location-3', '-o', 'PageSize=Letter'], calls)
        self.assertTrue(script.URI.match('socket://10.31.171.64:9100'))
        self.assertTrue(script.URI.match('lpd://10.31.171.64/'))
        self.assertFalse(script.URI.match('file:///etc/passwd'))

    def test_older_ipp_path(self):
        """ A printer with IPP 1.1 at /ipp, not /ipp/print (older Brothers),
        taking PCL: found there, with the generic PCL driver. """
        script = self.script
        snmp = ('network lpd://BRW008092B8DC1F/BINARY_P1 "Brother HL-2280DW" "Brother HL-2280DW" '
                '"MFG:Brother;CMD:PJL,PCL,PCLXL;MDL:HL-2280DW;CLS:PRINTER;" ""\n')
        self.run_cups.side_effect = lambda args, stdin=None: (
            'drv:///sample.drv/generpcl.ppd Generic PCL Laser Printer\n' if args[0] == 'lpinfo' else snmp)
        missing = script.Refused(502, 'The printer answered HTTP 404.', http_status=404)
        pcl = (0x0001, {script.PRINTER_ATTRIBUTES: {'printer-make-and-model': ['Brother HL-2280DW'],
                                                    'document-format-supported': ['application/vnd.hp-PCL']}})
        with mock.patch.object(script, 'ipp_post',
                               side_effect=[missing, (script.VERSION_NOT_SUPPORTED, {}), pcl]) as ipp:
            result = script.probe('10.31.155.22')
        self.assertEqual(result['uri'], 'ipp://10.31.155.22/ipp')
        self.assertEqual((result['info']['driver'], result['info']['model']), ('pcl', 'Brother HL-2280DW'))
        self.assertEqual([c[0][0] for c in ipp.call_args_list],
                         ['http://10.31.155.22:631/ipp/print'] + ['http://10.31.155.22:631/ipp'] * 2)
        #   A full URI is used as given
        with mock.patch.object(script, 'ipp_post', side_effect=[missing]), \
                mock.patch.object(script, 'port_open', return_value=False):
            with self.assertRaises(script.Refused):
                script.probe('ipp://10.31.155.22/ipp/print')

    def test_choose_driver_and_ipp_1_1(self):
        script = self.script
        self.assertEqual(script.choose_driver(['image/urf', 'application/pdf'], True), 'everywhere')
        self.assertEqual(script.choose_driver(['application/pdf'], False), None)
        self.assertEqual(script.choose_driver(['text/plain', 'application/postscript', 'application/vnd.hp-PCL'],
                                              False), 'postscript')
        self.assertEqual(script.choose_driver(['application/vnd.hp-PCL'], False), 'pcl')
        #   A printer refusing IPP 2.0 is asked again in 1.1
        replies = [(script.VERSION_NOT_SUPPORTED, {}),
                   (0, {script.PRINTER_ATTRIBUTES: {'document-format-supported': ['application/postscript']}})]
        with mock.patch.object(script, 'ipp_post', side_effect=replies) as ipp:
            result = script.probe('10.0.0.9')
        self.assertEqual(result['info']['driver'], 'postscript')
        self.assertEqual([c[0][1][:2] for c in ipp.call_args_list], [b'\x02\x00', b'\x01\x01'])

    def test_probe(self):
        import struct
        script = self.script
        self.assertEqual(script.normalize_address('10.1.2.3'), 'ipp://10.1.2.3/ipp/print')
        self.assertEqual(script.normalize_address('printer.mit.edu:8631'), 'ipp://printer.mit.edu:8631/ipp/print')
        self.assertEqual(script.http_url('ipps://p.mit.edu/ipp/print'), 'https://p.mit.edu:631/ipp/print')
        with self.assertRaises(script.Refused):
            script.normalize_address('not a printer!')
        #   The request is valid IPP (a request's op-id sits where a reply's status does)
        (status, groups) = script.decode_response(script.encode_request('ipp://h/ipp/print', request_id=9))
        self.assertEqual(status, script.GET_PRINTER_ATTRIBUTES)
        self.assertEqual(groups[script.OPERATION_ATTRIBUTES]['printer-uri'], ['ipp://h/ipp/print'])

        def attr(tag, name, values):
            out = b''
            for (i, value) in enumerate(values if isinstance(values, list) else [values]):
                data = struct.pack('>i', value) if isinstance(value, int) else value.encode('utf-8')
                key = name.encode('utf-8') if i == 0 else b''
                out += struct.pack('>BH', tag, len(key)) + key + struct.pack('>H', len(data)) + data
            return out
        reply = struct.pack('>BBHI', 2, 0, 0, 1) + struct.pack('>B', script.PRINTER_ATTRIBUTES)
        reply += attr(0x41, 'printer-make-and-model', 'Brother HL-L2350DW')
        reply += attr(script.ENUM, 'printer-state', 3)
        reply += attr(0x49, 'document-format-supported', ['image/urf', 'image/pwg-raster'])
        reply += attr(script.KEYWORD, 'sides-supported', ['one-sided', 'two-sided-long-edge'])
        reply += attr(script.ENUM, 'print-quality-supported', [4, 5])
        #   a collection is skipped
        reply += struct.pack('>BH', script.BEG_COLLECTION, len(b'media-col-default')) + b'media-col-default' + \
            struct.pack('>H', 0)
        reply += attr(0x4A, '', 'media-size')
        reply += struct.pack('>BHH', script.END_COLLECTION, 0, 0)
        reply += struct.pack('>B', script.END_OF_ATTRIBUTES)
        info = script.summarize(script.decode_response(reply)[1][script.PRINTER_ATTRIBUTES])
        self.assertEqual((info['model'], info['state'], info['formats'], info['qualities']),
                         ('Brother HL-L2350DW', 'idle', ['image/urf', 'image/pwg-raster'], ['normal', 'high']))
        #   Through the API
        with mock.patch.object(script, 'probe', return_value={'uri': 'ipp://p/ipp/print', 'info': info}) as probe:
            self.assertEqual(self.call('GET', '/probe', params={'address': 'p'})[1]['info']['model'],
                             'Brother HL-L2350DW')
        probe.assert_called_with('p')
