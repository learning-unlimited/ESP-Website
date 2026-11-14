
from __future__ import absolute_import
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

from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.utils.web import render_to_response
from esp.program.models import FinancialAidRequest
from esp.accounting.models import FinancialAidGrant, Transfer
from esp.accounting.controllers import IndividualAccountingController, ProgramAccountingController
from esp.middleware import ESPError
from esp.middleware.esperrormiddleware import ESPError_NoLog
from django.db.models import Sum
from django.http import HttpResponse
from decimal import Decimal, InvalidOperation
import json


class FinAidApproveModule(ProgramModuleObj):
    doc = """View and approve student financial aid applications."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Easily Approve Financial Aid Requests",
            "link_title": "Approve Financial Aid Requests",
            "module_type": "manage",
            "seq": 26,
            "choosable": 0,
            }

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'

    @staticmethod
    def _grant_terms(data):
        """ The grant terms entered on the page: (dollar cap, percent). Blank
        means 0; with both 0, approve() refuses (nothing granted). """
        try:
            amount_max_dec = Decimal(data.get('amount_max_dec', '').strip() or '0')
            percent = int(data.get('percent', '').strip() or '0')
        except (InvalidOperation, ValueError):
            raise ESPError('The dollar amount and percent must be numbers.', log=False)
        return (amount_max_dec, percent)

    @staticmethod
    def _sort_selected(reqs, data):
        """ Split the requests checked on the page into those that submitting
        would approve, and those it would skip (already approved, or no
        explanation without "approve blank requests"), each in page order. """
        userchecklist = data.getlist("user")
        approve_blanks = data.get('approve_blanks', False)
        to_approve, already_approved, blank = [], [], []
        for req in reqs:
            if str(req.user.id) not in userchecklist:
                continue
            if req.approved:
                already_approved.append(req)
            elif not approve_blanks and (req.extra_explaination is None or req.extra_explaination == ""):
                blank.append(req)
            else:
                to_approve.append(req)
        return (to_approve, already_approved, blank)

    @staticmethod
    def _already_paid(prog, reqs):
        """ Which of these requests' students have already paid something
        for the program, as "name ($amount)" strings in the order given. """
        paid = dict(Transfer.objects.filter(
            user__in=[req.user for req in reqs],
            line_item=ProgramAccountingController(prog).default_payments_lineitemtype(),
            source__isnull=True,
        ).values_list('user').annotate(Sum('amount_dec')))
        return ['%s ($%.2f)' % (req.user.name(), paid[req.user.id])
                for req in reqs if paid.get(req.user.id, 0) > 0]

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
            (amount_max_dec, percent) = self._grant_terms(request.POST)
            for req in self._sort_selected(reqs, request.POST)[0]:
                try:
                    req.approve(dollar_amount = amount_max_dec, discount_percent = percent)
                    users_approved.append(req.user.name())
                except:
                    users_error.append(req.user.name())

        context["requests"] = reqs
        context["users_approved"] = users_approved
        context["users_error"] = users_error
        return render_to_response(self.baseDir()+'finaid.html', request, context)

    @aux_call
    @needs_admin
    def finaidapprovepreview(self, request, tl, one, two, module, extra, prog):
        """ For the approval page's live preview: who submitting the form as
        it stands would approve and skip, and the approval email one of them
        would get -- either a chosen student (preview_user) or the first, in
        page order, matching the criteria (extracosts, payment). Nothing is
        saved. """
        data = request.POST
        reqs = FinancialAidRequest.objects.filter(program=prog).select_related('user').order_by("-id")
        (to_approve, already_approved, blank) = self._sort_selected(reqs, data)
        result = {
            'to_approve': [{'id': req.user.id, 'name': req.user.name()} for req in to_approve],
            'already_approved': [req.user.name() for req in already_approved],
            'blank': [req.user.name() for req in blank],
            'already_paid': self._already_paid(prog, to_approve),
            'student': None,
            'email': None,
            'error': None,
        }

        try:
            (amount_max_dec, percent) = self._grant_terms(data)
        except ESPError_NoLog as e:
            result['error'] = str(e)
            return HttpResponse(json.dumps(result), content_type='application/json')
        if not (amount_max_dec or percent):
            result['error'] = 'Enter a dollar amount or a percent to grant.'
            return HttpResponse(json.dumps(result), content_type='application/json')

        candidates = to_approve
        preview_user = data.get('preview_user', '')
        if preview_user:
            candidates = [req for req in candidates if str(req.user.id) == preview_user]
        else:
            extracosts = data.get('extracosts', '')
            if extracosts:
                pac = ProgramAccountingController(prog)
                with_extras = set(Transfer.objects.filter(
                    pac.all_transfers_Q(optional_only=True),
                    user__in=[req.user for req in candidates],
                ).values_list('user', flat=True))
                candidates = [req for req in candidates if (req.user.id in with_extras) == (extracosts == 'yes')]
            payment = data.get('payment', '')
            if payment:
                candidates = [req for req in candidates
                              if (IndividualAccountingController(prog, req.user).amount_paid() > 0) == (payment == 'paid')]

        if candidates:
            req = candidates[0]
            result['student'] = {'id': req.user.id, 'name': req.user.name()}
            result['email'] = req.preview_approval_email(dollar_amount=amount_max_dec, discount_percent=percent)
        return HttpResponse(json.dumps(result), content_type='application/json')
