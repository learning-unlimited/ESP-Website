
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
from django.http     import HttpResponseRedirect
from esp.users.views import search_for_user
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, needs_onsite_no_switchback, main_call, aux_call
from esp.program.modules.handlers.programprintables import ProgramPrintables
from esp.users.models import ESPUser
from esp.utils.models import Printer, PrintRequest
from datetime         import datetime, timedelta

class OnsiteClassSchedule(ProgramModuleObj):
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
    @needs_student
    def printschedule(self, request, tl, one, two, module, extra, prog):#(self, request, *args, **kwargs):
        '''Sends a schedule printing request to the schedule-printing script.  Defaults to the current (probably onsite-morphed) user, but can take a GET parameter instead.'''
        printer = request.GET.get('printer',None)
        if printer is not None:
            # we could check that it exists and is unique first, but if not, that should be an error anyway, and it isn't the user's fault unless they're trying to mess with us, so a 500 is reasonable and gives us better debugging output.
            printer = Printer.objects.get(name=printer)
        if 'user' in request.GET:
            user = ESPUser.objects.get(id=request.GET['user'])
        else:
            user = request.user
        redirectURL = request.GET.get('next', '/learn/%s/studentreg' % self.program.getUrlBase())
        PrintRequest.objects.create(user=user, printer=printer)
        return HttpResponseRedirect(redirectURL)

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

        user, found = search_for_user(request, ESPUser.getAllOfType('Student', False), add_to_context = {'tl': 'onsite'})
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
