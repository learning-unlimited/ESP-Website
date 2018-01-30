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
from esp.program.modules.base import ProgramModuleObj, needs_student, meets_deadline, meets_grade, CoreModule, main_call, aux_call, _checkDeadline_helper, meets_cap
from esp.program.models  import Program
from esp.utils.web import render_to_response
from esp.users.models    import ESPUser, Permission, Record
from esp.middleware   import ESPError
from datetime import datetime
from django.db import models
from django.contrib import admin
from django.template import Template
from django.template.loader import render_to_string, get_template, select_template

from esp.program.modules.handlers.studentclassregmodule import StudentClassRegModule

class StudentOnsite(ProgramModuleObj, CoreModule):
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Student Onsite",
            "admin_title": "Student Onsite Webapp",
            "module_type": "learn",
            "seq": -9999
            }

    @main_call
    @needs_student
    @meets_grade
    @meets_deadline('/Webapp')
    @meets_cap
    def studentonsite(self, request, tl, one, two, module, extra, prog):
        """ Display the landing page for the student onsite webapp """
        user = request.user

        context = StudentClassRegModule.prepare(user, prog)

        context['user'] = user
        context['program'] = prog
        context['one'] = one
        context['two'] = two
        context['scrmi'] = prog.studentclassregmoduleinfo
        context['isConfirmed'] = self.program.isConfirmed(user)
        context['class_changes'] = bool(Permission.user_has_perm(user, "Student/ClassChanges", prog))

        if extra == "map":
            return render_to_response(self.baseDir()+'map.html', request, context)
        elif extra == "contact":
            return render_to_response(self.baseDir()+'contact.html', request, context)
        elif extra == "survey":
            return render_to_response(self.baseDir()+'survey.html', request, context)
        else:
            return render_to_response(self.baseDir()+'schedule.html', request, context)

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Webapp')
    @meets_cap
    def map(self, request, tl, one, two, module, extra, prog):
        return render_to_response(self.baseDir()+'map.html', request, context)

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Webapp')
    @meets_cap
    def catalog(self, request, tl, one, two, module, extra, prog):
        if extra:
            try:
                timeslot = Event.objects.get(pk=int(extra), program=prog)
            except (TypeError, ValueError, Event.DoesNotExist) as e:
                raise Http404
            context['timeslot'] = extra
        return render_to_response(self.baseDir()+'catalog.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
