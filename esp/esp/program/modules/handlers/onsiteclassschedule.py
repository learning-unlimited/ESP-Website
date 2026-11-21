
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
from django.http     import HttpResponseRedirect, HttpResponseNotAllowed, Http404
from django.utils.http import is_safe_url
from esp.middleware import ESPError
from esp.program.controllers import dayof, printing
from esp.users.views import search_for_user
from esp.program.modules.base import ProgramModuleObj, needs_student_in_grade, needs_onsite, needs_onsite_no_switchback, main_call, aux_call
from esp.program.modules.handlers.programprintables import ProgramPrintables
from esp.users.models import ESPUser
from esp.utils.models import Printer

class OnsiteClassSchedule(ProgramModuleObj):
    doc = """Get and/or print a student's schedule for the program."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Onsite Scheduling for Students",
            "link_title": "Scheduling and Class Changes",
            "module_type": "onsite",
            "seq": 30,
            "choosable": 1,
            }

    @aux_call
    @needs_student_in_grade
    def printschedule(self, request, tl, one, two, module, extra, prog):
        """ Queues a student's schedule for printing (POST). Defaults to the
        current (probably onsite-morphed) user; printing someone else's
        ('user') needs onsite or admin access. 'printer' names the location
        (else the Default location), 'next' where to go after. """
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'])
        location = None
        if request.POST.get('printer'):
            location = Printer.objects.active().filter(name=request.POST['printer']).first()
            if location is None:
                raise Http404
        user = request.user
        if request.POST.get('user'):
            try:
                user = ESPUser.objects.get(id=int(request.POST['user']))
            except (ValueError, ESPUser.DoesNotExist):
                raise Http404
            real = dayof.real_user(request)
            if user != request.user and not (real.isOnsite(prog) or real.isAdmin(prog)):
                raise Http404
        recorded_by = dayof.real_user(request)
        try:
            printing.queue('schedule', prog, location, user=user, requested_by=recorded_by)
        except printing.PrintingError as e:
            raise ESPError(str(e), log=False)
        redirect = request.POST.get('next', '')
        if not is_safe_url(redirect, allowed_hosts={request.get_host()}):
            redirect = '/learn/%s/studentreg' % self.program.getUrlBase()
        return HttpResponseRedirect(redirect)

    @aux_call
    @needs_onsite_no_switchback
    def studentschedule(self, request, *args, **kwargs):
        if 'user' in request.GET:
            user = ESPUser.objects.get(id=request.GET['user'])
        else:
            user = request.user

        #  onsite=False since we probably want a PDF
        return ProgramPrintables.get_student_schedules(request, [user], self.program, onsite=False)


    @main_call
    @needs_onsite
    def schedule_students(self, request, tl, one, two, module, extra, prog):
        """ Redirect to student registration, having morphed into the desired
        student. """

        user, found = search_for_user(request, ESPUser.getAllOfType('Student', False), add_to_context = {'tl': 'onsite', 'module': self.module.link_title})
        if not found:
            return user

        request.user.switch_to_user(request,
                                 user,
                                 self.getCoreURL(tl),
                                 'OnSite Registration!',
                                 True)

        return HttpResponseRedirect('/learn/%s/studentreg' % self.program.getUrlBase())


    class Meta:
        proxy = True
        app_label = 'modules'
