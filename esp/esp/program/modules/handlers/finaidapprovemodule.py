
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
from esp.utils.web import render_to_response
from esp.program.models import FinancialAidRequest
from esp.accounting.models import FinancialAidGrant


class FinAidApproveModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Easily Approve Financial Aid Requests",
            "link_title": "Approve Financial Aid Requests",
            "module_type": "manage",
            "seq": 26,
            "choosable": 0,
            }

    class Meta:
        proxy = True
        app_label = 'modules'

    @main_call
    @needs_admin
    def finaidapprove(self, request, tl, one, two, module, extra, prog):
        context = {}
        users_approved = []
        users_error = []
        context['amount_max_dec_help_text'] = FinancialAidGrant._meta.get_field('amount_max_dec').help_text
        context['percent_help_text'] = FinancialAidGrant._meta.get_field('percent').help_text

        # The following code was copied and modified from finaid_approve.py in useful_scripts

        reqs = FinancialAidRequest.objects.filter(program=prog).order_by("-id")


        # computing len will use the same query we're probably going to use later and
        # populate the query set cache (whereas if we used .exists() or .count(), they
        # wouldn't, and the later iteration would hit the database again)
        if len(reqs) == 0:
            context["error"] = "No requests found."
            return render_to_response(self.baseDir()+'finaid.html', request, context)

        if request.method == 'POST':
            context['POST'] = True
            # ITERATE & APPROVE REQUESTS
            userchecklist = request.POST.getlist("user")
            approve_blanks = request.POST.get('approve_blanks', False)
            amount_max_dec = request.POST.get('amount_max_dec', None)
            percent = request.POST.get('percent', None)

            def is_blank(x):
                return x is None or x == ""

            for req in reqs:
                if str(req.user.id) not in userchecklist:
                    continue

                if not approve_blanks:
                    if is_blank(req.household_income) or is_blank(req.extra_explaination):
                        continue

                if req.approved:
                    continue

                try:
                    req.approve(dollar_amount = amount_max_dec, discount_percent = percent)
                    users_approved.append(req.user.name())
                except:
                    users_error.append(req.user.name())

        context["requests"] = reqs
        context["users_approved"] = users_approved
        context["users_error"] = users_error
        return render_to_response(self.baseDir()+'finaid.html', request, context)
