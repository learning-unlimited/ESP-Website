""" Payment issues for treasury, listed (and resolved) at the top of a
program's credit card viewer page (CreditCardViewer.viewpay):

- problem CyberSource postbacks for the program: payments not recorded,
  held for review, or recorded but not matched to items;
- problem postbacks that couldn't be linked to any program or student,
  listed on the programs they most likely belong to by date;
- students who have paid more than they now owe.

Resolving an issue only records a note (PaymentIssueResolution); it doesn't
move any money. """
from __future__ import absolute_import

import calendar
import json
from decimal import Decimal, InvalidOperation

from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Min, Q
from django.utils import timezone

from esp.accounting.controllers import IndividualAccountingController
from esp.accounting.models import CybersourcePostback, PaymentIssueResolution, Transfer
from esp.program.models import Program


#   Postback statuses that need someone to deal with them
OPEN_STATUSES = ('failed', 'review_hold', 'needs_review')

#   (label, one-line summary) for each of those
STATUS_TEXT = {
    'failed': ('Payment not recorded',
               'The card was probably charged, but the website has no record of the payment.'),
    'review_hold': ('Held for review by CyberSource',
                    'CyberSource is holding this payment for review; the card may have been '
                    'charged. Nothing is recorded on the website yet.'),
    'needs_review': ('Paid, but items not marked paid',
                     "The payment is recorded and counts toward the student's balance, but the "
                     "website couldn't tell which of their items it paid for."),
}
UNLINKED_SUMMARY = ("The website received a payment notice it couldn't read, so it doesn't know "
                    "who paid or whether the payment was recorded.")

#   How to resolve each kind of payment issue, shown on the issue's card.
#   Keyed by postback status, plus 'unlinked' and 'overpaid'.
ISSUE_STEPS = {
    'failed': [
        'Look up the transaction in CyberSource and check whether the charge went through.',
        'If it did, use "Record this payment" below (the amount and transaction ID are filled in). '
        'If the student had already paid for the same things, refund this charge in CyberSource instead.',
        "If it didn't go through, there's nothing to undo.",
        'Mark resolved, saying which you did.',
    ],
    'review_hold': [
        'Find the transaction in CyberSource and accept or reject it there.',
        'If you accepted it, use "Record this payment" below so the website knows they paid.',
        'Mark resolved, saying which you did.',
    ],
    'needs_review': [
        "Their balance already counts this payment, so nothing more is owed. Open their line items & "
        "payments (link below) and compare what they have with what they meant to buy (see the "
        "detail above for what didn't match).",
        'If they paid for something they no longer have (e.g. an item removed while they were paying), '
        'contact the student to ask whether they want it added back or refunded, then do that '
        '(refunds are done in CyberSource).',
        'Mark resolved, saying what you did.',
    ],
    'unlinked': [
        'Search CyberSource for a payment around this time (and of this amount, if shown) to find who paid and for what.',
        'If it was a real charge for this program, find the student in the table below and use '
        '"Add a payment" with its CyberSource transaction ID (if it was for another program, do that on that '
        "program's page). If it was already recorded, or the charge failed, there's nothing to add.",
        'Mark resolved, saying what you found.',
    ],
    'overpaid': [
        'Check "What happened" above to see why: e.g. financial aid approved after they paid, a duplicate payment, or a removed item.',
        "If the student or their family asks for a refund: refund card payments in CyberSource (their "
        "transaction IDs are under their line items & payments); cash/check payments need a refund by check.",
        'Mark resolved once it is settled (refunded, or they want to keep it as a donation), saying what you did. '
        'If their balance changes again later, the issue reopens.',
    ],
}

#   A postback that can't be linked to a program is listed on each program
#   starting within this many months of it (or else on the next one after it)
UNLINKED_MONTHS = 2


class PaymentIssueError(Exception):
    """ A request to change a payment issue that can't be carried out; the
    message is shown to the admin. """


def _user_dict(user):
    return {'id': user.id, 'name': user.name(), 'username': user.username}


def _add_months(when, months):
    month0 = when.month - 1 + months
    year = when.year + month0 // 12
    month = month0 % 12 + 1
    return when.replace(year=year, month=month, day=min(when.day, calendar.monthrange(year, month)[1]))


def postback_value(postback, key):
    """ A field of the raw postback, or '' if it's missing or unreadable. """
    try:
        data = json.loads(postback.post_data)
    except ValueError:
        return ''
    if not isinstance(data, dict):
        return ''
    value = data.get(key, '')
    if isinstance(value, list):
        value = value[-1] if value else ''
    return value if isinstance(value, str) else ''


def postback_amount(postback):
    """ The amount a postback says was charged, or None if it doesn't say. """
    try:
        return Decimal(postback_value(postback, 'req_amount') or postback_value(postback, 'auth_amount'))
    except InvalidOperation:
        return None


def linkable_payment_amounts(row):
    """ The amounts a new payment for a student could be for so that
    IndividualAccountingController.link_paid_transfers() can mark items paid
    by it. That walks the student's items oldest first, marking unpaid ones
    paid, until their running total reaches all payments + sibling discount +
    aid, and fails unless it lands exactly; so a new payment links cleanly
    only if it brings that target to one of the running totals. Takes a row
    from ProgramAccountingController.student_payment_rows(). """
    credits = row['amount_paid'] + row['amount_siblingdiscount'] + row['amount_finaid']
    amounts = []
    total = Decimal('0')
    for transfer in row['transfers']:
        if transfer.line_item.for_payments:
            continue
        total += transfer.amount_dec
        if total - credits > 0 and total - credits not in amounts:
            amounts.append(total - credits)
    return amounts


def _program_starts():
    """ [(program, first class time block)] for the programs that take
    CyberSource payments and have time blocks. """
    programs = Program.objects.filter(
        program_modules__handler='CreditCardModule_Cybersource',
        event__event_type__description='Class Time Block',
    ).annotate(start=Min('event__start'))
    return [(program, program.start) for program in programs]


def programs_for_unlinked(timestamp, starts):
    """ The programs a postback that couldn't be linked to a program is listed
    on, as (programs, near): each one starting within UNLINKED_MONTHS of it
    (near=True), or else the next one to start after it (near=False). starts
    is from _program_starts(). """
    near = [program for (program, start) in starts
            if _add_months(start, -UNLINKED_MONTHS) <= timestamp <= _add_months(start, UNLINKED_MONTHS)]
    if near:
        return (near, True)
    later = [(start, program) for (program, start) in starts if start > timestamp]
    if later:
        return ([min(later, key=lambda pair: pair[0])[1]], False)
    return ([], False)


def _latest_resolutions(resolutions, key):
    """ {key(resolution): latest resolution}, resolutions being in order. """
    latest = {}
    for resolution in resolutions:
        latest[key(resolution)] = resolution
    return latest


def _resolution_dict(resolution):
    return {
        'amount': resolution.amount,
        'note': resolution.note,
        'resolved_at': resolution.resolved_at,
        'resolved_by': resolution.resolved_by.name() if resolution.resolved_by else 'unknown',
        'reopened_at': resolution.reopened_at,
        'reopened_by': resolution.reopened_by.name() if resolution.reopened_by else '',
    }


def _postback_card(postback, steps_key, summary, match_note=''):
    label = STATUS_TEXT[postback.status][0]
    detail = postback.status_detail.strip()
    detail_long = ''
    if 'Traceback (most recent call last)' in detail:
        detail, detail_long = 'The website hit an error while processing it.', detail
    return {
        'id': postback.id,
        'anchor': 'issue-postback-%d' % postback.id,
        'timestamp': postback.timestamp,
        'admin_url': reverse('admin:accounting_cybersourcepostback_change', args=(postback.id,)),
        'user': _user_dict(postback.user) if postback.user else None,
        'amount': postback_amount(postback),
        'transaction_id': postback.transaction_id,
        'status': postback.status,
        'status_label': label,
        'todo': summary,
        'detail': detail,
        'detail_long': detail_long,
        'match_note': match_note,
        'steps': ISSUE_STEPS[steps_key],
        #   A charge that may have gone through but wasn't recorded
        'can_record': bool(postback.user_id and postback.status in ('failed', 'review_hold')
                           and not postback.transfer_id),
    }


def _unlinked_match_note(program, programs, near):
    others = [p for p in programs if p != program]
    if others:
        return ('Could be for this program or for %s: it came in within %d months of their start dates, '
                'so it is listed on each of their pages.' % (', '.join(p.niceName() for p in others), UNLINKED_MONTHS))
    if near:
        return 'Listed here because it came in within %d months of this program\'s start date.' % UNLINKED_MONTHS
    return ('No program started within %d months of this payment; listed here because this was the next '
            'program to start after it.' % UNLINKED_MONTHS)


def payment_issues(program, rows):
    """ The payment issues for a program, as the context for
    creditcardviewer/payment_issues.html. rows is
    ProgramAccountingController.student_payment_rows() for the program's
    students (all of them, so overpaid students can be found); each row also
    gets 'issues': [{anchor, label}] for its open issues. """
    rows_by_id = dict((row['student'].id, row) for row in rows)

    #   This program's problem postbacks, and the unlinked ones listed here
    postbacks = list(CybersourcePostback.objects.filter(program=program, status__in=OPEN_STATUSES)
                     .select_related('user').order_by('-timestamp'))
    starts = None
    unlinked = []
    for postback in (CybersourcePostback.objects.filter(program__isnull=True, status__in=OPEN_STATUSES)
                     .select_related('user').order_by('-timestamp')):
        if starts is None:
            starts = _program_starts()
        (programs, near) = programs_for_unlinked(postback.timestamp, starts)
        if program in programs:
            unlinked.append((postback, _unlinked_match_note(program, programs, near)))

    resolutions = list(PaymentIssueResolution.objects.filter(
        Q(program=program) | Q(postback__in=[postback for (postback, _) in unlinked])
    ).select_related('resolved_by', 'reopened_by', 'user', 'postback', 'postback__user'))
    by_postback = _latest_resolutions([r for r in resolutions if r.kind == 'postback'], lambda r: r.postback_id)
    by_student = _latest_resolutions([r for r in resolutions if r.kind == 'overpayment'], lambda r: r.user_id)
    manual_payments = [r for r in resolutions if r.kind == 'manual_payment']

    #   Payments recorded by hand (from a student's row or a postback) say so,
    #   with the note, wherever the payment is listed
    by_transfer = dict((r.transfer_id, r) for r in resolutions if r.transfer_id)
    for row in rows:
        for transfer in row['transfers']:
            resolution = by_transfer.get(transfer.id)
            transfer.recorded_by_hand = (
                'recorded by hand by %s on %s: %s' % (
                    resolution.resolved_by.name() if resolution.resolved_by else 'unknown',
                    resolution.resolved_at.strftime('%Y-%m-%d'), resolution.note)
                if resolution else '')

    def is_resolved(resolution):
        return resolution is not None and resolution.reopened_at is None

    open_postbacks = []
    for postback in postbacks:
        if is_resolved(by_postback.get(postback.id)):
            continue
        card = _postback_card(postback, postback.status, STATUS_TEXT[postback.status][1])
        row = rows_by_id.get(postback.user_id)
        card['in_table'] = row is not None
        #   None (no amount check on the form) if they aren't in the table
        card['link_amounts'] = ' '.join('%.2f' % a for a in linkable_payment_amounts(row)) if row else None
        open_postbacks.append(card)
    open_unlinked = []
    for (postback, note) in unlinked:
        if not is_resolved(by_postback.get(postback.id)):
            card = _postback_card(postback, 'unlinked', UNLINKED_SUMMARY, note)
            card['can_record'] = False
            card['in_table'] = postback.user_id in rows_by_id
            open_unlinked.append(card)

    overpaid = []
    for row in rows:
        if not (row['amount_paid'] > 0 and row['amount_due'] < 0):
            continue
        amount = -row['amount_due']
        latest = by_student.get(row['student'].id)
        if is_resolved(latest) and latest.amount == amount:
            continue
        history = [{'when': t.timestamp,
                    'text': 'Paid $%.2f%s' % (t.amount_dec, ' (%s)' % t.recorded_by_hand if t.recorded_by_hand
                                              else ' by %s' % t.get_payment_method_display().lower()
                                              if t.payment_method else '')}
                   for t in row['transfers'] if t.line_item.for_payments]
        if row['grant']:
            history.append({'when': row['grant'].timestamp,
                            'text': 'Financial aid approved (%s grant)' % row['grant'].terms})
        history.sort(key=lambda event: event['when'])
        overpaid.append({
            'anchor': 'issue-overpaid-%d' % row['student'].id,
            'user': _user_dict(row['student']),
            'amount_paid': row['amount_paid'],
            'amount_owed': row['amount_paid'] + row['amount_due'],
            'overpaid': amount,
            'history': history,
            'previous': _resolution_dict(latest) if latest else None,
            'steps': ISSUE_STEPS['overpaid'],
        })

    #   Resolved issues and payments recorded by hand, newest first. An
    #   overpaid student whose amount changed since is open again (shown with
    #   the earlier resolution).
    resolved = []
    for resolution in list(by_postback.values()) + list(by_student.values()) + manual_payments:
        if not is_resolved(resolution):
            continue
        if resolution.kind == 'manual_payment':
            entry = {'kind': 'manual_payment', 'id': resolution.id,
                     'user': _user_dict(resolution.user) if resolution.user else None,
                     'summary': 'Payment recorded by hand ($%.2f%s)' % (
                         resolution.amount, ', transaction %s' % resolution.transfer.transaction_id
                         if resolution.transfer else '')}
        elif resolution.kind == 'postback':
            postback = resolution.postback
            amount = postback_amount(postback)
            if postback.status == 'processed':
                label = 'Payment recorded'
            else:
                label = STATUS_TEXT.get(postback.status, ('Payment notice',))[0]
            entry = {'kind': 'postback', 'id': postback.id, 'postback_id': postback.id,
                     'admin_url': reverse('admin:accounting_cybersourcepostback_change', args=(postback.id,)),
                     'user': _user_dict(postback.user) if postback.user else None,
                     'summary': '%s%s' % (label, ' ($%.2f)' % amount if amount is not None else '')}
        else:
            row = rows_by_id.get(resolution.user_id)
            if row is not None and -row['amount_due'] != resolution.amount and row['amount_due'] < 0:
                continue
            entry = {'kind': 'overpayment', 'id': resolution.user_id,
                     'user': _user_dict(resolution.user) if resolution.user else None,
                     'summary': 'Overpaid by $%.2f' % resolution.amount}
        entry.update(_resolution_dict(resolution))
        resolved.append(entry)
    resolved.sort(key=lambda entry: entry['resolved_at'], reverse=True)

    #   Cross-links from the students' rows to their open issues
    for row in rows:
        row['issues'] = []
    for card in open_postbacks:
        if card['in_table']:
            rows_by_id[card['user']['id']]['issues'].append({'anchor': card['anchor'], 'label': card['status_label']})
    for card in overpaid:
        rows_by_id[card['user']['id']]['issues'].append(
            {'anchor': card['anchor'], 'label': 'Overpaid by $%.2f' % card['overpaid']})

    return {
        'postbacks': open_postbacks,
        'overpaid': overpaid,
        'orphans': open_unlinked,
        'resolved': resolved,
        'num_open': len(open_postbacks) + len(overpaid) + len(open_unlinked),
    }


##  Changes made from the payment issues box

def _postback_for(program, postback_id):
    """ A postback listed (or listable) on this program's page. """
    postback = CybersourcePostback.objects.filter(id=postback_id).select_related('user', 'program').first()
    if postback is None or (postback.program_id is not None and postback.program_id != program.id):
        raise PaymentIssueError('That payment notice is not for this program.')
    return postback


def _require_note(note):
    note = (note or '').strip()
    if not note:
        raise PaymentIssueError('Please say what you did about it.')
    return note


def resolve_postback(program, postback_id, admin, note):
    postback = _postback_for(program, postback_id)
    return PaymentIssueResolution.objects.create(
        kind='postback', postback=postback, user=postback.user, program=postback.program,
        amount=postback_amount(postback), note=_require_note(note), resolved_by=admin)


def resolve_overpayment(program, student, amount, admin, note):
    return PaymentIssueResolution.objects.create(
        kind='overpayment', user=student, program=program, amount=amount, note=_require_note(note),
        resolved_by=admin)


def reopen_postback(program, postback_id, admin):
    postback = _postback_for(program, postback_id)
    _reopen(PaymentIssueResolution.objects.filter(kind='postback', postback=postback), admin)


def reopen_overpayment(program, student, admin):
    _reopen(PaymentIssueResolution.objects.filter(kind='overpayment', program=program, user=student), admin)


def _reopen(resolutions, admin):
    latest = resolutions.order_by('-resolved_at', '-id').first()
    if latest is None or latest.reopened_at is not None:
        raise PaymentIssueError('That issue is not resolved.')
    latest.reopened_by = admin
    latest.reopened_at = timezone.now()
    latest.save()


def record_payment(program, student, amount, transaction_id, admin, note, postback_id=None):
    """ Records a payment made outside the website's normal flow (e.g. one
    whose postback failed) and marks the student's items paid by it if the
    amount matches them. Returns (payment, linked): linked is False if the
    amount didn't match their items, in which case the payment still counts
    toward their balance but no items are marked paid by it. Who recorded it
    and why is kept as a PaymentIssueResolution; recording it from a postback
    also links the postback to it and resolves that issue. """
    note = (note or '').strip()
    if not note:
        raise PaymentIssueError('Please add a note saying what the payment is.')
    transaction_id = (transaction_id or '').strip()
    if not transaction_id:
        raise PaymentIssueError('Please enter the CyberSource transaction ID.')
    if amount is None or amount <= 0:
        raise PaymentIssueError('Please enter an amount greater than $0.')
    existing = Transfer.objects.filter(source__isnull=True, line_item__for_payments=True,
                                       transaction_id=transaction_id).select_related('user').first()
    if existing is not None:
        raise PaymentIssueError('A payment with transaction ID %s is already recorded (for %s), so it was '
                                'not recorded again.' % (transaction_id, existing.user.name() if existing.user else 'nobody'))
    postback = None
    if postback_id:
        postback = _postback_for(program, postback_id)
        if postback.user_id != student.id or postback.transfer_id:
            raise PaymentIssueError('That payment notice is for someone else, or its payment is already recorded.')

    iac = IndividualAccountingController(program, student)
    with transaction.atomic():
        payment = iac.submit_payment(amount, transaction_id, link_transfers=False,
                                     payment_method='card', recorded_by=admin)
        try:
            with transaction.atomic():
                iac.link_paid_transfers(payment)
            linked = True
        except ValueError:
            linked = False
        if postback is not None:
            postback.transfer = payment
            postback.status = 'processed'
            postback.status_detail = ('%s\n\nPayment recorded by hand by %s on %s.' % (
                postback.status_detail, admin.name(), timezone.now().strftime('%Y-%m-%d %H:%M'))).strip()
            postback.save()
        PaymentIssueResolution.objects.create(
            kind='postback' if postback is not None else 'manual_payment', postback=postback,
            transfer=payment, user=student, program=program, amount=payment.amount_dec,
            note=note, resolved_by=admin)
    return (payment, linked)
