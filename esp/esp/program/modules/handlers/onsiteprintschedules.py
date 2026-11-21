
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
import json

from django.http import HttpResponse, HttpResponsePermanentRedirect, Http404

from esp.program import printer_views
from esp.program.controllers import dayof, printing
from esp.program.modules.base import ProgramModuleObj, needs_onsite, main_call, aux_call
from esp.utils.models import Printer


def _moved(request, view):
    """ An old /onsite/<program>/<view> page (GET), moved to /manage/printers/. """
    query = request.META.get('QUERY_STRING', '')
    return HttpResponsePermanentRedirect(printer_views.BASE_URL + view + ('?' + query if query else ''))


def _json(data, status=200):
    return HttpResponse(json.dumps(data), content_type='application/json', status=status)


class OnsitePrintSchedules(ProgramModuleObj):
    doc = """Links this program's onsite page to the Printers page (/manage/printers/: which printer prints for
    each day-of location, and the print queue), and queues schedules and receipts from the troubleshooting and help
    desk pages. Its old /onsite/<program>/printers_* URLs lead to the Printers page's views."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Printer Setup (day-of print locations, printers and print jobs)",
            "link_title": "Printer Setup",
            "module_type": "onsite",
            "seq": 10000,
            "choosable": 1,
            }

    @main_call
    @needs_onsite
    def printschedules(self, request, tl, one, two, module, extra, prog):
        """ The Printers page is for every program now (/manage/printers/,
        esp.program.printer_views); this program's onsite page links to it
        through here. The old per-printer URL (printschedules/<name>) goes to
        that location's laptop printing. """
        if extra:
            location = Printer.objects.active().filter(name=extra).first()
            if location is not None:
                return HttpResponsePermanentRedirect('%sprinters_laptop?location=%d' % (
                    printer_views.BASE_URL, location.id))
        return HttpResponsePermanentRedirect('%s?program=%d' % (printer_views.BASE_URL, prog.id))

    @aux_call
    @needs_onsite
    def printers_probe(self, request, tl, one, two, module, extra, prog):
        return _moved(request, 'printers_probe')

    @aux_call
    @needs_onsite
    def printers_action(self, request, tl, one, two, module, extra, prog):
        return printer_views.printers_action(request)

    @aux_call
    @needs_onsite
    def printers_laptop(self, request, tl, one, two, module, extra, prog):
        return _moved(request, 'printers_laptop')

    @aux_call
    @needs_onsite
    def printers_laptop_run(self, request, tl, one, two, module, extra, prog):
        return _moved(request, 'printers_laptop_run')

    @aux_call
    @needs_onsite
    def printers_test_pdf(self, request, tl, one, two, module, extra, prog):
        return _moved(request, 'printers_test_pdf')

    @aux_call
    @needs_onsite
    def printers_claim(self, request, tl, one, two, module, extra, prog):
        return printer_views.printers_claim(request)

    @aux_call
    @needs_onsite
    def printers_poll(self, request, tl, one, two, module, extra, prog):
        return printer_views.printers_poll(request)

    @aux_call
    @needs_onsite
    def printers_job_pdf(self, request, tl, one, two, module, extra, prog):
        return printer_views.printers_job_pdf(request)

    @aux_call
    @needs_onsite
    def printers_done(self, request, tl, one, two, module, extra, prog):
        return printer_views.printers_done(request)

    @aux_call
    @needs_onsite
    def printers_release(self, request, tl, one, two, module, extra, prog):
        return printer_views.printers_release(request)

    @aux_call
    @needs_onsite
    def printers_queue(self, request, tl, one, two, module, extra, prog):
        """ Queues a schedule or receipt for a location, from the
        troubleshooting and help desk pages (JSON). """
        if request.method != 'POST':
            raise Http404
        from esp.accounting.models import Receipt
        from esp.users.models import ESPUser
        #   With a location: the print panel's fields (its settings for this job too)
        (location, settings) = (None, {})
        if request.POST.get('location'):
            (location, _, settings, errors) = printing.print_panel_values(request.POST, copies=False)
            if errors:
                return _json({'error': ' '.join(errors)}, status=400)
        recorded_by = dayof.real_user(request)
        kind = request.POST.get('kind')
        if kind == 'schedule':
            user = ESPUser.objects.filter(id=request.POST.get('user') or 0).first()
            if user is None:
                raise Http404
            kwargs = {'user': user}
        elif kind == 'receipt':
            receipt = Receipt.objects.filter(id=request.POST.get('receipt') or 0, program=prog).first()
            if receipt is None:
                raise Http404
            kwargs = {'receipt': receipt}
        else:
            raise Http404
        try:
            job = printing.queue(kind, prog, location, requested_by=recorded_by, settings=settings, **kwargs)
        except printing.PrintingError as e:
            return _json({'error': str(e)}, status=409)
        where = job.printer.name if job.printer else 'Default'
        warning = printing.trouble_warning(job)
        return _json({'message': 'Sent %s to %s (job #%d).%s' % (job.describe(), where, job.id,
                                                                  ' ' + warning if warning else '')})

    class Meta:
        proxy = True
        app_label = 'modules'
