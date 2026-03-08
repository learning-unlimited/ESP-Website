from __future__ import absolute_import
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2026 by the individual contributors
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

import json
import logging
import stripe
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.utils import timezone

from esp.accounting.controllers import ProgramAccountingController
from esp.accounting.forms import RefundSearchForm
from esp.accounting.models import Transfer
from esp.dbmail.models import send_mail
from esp.program.models import Program
from esp.tagdict.models import Tag
from esp.users.models import admin_required, ESPUser
from esp.utils.web import render_to_response

logger = logging.getLogger(__name__)

# Maximum age of transactions to display (in days)
REFUND_MAX_TRANSACTION_AGE_DAYS = 180

# Email address for CFO notifications
CFO_EMAIL = 'cfo@learningu.org'


def _get_stripe_settings(program):
    """Load Stripe settings for a program, falling back to global config."""
    stripe_settings = dict(settings.STRIPE_CONFIG)
    try:
        tag_data = Tag.getProgramTag('stripe_settings', program)
        if tag_data:
            stripe_settings.update(json.loads(tag_data))
    except (ValueError, TypeError):
        pass
    return stripe_settings


def _configure_stripe(program):
    """Configure the stripe module with the correct API key for the program."""
    stripe_settings = _get_stripe_settings(program)
    stripe.api_key = stripe_settings.get('secret_key', '')
    stripe.api_version = '2014-03-13'
    return stripe_settings


def _get_payment_transfers(program, users=None):
    """Get all Stripe payment transfers for a program, optionally filtered by users.

    Only returns transactions within the REFUND_MAX_TRANSACTION_AGE_DAYS window.
    """
    pac = ProgramAccountingController(program)
    payment_type = pac.default_payments_lineitemtype()
    if payment_type is None:
        return Transfer.objects.none()

    cutoff_date = timezone.now() - timedelta(days=REFUND_MAX_TRANSACTION_AGE_DAYS)

    transfers = Transfer.objects.filter(
        line_item=payment_type,
        source__isnull=True,       # Payments from outside (credit card)
        timestamp__gte=cutoff_date,
    ).exclude(
        transaction_id='',
    ).exclude(
        transaction_id='TBD',
    ).select_related('user', 'line_item', 'line_item__program')

    if users is not None:
        transfers = transfers.filter(user__in=users)

    return transfers.order_by('-timestamp')


def _get_stripe_refund_info(charge_id):
    """Query Stripe for refund information on a charge.

    Returns (amount_refunded_cents, total_amount_cents) or (0, 0) on error.
    """
    try:
        charge = stripe.Charge.retrieve(charge_id)
        return (charge.amount_refunded, charge.amount)
    except stripe.error.StripeError as e:
        logger.error("Error retrieving Stripe charge %s: %s", charge_id, str(e))
        return (0, 0)


def _send_refund_notification_email(program, refund_results, is_error=False):
    """Send email notification to CFO about refund results."""
    domain_name = Site.objects.get_current().domain

    if is_error:
        subject = '[ ESP Refund ERROR ] Stripe refund error on %s for %s' % (
            domain_name, program.niceName())
        template = 'accounting/refund_error_email.txt'
    else:
        subject = '[ ESP Refund ] Stripe refunds issued on %s for %s' % (
            domain_name, program.niceName())
        template = 'accounting/refund_success_email.txt'

    context = {
        'program': program,
        'refund_results': refund_results,
        'domain_name': domain_name,
    }
    msg_content = render_to_string(template, context)
    send_mail(subject, msg_content, settings.SERVER_EMAIL, [CFO_EMAIL], bcc=None)


@admin_required
def refund(request):
    """Main refund page. Handles program/user search and shows transactions."""
    context = {
        'max_age_days': REFUND_MAX_TRANSACTION_AGE_DAYS,
    }

    program = None
    users = []

    initial_program_id = request.session.get('refund_last_program_id')
    if not initial_program_id:
        current_progs = Program.current_programs()
        if current_progs:
            initial_program_id = current_progs[0].id

    if request.method == 'POST' and 'search' in request.POST:
        form = RefundSearchForm(request.POST)
        context['form'] = form
        if form.is_valid():
            program = form.cleaned_data['program']
            user = form.cleaned_data.get('target_user')
            if user:
                users = [user]
            request.session['refund_last_program_id'] = program.id

    elif request.method == 'GET' and 'program' in request.GET:
        try:
            program = Program.objects.get(id=request.GET['program'])
            context['form'] = RefundSearchForm(initial={'program': program.id})
            request.session['refund_last_program_id'] = program.id
        except Program.DoesNotExist:
            context['form'] = RefundSearchForm(initial={'program': initial_program_id})
        if 'user' in request.GET:
            try:
                users = [ESPUser.objects.get(id=request.GET['user'])]
            except ESPUser.DoesNotExist:
                pass

    if 'form' not in context:
        context['form'] = RefundSearchForm(initial={'program': initial_program_id})

    if program and users:
        context['selected_program'] = program
        context['searched_with_user'] = bool(users)
        _configure_stripe(program)

        # Get payment transfers
        transfers = _get_payment_transfers(program, users if users else None)

        # Build transaction table with Stripe refund info
        transaction_rows = []
        for transfer in transfers:
            stripe_refunded_cents, stripe_total_cents = _get_stripe_refund_info(
                transfer.transaction_id)

            amount_paid = transfer.amount_dec
            amount_refunded = Decimal(stripe_refunded_cents) / Decimal('100')
            amount_remaining = amount_paid - amount_refunded

            transaction_rows.append({
                'transfer': transfer,
                'user': transfer.user,
                'user_id': transfer.user.id,
                'username': transfer.user.username,
                'full_name': transfer.user.name(),
                'transaction_id': transfer.transaction_id,
                'amount_paid': amount_paid,
                'amount_refunded': amount_refunded,
                'amount_remaining': amount_remaining,
                'timestamp': transfer.timestamp,
            })

        context['transaction_rows'] = transaction_rows
        context['has_transactions'] = len(transaction_rows) > 0

    return render_to_response('accounting/refund.html', request, context)


@admin_required
def process_refund(request):
    """Process the actual Stripe refund requests."""
    if request.method != 'POST':
        return render_to_response('accounting/refund.html', request, {
            'form': RefundSearchForm(),
            'max_age_days': REFUND_MAX_TRANSACTION_AGE_DAYS,
        })

    program_id = request.POST.get('program_id')
    try:
        program = Program.objects.get(id=program_id)
    except Program.DoesNotExist:
        return render_to_response('accounting/refund_error.html', request, {
            'error_message': 'Invalid program specified.',
        })

    _configure_stripe(program)

    # Collect refund requests from form
    refund_requests = []
    pac = ProgramAccountingController(program)
    payment_type = pac.default_payments_lineitemtype()
    for key, value in request.POST.items():
        if key.startswith('refund_amount_'):
            transfer_id = key.replace('refund_amount_', '')
            try:
                amount = Decimal(value)
                if amount > 0:
                    # Verify the transfer exists and belongs to this program
                    transfer = Transfer.objects.get(
                        id=transfer_id,
                        line_item=payment_type,
                        source__isnull=True,
                    )
                    refund_requests.append({
                        'transfer': transfer,
                        'amount': amount,
                    })
            except (ValueError, InvalidOperation, Transfer.DoesNotExist):
                continue

    if not refund_requests:
        return render_to_response('accounting/refund_error.html', request, {
            'error_message': 'No valid refund amounts were specified.',
            'program': program,
        })

    # Process each refund through Stripe
    refund_results = []
    has_errors = False

    for req in refund_requests:
        transfer = req['transfer']
        amount_cents = int(req['amount'] * Decimal('100'))
        result = {
            'user_id': transfer.user.id,
            'username': transfer.user.username,
            'full_name': transfer.user.name(),
            'transaction_id': transfer.transaction_id,
            'amount_requested': req['amount'],
            'success': False,
            'error_message': '',
            'stripe_refund_id': '',
        }

        try:
            stripe_refund = stripe.Refund.create(
                charge=transfer.transaction_id,
                amount=amount_cents,
            )
            result['success'] = True
            result['stripe_refund_id'] = stripe_refund.id
        except stripe.error.InvalidRequestError as e:
            result['error_message'] = str(e)
            has_errors = True
            logger.error("Stripe refund InvalidRequestError for charge %s: %s",
                         transfer.transaction_id, str(e))
        except stripe.error.StripeError as e:
            result['error_message'] = str(e)
            has_errors = True
            logger.error("Stripe refund error for charge %s: %s",
                         transfer.transaction_id, str(e))

        refund_results.append(result)

    # Send email notifications
    successful_results = [r for r in refund_results if r['success']]
    failed_results = [r for r in refund_results if not r['success']]

    if successful_results:
        _send_refund_notification_email(program, successful_results, is_error=False)
    if failed_results:
        _send_refund_notification_email(program, failed_results, is_error=True)

    context = {
        'program': program,
        'refund_results': refund_results,
        'successful_results': successful_results,
        'failed_results': failed_results,
        'has_errors': has_errors,
    }

    return render_to_response('accounting/refund_confirmation.html', request, context)
