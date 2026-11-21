"""Shared logic for day-of (onsite) operations: who is doing something, and
checking students in.

Who did something: ``real_user(request)`` gives the real account behind a
request (an admin morphed into another account counts as the admin).

Checking in: a staff-processed check-in means the student paid whatever they
owed at that moment, in cash or check (volunteers collect the amount printed
on the schedule). ``check_in_student`` records that payment along with the
check-in, and ``undo_check_in`` removes both.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction

from esp.accounting.controllers import IndividualAccountingController
from esp.accounting.models import FinancialAidGrant, Transfer
from esp.dbmail.models import send_mail
from esp.program.models import FinancialAidRequest
from esp.users.models import ESPUser, Record, RecordType

logger = logging.getLogger(__name__)

def real_user(request):
    """ The account actually behind the request: if an admin has morphed into
    someone (e.g. the onsite account or a student), the admin. """
    if 'user_morph' in request.session:
        old_id = request.session['user_morph'].get('olduser_id')
        if old_id:
            old = ESPUser.objects.filter(id=old_id).first()
            if old is not None:
                return old
    return request.user



@transaction.atomic
def check_in_student(program, student, recorded_by=None, record_payment=True):
    """ Checks a student in, if they aren't already, and on their first
    check-in for the program records a cash/check payment for whatever they
    owe at that moment (unless record_payment is False: onsite registration
    of someone who hasn't paid). Returns (record, payment): record is None if
    they were already checked in, payment is None if nothing was recorded. """
    # Serialize check-ins of the same student (e.g. two scanners at once)
    ESPUser.objects.select_for_update().filter(id=student.id).first()
    if program.isCheckedIn(student):
        return (None, None)
    first_checkin = not Record.objects.filter(user=student, program=program,
                                              event__name='attended').exists()
    record = Record.objects.create(user=student, program=program,
                                   event=RecordType.objects.get(name='attended'))
    payment = None
    if first_checkin:
        iac = IndividualAccountingController(program, student)
        iac.ensure_required_transfers()
        due = iac.amount_due()
        if due > 0 and record_payment:
            payment = iac.submit_payment(due, payment_method='cash_check', recorded_by=recorded_by, checkin_record=record)
    return (record, payment)


def check_in_request(program, student, request):
    """ check_in_student, recording who did it from the request. """
    recorded_by = real_user(request)
    return check_in_student(program, student, recorded_by)


def checkin_message(student, record, payment):
    """ What to tell staff about a check-in. """
    who = '%s (%s)' % (student.name(), student.id)
    if record is None:
        msg = '%s is already checked in.' % who
    elif payment is not None:
        msg = '%s is now checked in. Recorded $%.2f paid in cash/check.' % (who, payment.amount_dec)
    else:
        msg = '%s is now checked in.' % who
    return msg


@transaction.atomic
def delete_checkin_payments(record):
    """ Deletes the payment(s) a check-in record implied, first unmarking the
    items they paid for. """
    for payment in Transfer.objects.filter(checkin_record=record):
        Transfer.objects.filter(paid_in=payment).update(paid_in=None)
        payment.delete()


@transaction.atomic
def undo_check_in(record):
    """ Deletes a check-in record and the payment it implied. """
    delete_checkin_payments(record)
    record.delete()


#   Day-of troubleshooting


class StaleBalance(Exception):
    """ The balance changed since the page was loaded. """


def money(amount):
    return '$%.2f' % amount


def check_expected_balance(iac, data):
    """ Refuses (raises StaleBalance) if the balance the person was looking
    at, sent as 'expected_balance', isn't the student's balance now (e.g.
    a card payment landed, or another tab changed something). """
    expected = (data.get('expected_balance') or '').strip()
    current = '%.2f' % iac.amount_due()
    if expected != current:
        raise StaleBalance("%s's balance is now %s, which isn't what this page showed. Nothing was "
                           "changed; please look over the page again." % (iac.user.name(), money(iac.amount_due())))


def parse_amount(text, what='amount'):
    """ A non-negative dollar amount typed into a form, as a Decimal. """
    try:
        amount = Decimal((text or '').strip().lstrip('$') or 'x').quantize(Decimal('0.01'))
    except InvalidOperation:
        raise ValueError('Please enter the %s as a number of dollars.' % what)
    if amount < 0:
        raise ValueError('The %s can\'t be negative.' % what)
    return amount


def checkin_payment(program, student):
    """ The payment the student's first check-in implied, if any. """
    return Transfer.objects.filter(user=student, checkin_record__program=program,
                                   checkin_record__event__name='attended').order_by('id').first()


@transaction.atomic
def adjust_checkin_payment(program, student, actually_paid, recorded_by):
    """ The student paid only actually_paid at check-in, not the balance the
    check-in recorded: changes that payment (deleting it if $0), re-marks
    their items paid as far as it goes. Returns a message saying what it did. """
    payment = checkin_payment(program, student)
    if payment is None:
        raise ValueError('%s has no payment recorded at check-in to change.' % student.name())
    recorded = payment.amount_dec
    if actually_paid >= recorded:
        raise ValueError('That isn\'t less than the %s recorded at check-in.' % money(recorded))
    Transfer.objects.filter(paid_in=payment).update(paid_in=None)
    iac = IndividualAccountingController(program, student)
    if actually_paid == 0:
        payment.delete()
    else:
        Transfer.objects.filter(id=payment.id).update(amount_dec=actually_paid)
        payment.refresh_from_db()
        _link_as_far_as_possible(iac, payment)
    message = 'Paid %s of the %s recorded at check-in; still owes %s.' % (
        money(actually_paid), money(recorded), money(iac.amount_due()))
    logger.info('%s (%s) by %s: %s', student.username, program.niceName(),
                recorded_by.username if recorded_by else 'unknown', message)
    return message


def _link_as_far_as_possible(iac, payment):
    """ Marks the unpaid items this payment covers (oldest first) as paid by
    it, stopping before the first item it can't fully cover. """
    remaining = payment.amount_dec
    #   Items aid or the sibling discount cover don't need paying for
    credit = iac.amount_finaid() + iac.amount_siblingdiscount()
    other_paid = iac.amount_paid() - payment.amount_dec
    available = remaining + credit + other_paid
    covered = Decimal('0')
    for item in iac.get_transfers().filter(line_item__for_payments=False).exclude(
            line_item__text__in=iac.finaid_items).order_by('id'):
        covered += item.amount_dec
        if covered > available:
            break
        if item.paid_in_id is None:
            item.paid_in = payment
            item.save()


@transaction.atomic
def record_payment(program, student, amount, recorded_by, payment_method='cash_check', reference=''):
    """ Money received outside the site's payment flows (cash or a check, or
    a card payment taken elsewhere), of any amount. """
    iac = IndividualAccountingController(program, student)
    payment = iac.submit_payment(amount, transaction_id=reference, payment_method=payment_method,
                                 recorded_by=recorded_by, link_transfers=False)
    _link_as_far_as_possible(iac, payment)
    return payment


def owed_after_checkin(program):
    """ Students who are checked in (or were) and still owe money, with what
    they owe, largest first. """
    from esp.accounting.controllers import ProgramAccountingController
    students = ESPUser.objects.filter(record__program=program, record__event__name='attended').distinct()
    rows = [row for row in ProgramAccountingController(program).student_payment_rows(students)
            if row['amount_due'] > 0]
    rows.sort(key=lambda r: (-r['amount_due'], r['student'].last_name))
    return rows


def finaid_preview(program, student, amount_max, percent):
    """ What granting this aid would do: (balance before, balance after,
    uncovered) where uncovered lists (item text, amount) the student would
    still owe for because aid doesn't cover them. Changes nothing. """
    from esp.accounting.controllers import ProgramAccountingController
    iac = IndividualAccountingController(program, student)
    iac.ensure_required_transfers()
    before = iac.amount_due()
    grant = FinancialAidGrant(amount_max_dec=amount_max, percent=percent)
    sibling = iac.amount_siblingdiscount()
    aid = ProgramAccountingController.compute_finaid(iac.amount_requested(for_finaid_only=True), sibling, grant)
    after = iac.amount_requested() - aid - sibling - iac.amount_paid()
    uncovered = [(t.line_item.text, t.amount_dec) for t in iac.get_transfers().filter(
        line_item__for_finaid=False, line_item__for_payments=False).exclude(
        line_item__text__in=iac.finaid_items).select_related('line_item')]
    return (before, after, uncovered)


@transaction.atomic
def grant_finaid(program, student, amount_max, percent, reason, recorded_by, email=False):
    """ Grants (or changes) a student's financial aid at day-of
    troubleshooting, creating their aid request if they never made one. """
    if not amount_max and not percent:
        raise ValueError('Enter a dollar amount or a percent of aid to grant.')
    if percent is not None and not 0 <= percent <= 100:
        raise ValueError('The percent must be between 0 and 100.')
    reason = (reason or '').strip()
    if not reason:
        raise ValueError('Please say briefly why aid is being granted.')
    who = (recorded_by.username if recorded_by else '')
    request = FinancialAidRequest.objects.filter(program=program, user=student).order_by('-id').first()
    line = 'Granted at day-of troubleshooting by %s: %s' % (who, reason)
    if request is None:
        request = FinancialAidRequest.objects.create(program=program, user=student, extra_explaination=line)
    else:
        request.extra_explaination = ('%s\n\n%s' % (request.extra_explaination or '', line)).strip()
    request.done = True
    request.save()
    grant = FinancialAidGrant.objects.filter(request=request).first() or FinancialAidGrant(request=request)
    grant.amount_max_dec = amount_max
    grant.percent = percent
    grant.granted_by = recorded_by
    grant.finalized = False
    grant.finalize()
    grant.refresh_from_db()
    if email:
        try:
            message = request.approval_email(grant)
            send_mail(message['subject'], message['body'], message['from'], message['to'])
        except Exception:
            logger.exception('Failed to send financial aid approval email to user %d', student.id)
    return grant
