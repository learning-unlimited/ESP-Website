
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
from collections import OrderedDict
from esp.accounting.models import Account
from esp.web.util.main import render_to_response
from esp.users.models import admin_required

from datetime import datetime, time
from django.views.generic import ListView, DetailView, CreateView, TemplateView
from django.views.generic.base import TemplateView
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.db.models import Sum

from django.db.models import Q

from forms import TransferDetailsReportForm
from esp.program.models import Program
from esp.users.models import ESPUser
from esp.program.models import Program
from esp.accounting.models import *


@admin_required
def summary(request):
    context = {}
    context['accounts'] = Account.objects.all().order_by('id')
    return render_to_response('accounting/summary.html', request, context)


class ReportSection(object):
    def __init__(self, program, transfers):
        self.program = program
        self.transfers = transfers.filter(line_item__program=program)
        
        line_item_type_q = Q(line_item__text__iexact='Student payment')
        sum_query = Sum('amount_dec')
        self.total_owed_result = self.transfers.filter(~line_item_type_q) \
                                    .aggregate(sum_query)
        self.total_paid_result = self.transfers.filter(line_item_type_q) \
                                    .aggregate(sum_query)

        self.total_owed = self.total_owed_result['amount_dec__sum'] or 0
        self.total_paid = self.total_paid_result['amount_dec__sum'] or 0
        self.balance =  float(self.total_owed) - float(self.total_paid)


class TransferDetailsReportModel(object):
    def __init__(self, user, program, start_date=None, end_date=None):
        self.sections = []
        self.user = user
        self.program = program
        self.start_date = start_date
        self.end_date = end_date

        line_items = LineItemType.objects.filter(transfer__user=self.user)
        self.user_programs = Program.objects.filter(line_item_types__in=line_items).distinct()

        transfer_qs = self.user.transfers.all()

        if program:
            self.user_programs = self.user_programs.filter(id=program)

        transfer_qs = transfer_qs.filter(line_item__program__in=list(self.user_programs))

        if start_date:
            transfer_qs = transfer_qs.filter(timestamp__gte=start_date)

        if end_date:
            transfer_qs = transfer_qs.filter(timestamp_lte=end_date)

        program_transfers = []
        for program in self.user_programs:
            self.sections.append(ReportSection(program, transfer_qs))

    def __iter__(self):
        return iter(self.sections)


class TransferDetailsReport(TemplateView):
    """
    A report displaying all transfers for the specified user
    within a given time frame and selected program. 
    """
    template_name = 'transfer_details_report.html'
    model = Program

    def get(self, request, *args, **kwargs):
        self.user = get_object_or_404(ESPUser, username=self.kwargs['username'])
        return super(TransferDetailsReport, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TransferDetailsReport, self).get_context_data(**kwargs)
        line_items = LineItemType.objects.filter(transfer__user=self.user)
        user_programs = Program.objects.filter(line_item_types__in=line_items).distinct()
        form = TransferDetailsReportForm(self.request.GET, user_programs=user_programs)

        if form.is_valid():
            context['report_model'] = TransferDetailsReportModel(self.user,
                                          form.cleaned_data.get('program'),
                                          form.cleaned_data.get('start_date'),
                                          form.cleaned_data.get('end_date')
                                       )

        context['form'] = form
       
        return context


