
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

from esp.program.modules.forms.onsite import TeacherCheckinForm
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser, UserBit, User
from esp.cal.models import Event
from esp.datatree.models import *
from django              import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string, select_template
from django.db.models import Min
from datetime import datetime, timedelta

import simplejson as json


class TeacherCheckinModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Teacher Check-In",
            "link_title": "Check-in teachers",
            "module_type": "onsite",
            "seq": 10
            }

    
    def checkIn(self, teacher, prog):
        """Check teacher into program for the rest of the day"""
        if teacher.isTeacher() and teacher.getTaughtClassesFromProgram(prog).exists():
            now = datetime.now()
            endtime = datetime(now.year, now.month, now.day+1) - timedelta(seconds=1)
            new_bit, created = UserBit.objects.get_or_create(user=teacher,
                                                                qsc=prog.anchor,
                                                                verb=GetNode('V/Flags/Registration/Teacher/Arrived'),
                                                                enddate=endtime)
            if created:
                return '%s %s is checked in until %s.' % (teacher.first_name, teacher.last_name, str(endtime))
            else:
                return '%s %s has already been checked in until %s.' % (teacher.first_name, teacher.last_name, str(endtime))
        else:
            return '%s %s is not a teacher for %s.' % (teacher.first_name, teacher.last_name, prog.niceName())
    
    @main_call
    @needs_admin
    def teachercheckin(self, request, tl, one, two, module, extra, prog):
        context = {}
        if request.method == 'POST':
            form = TeacherCheckinForm(request.POST)
            if form.is_valid():
                teacher = ESPUser(form.cleaned_data['user'])
                context['message'] = self.checkIn(teacher, prog)
        else:
            form = TeacherCheckinForm()
        
        context['module'] = self
        context['form'] = form
        return render_to_response(self.baseDir()+'teachercheckin.html', request, (prog, tl), context)
    
    @aux_call
    @needs_admin
    def missingteachers(self, request, tl, one, two, module, extra, prog):
        if 'start' in request.GET:
            starttime = Event.objects.get(id=request.GET['start'])
        else:
            starttime = Event.objects.filter(start__gte=datetime.now() - timedelta(minutes=30)).order_by('start')[0]
        sections = prog.sections().annotate(begin_time=Min("meeting_times__start")).filter(
                        status=10, parent_class__status=10,
                        begin_time=starttime.start
                        )
        teachers = ESPUser.objects.filter(userbit__in=UserBit.valid_objects(),
                                          userbit__qsc__classsubject__sections__in=sections,
                                          userbit__verb=GetNode('V/Flags/Registration/Teacher'))
        arrived = teachers.filter(userbit__in=UserBit.valid_objects(),
                                  userbit__qsc=prog.anchor,
                                  userbit__verb=GetNode('V/Flags/Registration/Teacher/Arrived'))
        missing = teachers.exclude(id__in=arrived)
        missing_sections = sections.filter(parent_class__anchor__userbit_qsc__in=UserBit.valid_objects(),
                                           parent_class__anchor__userbit_qsc__user__in=missing,
                                           parent_class__anchor__userbit_qsc__verb=GetNode('V/Flags/Registration/Teacher'))
        userbits = UserBit.valid_objects().filter(qsc__classsubject__sections__in=missing_sections,
                                                  verb=GetNode('V/Flags/Registration/Teacher')) \
                                          .values_list('user', 'qsc__classsubject', 'qsc__friendly_name')
        teacher_data = {}
        for teacher in arrived:
            teacher_data[teacher.id] = {'name': teacher.name(), 'arrived': True}
        for teacher in missing:
            teacher_data[teacher.id] = {'name': teacher.name(), 'arrived': False}
        class_data = {}
        for teacher_id, class_id, class_name in userbits:
            if class_id not in class_data:
                class_data[class_id] = {'name': class_name, 'teachers':[]}
            class_data[class_id]['teachers'].append(teacher_id)
        json_data = {'teachers': teacher_data, 'classes': class_data}
        return HttpResponse(json.dumps(json_data))
    
    class Meta:
        abstract = True
