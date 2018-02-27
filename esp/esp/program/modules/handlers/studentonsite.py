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
from esp.program.models  import Program, ClassSubject
from esp.utils.web import render_to_response
from esp.users.models    import ESPUser, Permission, Record
from esp.cal.models import Event
from esp.middleware   import ESPError
from esp.tagdict.models  import Tag
from datetime import datetime
from django.db import models
from django.contrib import admin
from django.http import HttpResponseRedirect
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

        context = StudentClassRegModule.prepare_static(user, prog)

        context['user'] = user
        context['program'] = prog
        context['one'] = one
        context['two'] = two
        context['scrmi'] = prog.studentclassregmoduleinfo
        context['checked_in'] = Record.objects.filter(program=prog, event='attended', user=user).exists()

        return render_to_response(self.baseDir()+'schedule.html', request, context)

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Webapp')
    @meets_cap
    def onsitemap(self, request, tl, one, two, module, extra, prog):
        context = {}
        context['user'] = request.user
        context['program'] = prog
        context['one'] = one
        context['two'] = two
        context['center'] = Tag.getTag('program_center', default='')
        #extra should be a classroom id
        if extra:
            #gets lat/long of classroom and adds it to context
            context['classroom'] = "37.427490, -122.170267"
        return render_to_response(self.baseDir()+'map.html', request, context)

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Webapp')
    @meets_cap
    def onsitecatalog(self, request, tl, one, two, module, extra, prog):
        user = request.user
        context = {}
        context['user'] = user
        context['program'] = prog
        context['one'] = one
        context['two'] = two
        user_grade = user.getGrade(self.program)
        if extra:
            try:
                ts = Event.objects.get(id=int(extra), program=prog)
            except:
                raise ESPError('Please use the links on the schedule page.', log=False)
            context['timeslot'] = ts
            classes = list(ClassSubject.objects.catalog(prog, ts))
            classes = filter(lambda c: c.grade_min <=user_grade and c.grade_max >= user_grade, classes)
            context['checked_in'] = Record.objects.filter(program=prog, event='attended', user=user).exists()

        else:
            classes = list(ClassSubject.objects.catalog(prog))

        categories = {}

        for cls in classes:
            categories[cls.category_id] = {'id':cls.category_id, 'category':cls.category_txt if hasattr(cls, 'category_txt') else cls.category.category}

        context['classes'] = classes
        context['categories'] = categories.values()
        context['prereg_url'] = prog.get_learn_url() + 'onsiteaddclass'

        return render_to_response(self.baseDir()+'catalog.html', request, context)

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Webapp')
    @meets_cap
    def onsitesurvey(self, request, tl, one, two, module, extra, prog):
        context = {}
        context['user'] = request.user
        context['program'] = prog
        context['one'] = one
        context['two'] = two
        return render_to_response(self.baseDir()+'survey.html', request, context)

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Webapp')
    def onsiteaddclass(self, request, tl, one, two, module, extra, prog):
        if StudentClassRegModule.addclass_logic(request, tl, one, two, module, extra, prog):
            return HttpResponseRedirect(prog.get_learn_url() + 'studentonsite')

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Webapp')
    def onsiteclearslot(self, request, tl, one, two, module, extra, prog):
        result = StudentClassRegModule.clearslot_logic(request, tl, one, two, module, extra, prog)
        return HttpResponseRedirect(prog.get_learn_url() + 'studentonsite')

    class Meta:
        proxy = True
        app_label = 'modules'
