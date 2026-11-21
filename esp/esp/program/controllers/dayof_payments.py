"""Day-of card payments: started at troubleshooting (a student's balance) or
the help desk (an anonymous sale), paid on the staff laptop or on the payer's
phone via a QR code link that needs no login.

Help desk sales use their own CyberSource identifier,
``<program id>/onsite-<sale id>:<total>``; esp.program.views.submit_transaction
sends postbacks with that form here and handles every other identifier exactly
as before. After paying, CyberSource sends the browser back through
submit_transaction, and ``return_url`` decides where it lands.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core import signing
from django.db import transaction
from django.utils import timezone

from esp.accounting.controllers import IndividualAccountingController
from esp.accounting.models import DayOfCardCheckout, OnsiteSale, Transfer
from esp.program.models import Program
from esp.tagdict.models import Tag
from esp.users.models import ESPUser

logger = logging.getLogger(__name__)

SALE_PREFIX = 'onsite-'
TOKEN_SALT = 'esp.dayof.pay'
TOKEN_MAX_AGE = 3600            # seconds a QR pay link works for
SESSION_KEY = 'dayof_pay_token'


class CheckoutError(ValueError):
    pass


def _owner_part(identifier):
    try:
        return identifier.split(':')[0].split('/')[1]
    except (AttributeError, IndexError):
        return ''


def is_sale_identifier(identifier):
    return _owner_part(identifier).startswith(SALE_PREFIX)


def sale_from_identifier(identifier):
    """ (program, sale) a help desk sale identifier names; either may be None. """
    program = None
    try:
        program = Program.objects.filter(id=int(identifier.split('/')[0])).first()
        sale_id = int(_owner_part(identifier)[len(SALE_PREFIX):])
    except (ValueError, AttributeError):
        return (program, None)
    sale = OnsiteSale.objects.filter(id=sale_id, program=program).first() if program else None
    return (program, sale)


@transaction.atomic
def record_sale_payment(sale, amount_paid, transaction_id):
    """ Marks a help desk sale paid by an accepted card payment. Returns the
    (postback status, detail) to log: anything unexpected is recorded but
    flagged for treasury. """
    sale = OnsiteSale.objects.select_for_update().get(id=sale.id)
    if sale.status in ('paid', 'review'):
        if sale.transaction_id == transaction_id:
            return ('processed', 'Repeat of an already-recorded payment.')
        return ('needs_review', 'This sale was already paid (transaction %s), so this may be a second '
                                'charge for it; refund one of them.' % sale.transaction_id)
    detail = ''
    status = 'processed'
    if sale.status == 'void':
        status = 'needs_review'
        detail = 'The sale had been voided before this payment arrived; refund it or un-void the sale. '
    sale.status = 'paid'
    if amount_paid != sale.total_dec:
        #   Not "paid": staff shouldn't hand over the goods
        sale.status = 'review'
        status = 'needs_review'
        detail += 'They paid $%.2f but the sale totals $%.2f. ' % (amount_paid, sale.total_dec)
    sale.method = 'card'
    sale.transaction_id = transaction_id[:64]
    sale.paid_at = timezone.now()
    sale.save()
    return (status, detail.strip())


def card_minimum():
    try:
        return Decimal(Tag.getTag('card_payment_minimum') or '0')
    except InvalidOperation:
        return Decimal('0')


def _check_minimum(amount, below_minimum_reason):
    minimum = card_minimum()
    if amount < minimum and not (below_minimum_reason or '').strip():
        raise CheckoutError('$%.2f is below the $%.2f card minimum. To charge it anyway, tick "charge below '
                            'the minimum" and say why.' % (amount, minimum))


def student_checkout(program, student, channel, recorded_by, custom_amount=None,
                     description='', below_minimum_reason='', expected_balance=None):
    """ Starts a card payment of a student's balance (or, with custom_amount,
    of that amount, which isn't matched to any items). Returns the
    DayOfCardCheckout. """
    iac = IndividualAccountingController(program, student)
    iac.ensure_required_transfers()
    due = iac.amount_due().quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if expected_balance is not None and '%.2f' % due != expected_balance:
        raise CheckoutError("%s's balance is now $%.2f, which isn't what the page showed. Nothing was "
                            "charged; please look over the page again." % (student.name(), due))
    if custom_amount is None:
        if due <= 0:
            raise CheckoutError('%s doesn\'t owe anything.' % student.name())
        amount = due
        identifier = iac.get_identifier()
    else:
        amount = custom_amount
        if amount <= 0:
            raise CheckoutError('Enter an amount to charge.')
        if not (description or '').strip():
            raise CheckoutError('Say what the custom amount is for.')
        #   No items: the payment counts toward their balance without being
        #   matched to anything (reconcile_payment_with_identifier then just
        #   checks 0 - 0 - credit == amount)
        identifier = '%s::0.00:%.2f' % (iac.get_id(), -amount)
    _check_minimum(amount, below_minimum_reason)
    return DayOfCardCheckout.objects.create(
        program=program, user=student, amount=amount, identifier=identifier, channel=channel,
        custom_amount=custom_amount is not None, description=(description or '').strip()[:200],
        below_minimum_reason=(below_minimum_reason or '').strip()[:200],
        recorded_by=recorded_by)


def sale_checkout(sale, channel, recorded_by, below_minimum_reason=''):
    """ Starts a card payment for a pending help desk sale. """
    if sale.status != 'pending':
        raise CheckoutError('That sale is already %s.' % sale.get_status_display().lower())
    _check_minimum(sale.total_dec, below_minimum_reason)
    return DayOfCardCheckout.objects.create(
        program=sale.program, sale=sale, amount=sale.total_dec, identifier=sale.identifier(),
        channel=channel, custom_amount=not sale.lines.exists(), description=sale.description,
        below_minimum_reason=(below_minimum_reason or '').strip()[:200],
        recorded_by=recorded_by)


def checkout_still_valid(checkout):
    """ Whether a checkout can still be paid as it stands (for a QR link that
    was opened later): the sale is still waiting, or the student still owes
    what it would charge. Returns an error message, or None if valid. """
    if checkout.sale_id is not None:
        if checkout.sale.status != 'pending':
            return 'This purchase is already %s.' % checkout.sale.get_status_display().lower()
        return None
    if checkout.custom_amount:
        #   Paid already (a card payment of this amount since the link was made)?
        if Transfer.objects.filter(user=checkout.user, source__isnull=True, line_item__for_payments=True,
                                   line_item__program=checkout.program, payment_method='card',
                                   amount_dec=checkout.amount, timestamp__gte=checkout.created_at).exists():
            return 'This payment has already been made.'
        return None
    iac = IndividualAccountingController(checkout.program, checkout.user)
    due = iac.amount_due().quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if due <= 0:
        return 'Nothing is owed any more.'
    if due != checkout.amount or iac.get_identifier() != checkout.identifier:
        return 'The amount owed has changed since this link was made; please ask for a new one.'
    return None


def make_pay_token(checkout):
    return signing.dumps({'c': checkout.id}, salt=TOKEN_SALT, compress=True)


def checkout_from_token(token):
    """ The DayOfCardCheckout a QR pay link is for, or None if the link is
    invalid or expired. """
    try:
        data = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
    except signing.BadSignature:
        return None
    return DayOfCardCheckout.objects.filter(id=data.get('c')).select_related('program', 'user', 'sale').first()


def pay_link_path(checkout):
    return '/onsite_pay/%s' % make_pay_token(checkout)


def qr_svg(text):
    """ An SVG QR code of text, as a string (reportlab's QR widget). """
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderSVG
    widget = QrCodeWidget(text)
    (x1, y1, x2, y2) = widget.getBounds()
    size = 240.0
    drawing = Drawing(size, size, transform=[size / (x2 - x1), 0, 0, size / (y2 - y1), 0, 0])
    drawing.add(widget)
    out = renderSVG.drawToString(drawing)
    #   drop the XML prolog/doctype so it can be inlined in HTML
    start = out.find('<svg')
    return out[start:] if start >= 0 else out


def return_url(request, program, identifier, result):
    """ Where the browser should land after paying a day-of checkout, or
    None for a student paying for themselves (the usual payment page). """
    if request is None:
        return None
    token = request.session.get(SESSION_KEY) if hasattr(request, 'session') else None
    if token:
        checkout = checkout_from_token(token)
        if checkout is not None and checkout.identifier == identifier:
            return '/onsite_pay/%s?card_result=%s' % (token, result)
    if is_sale_identifier(identifier):
        (prog, sale) = sale_from_identifier(identifier)
        if sale is not None:
            return '/onsite/%s/helpdesk_sales?sale=%d&card_result=%s' % (program.getUrlBase(), sale.id, result)
        return '/onsite/%s/helpdesk_sales?card_result=%s' % (program.getUrlBase(), result)
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return None
    try:
        student_id = int(_owner_part(identifier))
    except ValueError:
        return None
    if student_id == user.id:
        return None
    if not isinstance(user, ESPUser):
        user = ESPUser.objects.get(id=user.id)
    if user.isAdmin(program) or user.isOnsite(program):
        return '/onsite/%s/troubleshooting?user=%d&card_result=%s' % (program.getUrlBase(), student_id, result)
    return None


def checkout_form_context(checkout):
    """ What the auto-submitting CyberSource form needs (see
    templates/program/modules/dayof/card_checkout.html). """
    from django.conf import settings
    if not (settings.CYBERSOURCE_CONFIG.get('post_url') and settings.CYBERSOURCE_CONFIG.get('merchant_id')):
        raise CheckoutError('Card payments aren\'t set up on this site (CYBERSOURCE_CONFIG).')
    program = checkout.program
    if checkout.sale_id is not None:
        comments = '%s help desk sale %d (for %s)' % (settings.ORGANIZATION_SHORT_NAME, checkout.sale_id,
                                                      program.niceName())
        who = 'Help desk purchase'
    else:
        comments = '%s Invoice %d/%d (for %s)' % (settings.ORGANIZATION_SHORT_NAME, program.id,
                                                  checkout.user_id, program.niceName())
        who = checkout.user.name()
    if checkout.sale_id is not None:
        who_public = who
    else:
        who_public = '%s %s.' % (checkout.user.first_name, checkout.user.last_name[:1])
    return {
        'who_public': who_public,
        'post_url': settings.CYBERSOURCE_CONFIG['post_url'],
        'merchant_id': settings.CYBERSOURCE_CONFIG['merchant_id'],
        'amount': '%.2f' % checkout.amount,
        'identifier': checkout.identifier,
        'comments': comments,
        'who': who,
        'program': program,
    }


def checkout_page(request, checkout, status_url, back_url, paid_when, extra=None):
    """ The page a card payment continues on, for the card buttons
    (dayof/card_pay.html): on the laptop, the auto-submitting CyberSource
    form (in its own tab); by QR, the code for their phone, which watches
    status_url until the payment arrives. Raises CheckoutError if card
    payments aren't set up. """
    from esp.utils.web import render_to_response
    form = checkout_form_context(checkout)
    if checkout.channel == 'laptop':
        return render_to_response('program/modules/dayof/card_checkout.html', request, form)
    link = request.build_absolute_uri(pay_link_path(checkout))
    context = dict(form, qr_svg=qr_svg(link), link=link, minutes=TOKEN_MAX_AGE // 60,
                   status_url=status_url, paid_when=paid_when, back_url=back_url)
    context.update(extra or {})
    return render_to_response('program/modules/dayof/card_qr.html', request, context)


RESULT_TEXT = {
    'success': ('ok', 'Payment received.'),
    'received_review': ('warn', 'Payment received, but treasury needs to check it (they\'ve been told). '
                                'Don\'t charge again.'),
    'declined': ('error', 'The card was declined. Nothing was charged.'),
    'bank_verify': ('error', 'The card\'s bank wants the cardholder to call them. Nothing was charged.'),
    'under_review': ('warn', 'The payment is being held for review by the card processor; it may have been '
                             'charged. Don\'t charge again; treasury has been told.'),
    'possible_duplicate': ('warn', 'This looked like a repeat of a payment made in the last 15 minutes; '
                                   'check whether the first one went through before trying again.'),
    'error': ('error', 'The card processor reported an error. Nothing was recorded.'),
    'cancelled': ('error', 'The payment was cancelled. Nothing was charged.'),
}


def result_text(result):
    """ (kind, text) to show for a ?card_result=..., or None. """
    return RESULT_TEXT.get(result)
