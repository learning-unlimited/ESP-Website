"""Day-of payment troubleshooting: a table beside morning check-in where staff fix
whatever blocks a student's check-in (balance owed, financial aid, extra
costs, card payment, receipt). One student per page, so staff can keep
several students open in separate tabs."""
from __future__ import absolute_import
from __future__ import unicode_literals

import hashlib
import json

from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404

from esp.accounting.controllers import IndividualAccountingController
from esp.accounting.models import Receipt, Transfer
from esp.middleware import ESPError
from esp.program.controllers import dayof, dayof_payments, receipts
from esp.program.controllers.dayof_payments import result_text as dayof_payments_result_text
from esp.program.modules.base import ProgramModuleObj, needs_onsite, main_call, aux_call
from esp.users.models import ESPUser, Record
from esp.users.views import search_for_user
from esp.utils.web import render_to_response



def student_summary(program, student):
    """ Everything the troubleshooting page shows about a student's money. """
    iac = IndividualAccountingController(program, student)
    iac.ensure_required_transfers()
    items = []
    for t in iac.get_transfers().filter(line_item__for_payments=False).exclude(
            line_item__text__in=iac.finaid_items).select_related('line_item', 'option').order_by('id'):
        items.append({'transfer': t, 'text': t.line_item.text,
                      'option': t.option.description if t.option else '',
                      'amount': t.amount_dec, 'paid': t.paid_in_id is not None,
                      'for_finaid': t.line_item.for_finaid})
    payments = []
    for p in Transfer.objects.filter(user=student, source__isnull=True,
                                     line_item=iac.default_payments_lineitemtype()).select_related(
                                         'recorded_by').order_by('id'):
        payments.append({'transfer': p, 'amount': p.amount_dec, 'date': p.timestamp,
                         'method': p.get_payment_method_display() or 'Unknown',
                         'transaction_id': p.transaction_id,
                         'at_checkin': p.checkin_record_id is not None,
                         'recorded_by': (p.recorded_by.username if p.recorded_by else '')})
    grant = iac.latest_finaid_grant()
    balance = iac.amount_due()
    return {
        'items': items,
        'amount_requested': iac.amount_requested(),
        'finaid': iac.amount_finaid(),
        'grant': grant,
        'sibling_discount': iac.amount_siblingdiscount(),
        'payments': payments,
        'amount_paid': iac.amount_paid(),
        'balance': balance,
        'balance_str': '%.2f' % balance,
        'checked_in': program.isCheckedIn(student),
        'ever_checked_in': Record.objects.filter(user=student, program=program, event__name='attended').exists(),
        'checkin_payment': dayof.checkin_payment(program, student),
    }


def summary_fingerprint(summary):
    """ Changes whenever anything shown on the page changes, so the page can
    tell staff to reload. """
    parts = [summary['balance_str'], str(summary['checked_in']), str(summary['finaid'])]
    parts += ['%s:%s:%s' % (i['transfer'].id, i['amount'], i['paid']) for i in summary['items']]
    parts += ['%s:%s' % (p['transfer'].id, p['amount']) for p in summary['payments']]
    return hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()[:16]


class OnsiteTroubleshooting(ProgramModuleObj):
    doc = """Day-of troubleshooting for students whose check-in is blocked: balance, financial aid,
    extra costs, card payment and receipts."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Payment Troubleshooting",
            "link_title": "Day-Of Payment Troubleshooting",
            "module_type": "onsite",
            "seq": 5,
            "choosable": 1,
            }

    def _url(self, view='troubleshooting', student=None):
        url = '/onsite/%s/%s' % (self.program.getUrlBase(), view)
        if student is not None:
            url += '?user=%d' % student.id
        return url

    def _student(self, request):
        try:
            student_id = int(request.GET.get('user') or request.POST.get('user'))
        except (TypeError, ValueError):
            raise Http404
        student = ESPUser.objects.filter(id=student_id).first()
        if student is None:
            raise Http404
        return student

    def _back(self, student):
        return HttpResponseRedirect(self._url(student=student))

    @main_call
    @needs_onsite
    def troubleshooting(self, request, tl, one, two, module, extra, prog):
        if 'user' in request.GET:
            student = self._student(request)
            summary = student_summary(prog, student)
            context = {
                'program': prog,
                'student': student,
                'summary': summary,
                'fingerprint': summary_fingerprint(summary),
                'finaid_defaults': {'amount_max': '0.00', 'percent': '100'},
                'user_manage_url': '/manage/userview?username=%s&program=%d' % (student.username, prog.id),
                'admin_transfers_url': '%s?user__id__exact=%d&line_item__program__id__exact=%d' % (
                    reverse('admin:accounting_transfer_changelist'), student.id, prog.id),
                'admin_postbacks_url': '%s?user__id__exact=%d&program__id__exact=%d' % (
                    reverse('admin:accounting_cybersourcepostback_changelist'), student.id, prog.id),
                'module': self,
            }
            for (key, value) in self.troubleshooting_extra_context(request, prog, student, summary).items():
                context[key] = value
            return render_to_response(self.baseDir() + 'student.html', request, context)

        if request.GET.get('op') == 'usersearch':
            # The standard user search form (users/usersearch_form.html)
            (result, found) = search_for_user(request, add_to_context={'tl': 'onsite', 'module': self.module.link_title})
            if not found:
                return result
            if not isinstance(result, ESPUser):
                raise ESPError('Please search for a single student.', log=False)
            return self._back(result)

        return render_to_response(self.baseDir() + 'search.html', request, {
            'program': prog,
            'owed': dayof.owed_after_checkin(prog),
            'module': self,
        })

    def troubleshooting_extra_context(self, request, prog, student, summary):
        """ Context for the card payment and receipt sections. """
        remake = None
        if request.GET.get('remake', '').isdigit():
            remake = Receipt.objects.filter(id=int(request.GET['remake']), program=prog, user=student,
                                            voided_at__isnull=True).first()
            if remake is not None:
                content = receipts.receipt_content(remake)
                remake.item_ids = content.get('item_ids')       # missing on older receipts: all items
                remake.payer_name_given = content.get('payer_name_given', '')
        return {
            'remake': remake,
            'can_receipt': receipts.can_have_receipt(prog, student),
            'receipt_items': receipts.allocate(prog, student),
            'receipts': Receipt.objects.filter(program=prog, user=student).select_related('recorded_by'),
            'card_result': request.GET.get('card_result', ''),
            'card_result_text': dayof_payments_result_text(request.GET.get('card_result', '')),
            'card_minimum': '%.2f' % dayof_payments.card_minimum(),
        }

    @aux_call
    @needs_onsite
    def troubleshooting_card(self, request, tl, one, two, module, extra, prog):
        """ Starts a card payment of the student's balance (or a custom
        amount): on this laptop (renders the auto-submitting CyberSource
        form, opened in a new tab) or by QR code on their phone. """
        if request.method != 'POST':
            raise Http404
        student = self._student(request)
        channel = 'qr' if request.POST.get('channel') == 'qr' else 'laptop'
        try:
            recorded_by = dayof.real_user(request)
            custom = None
            if request.POST.get('custom'):
                custom = dayof.parse_amount(request.POST.get('amount'))
            checkout = dayof_payments.student_checkout(
                prog, student, channel, recorded_by, custom_amount=custom,
                description=request.POST.get('description', ''),
                below_minimum_reason=request.POST.get('below_minimum_reason', '') if request.POST.get('below_minimum') else '',
                expected_balance=request.POST.get('expected_balance', ''))
            return dayof_payments.checkout_page(
                request, checkout, status_url='%s?user=%d' % (self._url('troubleshooting_status'), student.id),
                back_url=self._url(student=student), paid_when='balance',
                extra={'known_card_payments': json.dumps([p.id for p in Transfer.objects.filter(
                    user=student, source__isnull=True, line_item__program=prog, line_item__for_payments=True,
                    payment_method='card')])})
        except ValueError as e:
            messages.error(request, str(e))
            return self._back(student)

    @aux_call
    @needs_onsite
    def troubleshooting_status(self, request, tl, one, two, module, extra, prog):
        """ For the page to poll: what the student's account looks like now. """
        student = self._student(request)
        summary = student_summary(prog, student)
        data = {
            'fingerprint': summary_fingerprint(summary),
            'balance': summary['balance_str'],
            'checked_in': summary['checked_in'],
            'card_payments': [{'id': p['transfer'].id, 'amount': '%.2f' % p['amount'],
                               'transaction_id': p['transaction_id']}
                              for p in summary['payments'] if p['transfer'].payment_method == 'card'],
        }
        return HttpResponse(json.dumps(data), content_type='application/json')

    def _post_action(self, request, prog, action):
        """ Runs action(student, recorded_by) for a POST from
        the troubleshooting page, refusing it if the balance changed since
        the page was loaded, and reports the result as a message. """
        if request.method != 'POST':
            raise Http404
        student = self._student(request)
        try:
            recorded_by = dayof.real_user(request)
            iac = IndividualAccountingController(prog, student)
            dayof.check_expected_balance(iac, request.POST)
            message = action(student, recorded_by)
            if message:
                messages.success(request, message)
        except (ValueError, dayof.StaleBalance) as e:
            messages.error(request, str(e))
        return self._back(student)

    @aux_call
    @needs_onsite
    def troubleshooting_finaid_preview(self, request, tl, one, two, module, extra, prog):
        """ What the aid entered would do, for the confirm step. """
        student = self._student(request)
        try:
            amount_max = dayof.parse_amount(request.GET.get('amount_max'), 'dollar amount')
            percent = int(request.GET.get('percent') or 0)
        except ValueError as e:
            return HttpResponse(json.dumps({'error': str(e)}), content_type='application/json')
        (before, after, uncovered) = dayof.finaid_preview(prog, student, amount_max, percent)
        iac = IndividualAccountingController(prog, student)
        warnings = []
        if after > 0 and uncovered:
            warnings.append("Aid doesn't cover %s; %s still due." % (
                ', '.join('%s (%s)' % (text, dayof.money(amount)) for (text, amount) in uncovered),
                dayof.money(after)))
        if after < 0:
            warnings.append('%s has already paid %s, so this leaves them overpaid by %s (treasury refunds it).'
                            % (student.first_name, dayof.money(iac.amount_paid()), dayof.money(-after)))
        if iac.latest_finaid_grant() is not None:
            warnings.append('This replaces their current aid (%s).' % iac.latest_finaid_grant().terms)
        data = {'before': '%.2f' % before, 'after': '%.2f' % after, 'warnings': warnings,
                'confirm': 'Grant %s aid to %s: balance %s → %s?' % (
                    self._terms(amount_max, percent), student.name(), dayof.money(before), dayof.money(after))}
        return HttpResponse(json.dumps(data), content_type='application/json')

    @staticmethod
    def _terms(amount_max, percent):
        parts = []
        if amount_max:
            parts.append('up to %s' % dayof.money(amount_max))
        if percent:
            parts.append('%d%%' % percent)
        return ' + '.join(parts) or 'no'

    @aux_call
    @needs_onsite
    def troubleshooting_finaid(self, request, tl, one, two, module, extra, prog):
        def grant(student, recorded_by):
            amount_max = dayof.parse_amount(request.POST.get('amount_max'), 'dollar amount')
            try:
                percent = int(request.POST.get('percent') or 0)
            except ValueError:
                raise ValueError('The percent must be a whole number.')
            g = dayof.grant_finaid(prog, student, amount_max or None, percent or None,
                                   request.POST.get('reason'), recorded_by,
                                   email=bool(request.POST.get('email')))
            return 'Granted %s financial aid (%s). Balance is now %s.' % (
                student.name(), g.terms, dayof.money(IndividualAccountingController(prog, student).amount_due()))
        return self._post_action(request, prog, grant)

    @aux_call
    @needs_onsite
    def troubleshooting_checkin_adjust(self, request, tl, one, two, module, extra, prog):
        def adjust(student, recorded_by):
            paid = dayof.parse_amount(request.POST.get('actually_paid'), 'amount they paid')
            return dayof.adjust_checkin_payment(prog, student, paid, recorded_by)
        return self._post_action(request, prog, adjust)

    @aux_call
    @needs_onsite
    def troubleshooting_checkin(self, request, tl, one, two, module, extra, prog):
        """ Checks the student in, as check-in would (a first check-in records
        their balance as paid in cash/check). """
        def checkin(student, recorded_by):
            with transaction.atomic():
                (record, payment) = dayof.check_in_student(prog, student, recorded_by)
            return dayof.checkin_message(student, record, payment)
        return self._post_action(request, prog, checkin)

    @aux_call
    @needs_onsite
    def troubleshooting_undo_checkin(self, request, tl, one, two, module, extra, prog):
        """ Undoes the student's check-in, and the cash/check payment it
        recorded, as the check-in page's "undo check-in" does. """
        def undo(student, recorded_by):
            record = Record.objects.filter(user=student, program=prog, event__name='attended').order_by('-time').first()
            if record is None or not prog.isCheckedIn(student):
                raise ValueError('%s isn\'t checked in.' % student.name())
            payment = Transfer.objects.filter(checkin_record=record).first()
            dayof.undo_check_in(record)
            dayof.logger.info('%s undid the check-in of %s (%s)', recorded_by.username if recorded_by else 'unknown',
                              student.username, prog.niceName())
            message = 'Undid %s\'s check-in.' % student.name()
            if payment is not None:
                message += ' Removed the %s cash/check payment it recorded.' % dayof.money(payment.amount_dec)
            return message
        return self._post_action(request, prog, undo)

    @aux_call
    @needs_onsite
    def troubleshooting_record_payment(self, request, tl, one, two, module, extra, prog):
        """ Records money received outside the site's own payment flows (cash
        or a check, or a card payment taken elsewhere), of any amount. """
        def record(student, recorded_by):
            amount = dayof.parse_amount(request.POST.get('amount'))
            method = request.POST.get('method') or 'cash_check'
            if method not in dict(Transfer.PAYMENT_METHOD_CHOICES):
                raise ValueError('Choose how they paid.')
            iac = IndividualAccountingController(prog, student)
            due = iac.amount_due()
            if amount <= 0:
                raise ValueError('Enter the amount they paid.')
            if amount > due and not request.POST.get('overpay'):
                raise ValueError('%s is more than the %s they owe. Tick "they paid more than they owe" '
                                 'if that\'s right.' % (dayof.money(amount), dayof.money(due)))
            payment = dayof.record_payment(prog, student, amount, recorded_by, method,
                                           (request.POST.get('reference') or '').strip()[:200])
            return 'Recorded %s (%s) from %s. They now owe %s.' % (
                dayof.money(amount), payment.get_payment_method_display().lower(), student.name(),
                dayof.money(iac.amount_due()))
        return self._post_action(request, prog, record)

    @aux_call
    @needs_onsite
    def troubleshooting_extracosts(self, request, tl, one, two, module, extra, prog):
        """ The student's extra costs (preorder items), editable by staff even
        if already paid for (which can leave the student overpaid; that needs
        confirming). """
        student = self._student(request)
        extracosts = prog.getModule('StudentExtraCosts')
        if extracosts is None:
            raise ESPError('This program has no extra costs module.', log=False)
        if request.method == 'POST':
            try:
                dayof.check_expected_balance(IndividualAccountingController(prog, student), request.POST)
            except dayof.StaleBalance as e:
                messages.error(request, str(e))
                return HttpResponseRedirect(self._url('troubleshooting_extracosts', student))
        recorded_by = dayof.real_user(request)
        extracosts.request = request
        extracosts.user = student

        def done():
            messages.success(request, 'Saved %s\'s extra costs. Balance is now %s.' % (
                student.name(), dayof.money(IndividualAccountingController(prog, student).amount_due())))
            return self._back(student)
        return extracosts.extracosts_page(request, tl, prog, student, troubleshooting={
            'template': self.baseDir() + 'extracosts.html',
            'context': {'student': student, 'program': prog, 'module': self,
                        'back_url': self._url(student=student)},
            'done': done,
            'recorded_by': recorded_by,
        })

    def _receipt(self, request, prog):
        try:
            receipt_id = int(request.GET.get('receipt') or request.POST.get('receipt'))
        except (TypeError, ValueError):
            raise Http404
        receipt = Receipt.objects.filter(id=receipt_id, program=prog, user__isnull=False).first()
        if receipt is None:
            raise Http404
        return receipt

    def _receipt_urls(self, receipt):
        return {
            'pdf': '%s?receipt=%d' % (self._url('troubleshooting_receipt_pdf'), receipt.id),
            'void': self._url('troubleshooting_receipt_void'),
            'back': self._url(student=receipt.user),
            'remake': '%s&remake=%d#receipt' % (self._url(student=receipt.user), receipt.id),
        }

    @aux_call
    @needs_onsite
    def troubleshooting_receipt(self, request, tl, one, two, module, extra, prog):
        """ Makes a receipt for the chosen items (all by default). """
        if request.method != 'POST':
            raise Http404
        student = self._student(request)
        try:
            recorded_by = dayof.real_user(request)
            item_ids = [int(i) for i in request.POST.getlist('items') if i.isdigit()]
            content = receipts.student_receipt_content(prog, student, item_ids,
                                                       (request.POST.get('payer_name') or '').strip())
            replaces = None
            if request.POST.get('replaces'):
                replaces = Receipt.objects.filter(id=int(request.POST['replaces']) if request.POST['replaces'].isdigit() else 0,
                                                  program=prog, user=student, voided_at__isnull=True).first()
                if replaces is None:
                    raise ValueError('The receipt being replaced is already void or isn\'t this student\'s.')
            #   Remaking one is fine even if they no longer qualify (e.g. check-in undone)
            if replaces is None and not receipts.can_have_receipt(prog, student):
                raise ValueError('%s isn\'t checked in and hasn\'t paid by card, so they can\'t have a receipt yet.'
                                 % student.name())
            with transaction.atomic():
                receipt = receipts.create_receipt(prog, content, recorded_by, user=student)
                if replaces is not None:
                    receipts.void_receipt(replaces, recorded_by)
                    messages.success(request, 'Receipt %d replaces receipt %d, which is now void.'
                                     % (receipt.number, replaces.number))
        except ValueError as e:
            messages.error(request, str(e))
            return self._back(student)
        return HttpResponseRedirect('%s?receipt=%d' % (self._url('troubleshooting_receipt_view'), receipt.id))

    @aux_call
    @needs_onsite
    def troubleshooting_receipt_view(self, request, tl, one, two, module, extra, prog):
        receipt = self._receipt(request, prog)
        return receipts.receipt_page(request, receipt, self._receipt_urls(receipt))

    @aux_call
    @needs_onsite
    def troubleshooting_receipt_pdf(self, request, tl, one, two, module, extra, prog):
        return receipts.pdf_response(self._receipt(request, prog))

    @aux_call
    @needs_onsite
    def troubleshooting_receipt_void(self, request, tl, one, two, module, extra, prog):
        if request.method != 'POST':
            raise Http404
        receipt = self._receipt(request, prog)
        recorded_by = dayof.real_user(request)
        receipts.void_receipt(receipt, recorded_by)
        messages.success(request, 'Voided receipt %d.' % receipt.number)
        return self._back(receipt.user)

    class Meta:
        proxy = True
        app_label = 'modules'
