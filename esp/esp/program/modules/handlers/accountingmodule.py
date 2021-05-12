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

from esp.accounting.controllers import IndividualAccountingController
from esp.program.modules.base import ProgramModuleObj, needs_student, needs_admin, main_call, aux_call
from esp.users.forms.generic_search_form import StudentSearchForm
from esp.users.models import ESPUser
from esp.utils.web import render_to_response

class AccountingModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Accounting",
            "link_title": "Accounting",
            "module_type": "manage",
            "seq": 253,
            "choosable": 0,
            }

    @main_call
    @needs_admin
    def accounting(self, request, tl, one, two, module, extra, prog):
        '''Lists accounting for a student.

        Defaults to the current user, but can take the user ID in the extra
        argument instead.'''

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
            iac = IndividualAccountingController(prog, user)
            classified_transfers = [
                { 'transfer': t, 'type': iac.classify_transfer(t) }
                for t in iac.get_transfers().select_related('line_item')
            ]
            context.update({
                'transfers': classified_transfers,
                'identifier': iac.get_identifier(),
                'grant': iac.latest_finaid_grant(),
            })
            if iac.transfers_to_program_exist():
                context['transfers_exist'] = True
                context['requested'] = iac.amount_requested(ensure_required=False)
                context['finaid'] = iac.amount_finaid()
                context['siblingdiscount'] = iac.amount_siblingdiscount()
                context['paid'] = iac.amount_paid()
                context['due'] = iac.amount_due()
        context['target_user'] = user
        context['form'] = form
        return render_to_response(self.baseDir()+'accounting.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
