
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

from six.moves.urllib.parse import urlencode

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils import timezone

from esp.middleware.esperrormiddleware import ESPError_NoLog
from esp.utils import print_server
from esp.program.controllers import dayof, printing
from esp.program.modules.base import ProgramModuleObj, needs_onsite, main_call, aux_call
from esp.utils.models import Printer, PrintRequest
from esp.utils.web import render_to_response


def _json(data, status=200):
    return HttpResponse(json.dumps(data), content_type='application/json', status=status)


class OnsitePrintSchedules(ProgramModuleObj):
    doc = """The Printers page: which printer prints for each location on the day (a laptop running the
    printing page, or a network printer the server prints to), and the print queue."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Printers (Onsite Schedule and Receipt Printing)",
            "link_title": "Printers",
            "module_type": "onsite",
            "seq": 10000,
            "choosable": 1,
            }

    def _url(self, view='printschedules'):
        return '/onsite/%s/%s' % (self.program.getUrlBase(), view)

    def _location(self, request):
        try:
            location_id = int(request.GET.get('location') or request.POST.get('location'))
        except (TypeError, ValueError):
            raise Http404
        location = Printer.objects.filter(id=location_id).first()
        if location is None:
            raise Http404
        return location

    @main_call
    @needs_onsite
    def printschedules(self, request, tl, one, two, module, extra, prog):
        """ The Printers page. The old per-printer URL
        (printschedules/<name>) goes to that location's laptop printing. """
        if extra:
            location = Printer.objects.active().filter(name=extra).first()
            if location is not None:
                return HttpResponseRedirect('%s?location=%d' % (self._url('printers_laptop'), location.id))
        printing.default_location()
        printing.release_all_stale()
        locations = list(Printer.objects.active().order_by('-is_default', 'name'))
        for location in locations:
            location.connected = printing.is_connected(location)
            location.info = json.loads(location.network_info or '{}')
            location.settings = printing.location_settings(location)
            waiting = printing.jobs_for(location) if location.connected else \
                PrintRequest.objects.filter(printer=location, status='queued').order_by('id')
            location.waiting = waiting.count()
            oldest = waiting.first()
            location.oldest_waiting = oldest.time_requested if oldest else None
            location.history = location.changes.select_related('recorded_by')[:8]
        return render_to_response(self.baseDir() + 'printers.html', request, {
            'program': prog, 'locations': locations, 'module': self,
            'laptop_timeout': int(printing.LAPTOP_TIMEOUT.total_seconds()),
            'network_printing': print_server.configured(),
            'archived_locations': Printer.objects.filter(archived=True).order_by('name'),
        })

    @aux_call
    @needs_onsite
    def printers_probe(self, request, tl, one, two, module, extra, prog):
        """ Asks a network printer what it is, before connecting it (JSON). """
        try:
            (uri, info) = printing.probe(request.GET.get('address', ''))
        except printing.PrintingError as e:
            return _json({'error': str(e)})
        return _json({'uri': uri, 'info': info})

    @aux_call
    @needs_onsite
    def printers_action(self, request, tl, one, two, module, extra, prog):
        """ Changes to locations and their printers, from the Printers page. """
        if request.method != 'POST':
            raise Http404
        action = request.POST.get('action')
        try:
            recorded_by = dayof.real_user(request)
            take_over = bool(request.POST.get('take_over'))
            if action == 'add_location':
                name = (request.POST.get('name') or '').strip()
                if not name or Printer.objects.active().filter(name=name).exists():
                    raise printing.PrintingError('Enter a new, unused location name.')
                location = Printer.objects.create(name=name[:255])
                printing.log(location, 'location added', '', recorded_by)
                messages.success(request, 'Added location %s.' % name)
                return HttpResponseRedirect(self._url())
            location = self._location(request)
            if action == 'connect':
                address = request.POST.get('address', '')
                (uri, info) = printing.probe(address)
                printing.connect_network(location, address, info, uri, recorded_by, take_over)
                if request.POST.get('discard_waiting'):
                    printing.discard_waiting(location, recorded_by)
                messages.success(request, '%s now prints to %s (%s).' % (location.name, address, info['model']))
            elif action == 'disconnect':
                printing.disconnect(location, recorded_by)
                messages.success(request, 'Disconnected %s.' % location.name)
            elif action == 'test':
                printing.test_page(location, recorded_by)
                messages.success(request, 'Sent a test page to %s.' % location.name)
            elif action == 'settings':
                printing.save_settings(location, request.POST, recorded_by)
                messages.success(request, 'Saved the settings for %s.' % location.name)
            elif action == 'rename':
                name = (request.POST.get('name') or '').strip()
                if not name or Printer.objects.active().filter(name=name).exclude(id=location.id).exists():
                    raise printing.PrintingError('Enter a new, unused location name.')
                with transaction.atomic():
                    printing.log(location, 'renamed', '%s -> %s' % (location.name, name), recorded_by)
                    location.name = name[:255]
                    location.save()
            elif action == 'archive':
                printing.archive(location, recorded_by)
                messages.success(request, 'Archived location %s.' % location.name)
            elif action == 'restore':
                printing.restore(location, recorded_by)
                messages.success(request, 'Restored location %s.' % location.name)
            elif action == 'discard_waiting':
                count = printing.discard_waiting(location, recorded_by)
                messages.success(request, 'Cancelled %d waiting job(s) for %s.' % (count, location.name))
            else:
                raise Http404
        except printing.PrintingError as e:
            messages.error(request, str(e))
        return HttpResponseRedirect(self._url())

    @aux_call
    @needs_onsite
    def printers_laptop(self, request, tl, one, two, module, extra, prog):
        """ This laptop prints for a location (claimed by the page's script). """
        location = self._location(request)
        return render_to_response(self.baseDir() + 'laptop.html', request, {
            'program': prog, 'location': location, 'module': self,
            'connected_elsewhere': printing.is_connected(location),
            'printers_url': self._url(),
        })

    @aux_call
    @needs_onsite
    def printers_laptop_run(self, request, tl, one, two, module, extra, prog):
        """ The page left running on the printing laptop, after it claimed
        the location on printers_laptop (the token is in the URL fragment). """
        location = self._location(request)
        return render_to_response(self.baseDir() + 'laptop_running.html', request, {
            'program': prog, 'location': location, 'module': self,
            'printers_url': self._url(),
        })

    @aux_call
    @needs_onsite
    def printers_test_pdf(self, request, tl, one, two, module, extra, prog):
        """ The test page, for a laptop to print from its browser (the same
        one network printers get). """
        location = self._location(request)
        pdf = printing.test_page_pdf(location, dayof.real_user(request), 'this laptop')
        return HttpResponse(pdf, content_type='application/pdf')

    @aux_call
    @needs_onsite
    def printers_claim(self, request, tl, one, two, module, extra, prog):
        if request.method != 'POST':
            raise Http404
        location = self._location(request)
        try:
            recorded_by = dayof.real_user(request)
            token = printing.claim_for_laptop(location, recorded_by,
                                              take_over=bool(request.POST.get('take_over')))
            if request.POST.get('discard_waiting'):
                printing.discard_waiting(location, recorded_by)
        except (printing.PrintingError, ESPError_NoLog) as e:
            return _json({'error': str(e)}, 409)
        return _json({'token': token})

    @aux_call
    @needs_onsite
    def printers_poll(self, request, tl, one, two, module, extra, prog):
        """ The laptop asks for its next job. """
        if request.method != 'POST':
            raise Http404
        location = self._location(request)
        try:
            job = printing.next_job_for_laptop(location, request.POST.get('token', ''))
        except printing.PrintingError as e:
            return _json({'stop': str(e)}, 409)
        if job is None:
            return _json({'job': None})
        return _json({'job': job.id, 'title': job.describe(), 'copies': job.copies,
                      'pdf': '%s?%s' % (self._url('printers_job_pdf'), urlencode({
                          'location': location.id, 'job': job.id, 'token': request.POST.get('token', '')}))})

    @aux_call
    @needs_onsite
    def printers_job_pdf(self, request, tl, one, two, module, extra, prog):
        location = self._location(request)
        job = printing.laptop_job(location, request.GET.get('token', ''), request.GET.get('job') or 0)
        if job is None:
            raise Http404
        try:
            pdf = printing.render(job)
        except Exception as e:
            printing.mark_printed(job, ok=False, error='Could not make the document: %s' % e)
            raise
        return HttpResponse(pdf, content_type='application/pdf')

    @aux_call
    @needs_onsite
    def printers_done(self, request, tl, one, two, module, extra, prog):
        if request.method != 'POST':
            raise Http404
        location = self._location(request)
        job = printing.laptop_job(location, request.POST.get('token', ''), request.POST.get('job') or 0)
        if job is not None:
            printing.mark_printed(job, ok=request.POST.get('ok') != '0', error=request.POST.get('error', ''))
            Printer.objects.filter(id=location.id).update(
                last_result='ok' if request.POST.get('ok') != '0' else 'failed', last_result_at=timezone.now())
        return _json({'ok': True})

    @aux_call
    @needs_onsite
    def printers_release(self, request, tl, one, two, module, extra, prog):
        """ The laptop stops printing (its Stop button). A laptop that just
        goes away is released after LAPTOP_TIMEOUT instead. """
        if request.method != 'POST':
            raise Http404
        location = self._location(request)
        printing.release_laptop(location, request.POST.get('token', ''))
        return _json({'ok': True})

    @aux_call
    @needs_onsite
    def printers_queue(self, request, tl, one, two, module, extra, prog):
        """ Queues a schedule or receipt for a location, from the
        troubleshooting and help desk pages (JSON). """
        if request.method != 'POST':
            raise Http404
        from esp.accounting.models import Receipt
        from esp.users.models import ESPUser
        location = None
        if request.POST.get('location'):
            location = self._location(request)
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
            job = printing.queue(kind, prog, location, requested_by=recorded_by, **kwargs)
        except printing.PrintingError as e:
            return _json({'error': str(e)}, status=409)
        where = job.printer.name if job.printer else 'Default'
        warning = ''
        target = job.printer if job.printer and printing.is_connected(job.printer) else printing.default_location()
        if target.mode == 'network' and target.trouble:
            warning = ' %s has trouble printing right now (%s); it will print once that clears.' % (
                target.name, target.trouble)
        return _json({'message': 'Sent %s to %s (job #%d).%s' % (job.describe(), where, job.id, warning)})

    class Meta:
        proxy = True
        app_label = 'modules'
