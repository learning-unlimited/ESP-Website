
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
    user = None
    context = {}



    # ALWAYS define form first (IMPORTANT)
    form = StudentSearchForm()

    if 'target_user' in request.GET:
        users = ESPUser.objects.filter(id=request.GET['target_user'])
        if users.count() == 1:
            user = users[0]

    elif 'target_user' in request.POST:
        form = StudentSearchForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['target_user']

    if user:
        form = StudentSearchForm(initial={'target_user': user.id})
        programs = Program.objects.filter(
            id__in=list(
                Transfer.objects.filter(user=user)
                .values_list('line_item__program', flat=True)
                .distinct()
            )
        )
        context['prog_results'] = user_accounting(user, programs)

    context['target_user'] = user
    context['form'] = form

    return render_to_response(
        'program/modules/accountingmodule/accounting.html',
        request,
        context
    )

def user_accounting(user, progs=[]):
    results = []
    for prog in progs:
        iac = IndividualAccountingController(prog, user)
        classified_transfers = [
            {'transfer': t, 'type': iac.classify_transfer(t)}
            for t in iac.get_transfers().select_related('line_item')
        ]

        refund_lit = iac.default_refund_lineitemtype()
        if refund_lit:
            for t in Transfer.objects.filter(
                user=user,
                line_item=refund_lit,
                destination__isnull=True
            ).select_related('line_item'):
                classified_transfers.append({
                    'transfer': t,
                    'type': iac.classify_transfer(t)
                })

        result = {
            'program': prog,
            'transfers': classified_transfers,
        }

        results.append(result)

    return results