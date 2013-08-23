
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
  Email: web-team@lists.learningu.org
"""
from django.http      import HttpResponse
from esp.users.views  import search_for_user
from esp.program.models import SplashInfo
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules.handlers.programprintables import ProgramPrintables
from esp.users.models import ESPUser
from datetime         import datetime
from esp.web.util     import render_to_response
from esp.datatree.models import *
from esp.utils.models import Printer, PrintRequest
from datetime         import datetime
from django.db.models.query   import Q
from django.template.loader import select_template

class OnsitePrintSchedules(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Automatically Print Schedules for Onsite Reg",
            "link_title": "Automatically Print Schedules",
            "module_type": "onsite",
            "seq": 10000
            }

    @main_call
#    @needs_onsite
    def printschedules(self, request, tl, one, two, module, extra, prog):
        " A link to print a schedule. "
        if not request.GET.has_key('sure') and not request.GET.has_key('gen_img'):
            printers = Printer.objects.all().values_list('name', flat=True)

            return render_to_response(self.baseDir()+'instructions.html',
                                    request, {'printers': printers})

        if request.GET.has_key('sure'):
            return render_to_response(self.baseDir()+'studentschedulesrenderer.html',
                            request, {})

        requests = PrintRequest.objects.filter(time_executed__isnull=True)
        if extra and Printer.objects.filter(name=extra).exists():
            requests = requests.filter(printer__name=extra)

        for req in requests:
            req.time_executed = datetime.now()
            req.save()

        # get students
        old_students = set([ ESPUser(req.user) for req in requests ])

        if len(old_students) > 0:
            response = ProgramPrintables.get_student_schedules(request, list(old_students), prog, onsite=True)       
        # set the refresh rate
        #response['Refresh'] = '2'
            return response
        else:
            # No response if no users
            return HttpResponse('')

    def studentschedule(self, request, *args, **kwargs):
        request.GET = {'extra': str(285), 'op':'usersearch',
                       'userid': str(request.user.id) }

        module = [module for module in self.program.getModules('manage')
                  if type(module) == ProgramPrintables        ][0]

        module.user = request.user
        module.program = self.program
#        return module.studentschedules(request, *args, **kwargs)
        return ProgramPrintables.get_student_schedules(request, [request.user], self.program, onsite=True)
        

    class Meta:
        abstract = True

