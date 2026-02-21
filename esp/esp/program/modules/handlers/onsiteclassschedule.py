
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
from django.http     import HttpResponseRedirect
from esp.middleware  import ESPError
from esp.users.views import search_for_user
from esp.program.modules.base import ProgramModuleObj, needs_student_in_grade, needs_onsite, needs_onsite_no_switchback, main_call, aux_call
from esp.program.modules.handlers.programprintables import ProgramPrintables
from esp.users.models import ESPUser
from esp.utils.models import Printer, PrintRequest

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
    def printschedule(self, request, tl, one, two, module, extra, prog):#(self, request, *args, **kwargs):
        '''Sends a schedule printing request to the schedule-printing script.  Defaults to the current (probably onsite-morphed) user, but can take a GET parameter instead.'''
        printer = request.GET.get('printer', None)
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
        """ Redirect to student registration, having switched into the desired
        student.

        When ``user_id`` is supplied as a GET parameter (e.g. from the User
        View admin page) the student-search step is skipped and the caller is
        taken directly to that student's onsite registration.  Without it the
        standard search flow is used.
        """

        user_id = request.GET.get('user_id')
        if user_id:
            try:
                user = ESPUser.objects.get(id=user_id)
                # Restrict to non-admin students only.  Without this check an
                # attacker could enumerate arbitrary account IDs and morph into
                # any non-admin account (IDOR).  Admins are also blocked by
                # switch_to_user, but we enforce the constraint here so the
                # ESPError it raises can never reach the caller.
                if (user.isAdministrator() or user.is_staff or user.is_superuser
                        or not user.hasRole('Student')):
                    user_id = None
            except (ESPUser.DoesNotExist, ValueError):
                # Fall through to the normal search rather than 500-ing.
                user_id = None

        if not user_id:
            user, found = search_for_user(request, ESPUser.getAllOfType('Student', False), add_to_context = {'tl': 'onsite', 'module': self.module.link_title})
            if not found:
                return user

        try:
            request.user.switch_to_user(request,
                                     user,
                                     self.getCoreURL(tl),
                                     'OnSite Registration!',
                                     True)
        except ESPError:
            # Defensive: switch_to_user raises ESPError when the target is an
            # administrator.  The guard above should make this unreachable, but
            # catching it here ensures a single malformed request cannot
            # repeatedly trigger a 500.
            return HttpResponseRedirect(self.getCoreURL(tl))

        return HttpResponseRedirect('/learn/%s/studentreg' % self.program.getUrlBase())


    class Meta:
        proxy = True
        app_label = 'modules'
