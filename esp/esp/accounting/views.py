
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
from datetime import datetime, time
import csv

from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from esp.accounting.models import Account, LineItemType, TransferDetailsReportModel
from esp.gen_media.view_helpers import PDFResponseMixin
from esp.program.models import Program
from esp.users.models import admin_required, ESPUser
from esp.web.util.main import render_to_response

from forms import TransferDetailsReportForm


@admin_required
def summary(request):
    context = {}
    context['accounts'] = Account.objects.all().order_by('id')
    return render_to_response('accounting/summary.html', request, context)


class CSVResponseMixin(object):

    def get_csv_response(self, context, **response_kwargs):
        """
        Sets content type to text/csv. Converts the report model into a csv document.
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s.csv"' % slugify('csv download')
        writer = csv.writer(response)
        report_model = context['report_model']

        for section in report_model:
            for transfer in section.transfers:
                amount = transfer.amount_dec
                if transfer.line_item.text == 'Student payment':
                    amount = -amount

                row = [unicode(section.program),
                       transfer.id,
                       transfer.timestamp,
                       transfer.line_item.text,
                       transfer.amount_dec
                       ]
                writer.writerow(row)

        return response


class TransferDetailsReport(CSVResponseMixin, PDFResponseMixin, TemplateView):
    """
    A report displaying all transfers for the specified user
    within a given time frame and selected program. 
    """
    template_name = 'transfer_details_report.html'
    model = Program
    file_type = 'html'

    def render_to_response(self, context, **response_kwargs):
        if self.file_type == 'csv':
            response = self.get_csv_response(context, **response_kwargs)
        elif self.file_type == 'pdf':
            response = self.get_pdf_response(context, **response_kwargs)
        else:
            response = super(TransferDetailsReport, self).render_to_response(
            context, **response_kwargs)

        return response

    def get(self, request, *args, **kwargs):
        self.user = get_object_or_404(ESPUser, username=self.kwargs['username'])
        return super(TransferDetailsReport, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TransferDetailsReport, self).get_context_data(**kwargs)
        line_items = LineItemType.objects.filter(transfer__user=self.user)
        user_programs = Program.objects.filter(line_item_types__in=line_items).distinct()

        form_initial = self.request.GET
        form = TransferDetailsReportForm(form_initial, user_programs=user_programs)

        if form.is_valid():
            self.file_type = form.cleaned_data.get('file_type')
            context['report_model'] = TransferDetailsReportModel(self.user,
                                          form.cleaned_data.get('program'),
                                          form.cleaned_data.get('from_date'),
                                          form.cleaned_data.get('to_date')
                                       )
            context['from_date'] = form.cleaned_data.get('from_date')
            context['to_date'] = form.cleaned_data.get('to_date')

        context['user'] = self.user
        context['form'] = form
        return context

    @method_decorator(admin_required)
    def dispatch(self, *args, **kwargs):
        return super(TransferDetailsReport, self).dispatch(*args, **kwargs)
