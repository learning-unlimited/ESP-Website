
from __future__ import absolute_import
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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

from esp.accounting.controllers import IndividualAccountingController
from esp.accounting.models import Account, Transfer
from esp.program.models import Program
from esp.utils.web import render_to_response
from esp.users.models import admin_required, ESPUser
from esp.users.forms.generic_search_form import StudentSearchForm

@admin_required
def summary(request):
    context = {}
    context['accounts'] = Account.objects.all().order_by('id')
    return render_to_response('accounting/summary.html', request, context)

@admin_required
def user_summary(request):
    '''Lists accounting for a user.

    Defaults to the current user, but can take the user ID in the extra
    argument instead.'''
    user = None
    context = {}
    if 'target_user' in request.GET:
        users = ESPUser.objects.filter(id=request.GET['target_user'])
        if users.count() == 1:
            user = users[0]
    elif 'target_user' in request.POST:
        form = StudentSearchForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['target_user']
    else:
        form = StudentSearchForm()

    if user:
        form = StudentSearchForm(initial={'target_user': user.id})
        programs = Program.objects.filter(id__in=list(Transfer.objects.filter(user=user).values_list('line_item__program', flat = True).distinct()))
        context['prog_results'] = user_accounting(user, programs)

    context['target_user'] = user
    context['form'] = form
    return render_to_response('program/modules/accountingmodule/accounting.html', request, context)

def user_accounting(user, progs = []):
    results = []
    for prog in progs:
        iac = IndividualAccountingController(prog, user)
        classified_transfers = [
            { 'transfer': t, 'type': iac.classify_transfer(t) }
            for t in iac.get_transfers().select_related('line_item')
        ]
        sort_order = {"Cost (required)": 0, "Cost (optional)": 1, "Sibling discount": 2, "Financial aid": 3, "Payment": 4}
        classified_transfers.sort(key=lambda t: 'Program admission' not in t['transfer'].line_item.text) # put Program admission at the top
        classified_transfers.sort(key=lambda t: sort_order[t['type']])
        result = {
            'program': prog,
            'transfers': classified_transfers,
            'identifier': iac.get_identifier(),
            'grant': iac.latest_finaid_grant(),
        }
        if iac.transfers_to_program_exist():
            result['transfers_exist'] = True
            result['requested'] = iac.amount_requested(ensure_required=False)
            result['finaid'] = iac.amount_finaid()
            result['siblingdiscount'] = iac.amount_siblingdiscount()
            result['paid'] = iac.amount_paid()
            result['due'] = iac.amount_due()
        results.append(result)
    return results

