
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

from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules import module_ext
from esp.utils.web import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser
from django              import forms
from django.http import HttpResponseRedirect
from esp.users.views    import search_for_user
from esp.accounting.controllers import IndividualAccountingController


class OnsitePaidItemsModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Onsite View Purchased Items",
            "link_title": "View Purchased Items for a Student",
            "module_type": "onsite",
            "seq": 31,
            "choosable": 1,
            }

    @main_call
    @needs_onsite
    def paiditems(self, request, tl, one, two, module, extra, prog):

        #   Get a user
        user, found = search_for_user(request, add_to_context = {'tl': 'onsite'})
        if not found:
            return user

        #   Get the optional purchases for that user
        iac = IndividualAccountingController(prog, user)
        context = {}
        context['student'] = user
        context['requireditems'] = iac.get_transfers(required_only=True)
        context['reserveditems'] = iac.get_transfers(optional_only=True)
        context['amount_requested'] = iac.amount_requested()
        context['amount_finaid'] = iac.amount_finaid()
        context['amount_due'] = iac.amount_due()

        return render_to_response(self.baseDir()+'paiditems.html', request, context)


    class Meta:
        proxy = True
        app_label = 'modules'
