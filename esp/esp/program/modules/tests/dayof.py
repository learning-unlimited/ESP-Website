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
from esp.program.controllers import dayof, dayof_payments
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
