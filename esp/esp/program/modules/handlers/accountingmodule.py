__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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

from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.users.forms.generic_search_form import StudentSearchForm
from esp.utils.web import render_to_response
from esp.accounting.views import user_accounting
from esp.users.models import ESPUser
from django.conf import settings
from decimal import Decimal
import json
import urllib.request
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from esp.tagdict.models import Tag
from esp.accounting.models import Transfer
from esp.accounting.controllers import ProgramAccountingController
import datetime

class AccountingModule(ProgramModuleObj):
    doc = """Lists accounting information for the program for a single user."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Accounting",
            "link_title": "Accounting",
            "module_type": "manage",
            "seq": 253,
            "choosable": 0,
            }

    CC_FEE_RATE = 0.022

    def _get_cc_totals(self, prog):
        # Load Stripe settings exactly mimicking refund_views
        stripe_settings = {
            'offer_donation': True,
            'donation_text': 'Donation to Learning Unlimited',
        }
        if hasattr(settings, 'STRIPE_CONFIG'):
            stripe_settings.update(settings.STRIPE_CONFIG)

        try:
            tag_data_str = Tag.getProgramTag('stripe_settings', prog)
            if tag_data_str:
                stripe_settings.update(json.loads(tag_data_str))
        except (ValueError, TypeError):
            pass

        secret_key = stripe_settings.get('secret_key')
        if not secret_key:
            return None

        # Find starting time from earliest credit card payment
        earliest_transfer = Transfer.objects.filter(
            line_item__program=prog,
            line_item__text="Student payment"
        ).exclude(transaction_id="").exclude(transaction_id=None).order_by('timestamp').first()

        if not earliest_transfer:
            return {
                'gross_amount': Decimal('0.00'),
                'gross_count': 0,
                'refunded_amount': Decimal('0.00'),
                'total_stripe_fees': Decimal('0.00'),
                'donation_amount': Decimal('0.00'),
                'donation_count': 0,
                'cc_donation_fees': Decimal('0.00'),
                'error': None,
                'is_configured': True,
            }

        start_time = earliest_transfer.timestamp - datetime.timedelta(days=1)
        start_timestamp = int(start_time.timestamp())

        pac = ProgramAccountingController(prog)
        transfers = pac.all_transfers()
        donation_amount = Decimal('0.00')
        donation_count = 0
        donation_text = stripe_settings.get('donation_text', 'Donation to Learning Unlimited')

        donation_lineitem_id = None
        for t in transfers:
            if t.line_item and t.line_item.text and donation_text in str(t.line_item.text):
                donation_lineitem_id = t.line_item_id
                break

        if donation_lineitem_id:
            for t in transfers:
                if t.line_item_id == donation_lineitem_id and t.amount_dec > 0:
                    donation_amount += t.amount_dec
                    donation_count += 1

        totals = {
            'gross_amount': Decimal('0.00'),
            'gross_count': 0,
            'refunded_amount': Decimal('0.00'),
            'total_stripe_fees': Decimal('0.00'),
            'cc_donation_fees': (Decimal(str(donation_count)) * Decimal('0.01')) + (donation_amount * Decimal(str(self.CC_FEE_RATE))),
            'donation_amount': donation_amount,
            'donation_count': donation_count,
            'error': None,
            'is_configured': True,
        }

        headers = {
            'Authorization': 'Bearer ' + secret_key,
            'Stripe-Version': '2022-11-15'
        }
        url = 'https://api.stripe.com/v1/charges'

        has_more = True
        starting_after = None
        try:
            pages_checked = 0
            while has_more and pages_checked < 100: # Increased limit for time-based search
                query_params = [
                    ('limit', '100'),
                    ('created[gte]', str(start_timestamp)),
                    ('expand[]', 'data.balance_transaction'),
                ]
                if starting_after:
                    query_params.append(('starting_after', starting_after))

                params_encoded = urlencode(query_params)
                req = urllib.request.Request(url + '?' + params_encoded, headers=headers)

                try:
                    with urllib.request.urlopen(req, timeout=10) as response:
                        resp_data = response.read().decode('utf-8')
                        data = json.loads(resp_data)
                except URLError as e:
                    if hasattr(e, 'code') and hasattr(e, 'read'):
                        totals['error'] = "Provider API returned %s: %s" % (e.code, e.read().decode('utf-8', errors='ignore'))
                    else:
                        totals['error'] = "Provider API error: %s" % str(e)
                    break
                charges = data.get('data', [])
                for charge in charges:
                    # Filter by program name in the description to ensure we only count charges for this program
                    if prog.name not in charge.get('description', ''):
                        continue

                    totals['gross_count'] += 1
                    totals['gross_amount'] += Decimal(str(charge.get('amount', 0))) / 100
                    totals['refunded_amount'] += Decimal(str(charge.get('amount_refunded', 0))) / 100

                    bt = charge.get('balance_transaction')
                    if bt and isinstance(bt, dict):
                        totals['total_stripe_fees'] += Decimal(str(bt.get('fee', 0))) / 100

                has_more = data.get('has_more', False)
                if has_more and charges:
                    starting_after = charges[-1]['id']
                pages_checked += 1
        except Exception as e:
            totals['error'] = str(e)

        return totals

    @main_call
    @needs_admin
    def accounting(self, request, tl, one, two, module, extra, prog):
        user = None
        context = {}
        if extra:
            user = ESPUser.objects.get(id=extra)
        elif 'target_user' in request.POST:
            form = StudentSearchForm(request.POST)
            if form.is_valid():
                user = form.cleaned_data['target_user']
        else:
            form = StudentSearchForm()

        if user:
            form = StudentSearchForm(initial={'target_user': user.id})
            context['prog_results'] = user_accounting(user, [prog])

        if not user:
            context['cc_enabled'] = bool(Tag.getProgramTag('stripe_settings', prog)) or bool(getattr(settings, 'STRIPE_CONFIG', {}).get('secret_key'))
            if context['cc_enabled'] and request.GET.get('fetch_cc_totals') == '1':
                cc_totals = self._get_cc_totals(prog)
                context['cc_totals'] = cc_totals

        context['target_user'] = user
        context['form'] = form

        pac = ProgramAccountingController(self.program)

        context['donation_count'], context['donation_total'] = pac.donation_summary()
        context['admission_count'], context['admission_total'] = pac.admission_summary()

        donation_data = pac.donation_times()
        if donation_data:
            cumulative = []
            running = Decimal('0')
            for amount, dt in donation_data:
                running += amount
                cumulative.append([dt.timestamp() * 1000, float(running)]) # [timestamp_ms, value]
            context['donation_graph_data'] = cumulative

        admission_data = pac.admission_times()
        if admission_data:
            cumulative = []
            running = Decimal('0')
            for amount, dt in admission_data:
                running += amount
                cumulative.append([dt.timestamp() * 1000, float(running)])
            context['admission_graph_data'] = cumulative

        return render_to_response(self.baseDir()+'accounting.html', request, context)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
