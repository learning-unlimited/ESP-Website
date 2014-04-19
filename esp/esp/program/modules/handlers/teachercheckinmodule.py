
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
from esp.program.models.class_ import ClassSubject
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser, Record, ContactInfo
from esp.cal.models import Event
from esp.datatree.models import *
from django              import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string, select_template
from django.db.models.aggregates import Min
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
    
    def checkIn(self, teacher, prog, when=None):
        """Check teacher into program for the rest of the day (given by 'when').

        'when' defaults to datetime.now()."""
        if when is None:
            when = datetime.now()
        if teacher.isTeacher() and teacher.getTaughtClassesFromProgram(prog).exists():
            endtime = datetime(when.year, when.month, when.day) + timedelta(days=1, seconds=-1)
            checked_in_already = Record.user_completed(teacher, 'teacher_checked_in', prog, when, only_today=True)
            if not checked_in_already:
                Record.objects.create(user=teacher, event='teacher_checked_in', program=prog, time=when)
                return '%s is checked in until %s.' % (teacher.name(), str(endtime))
            else:
                return '%s has already been checked in until %s.' % (teacher.name(), str(endtime))
        else:
            return '%s is not a teacher for %s.' % (teacher.name(), prog.niceName())
    
    def undoCheckIn(self, teacher, prog, when=None):
        """Undo what checkIn does"""
        if when is None:
            when = datetime.now()
        records = Record.filter(teacher, 'teacher_checked_in', prog, when, only_today=True)
        if records:
            records.delete()
            return '%s is no longer checked in.' % teacher.name()
        else:
            return '%s was not checked in for %s.' % (teacher.name(), prog.niceName())
    
    @main_call
    @needs_onsite
    def teachercheckin(self, request, tl, one, two, module, extra, prog):
        context = {}
        if 'when' in request.GET:
            form = TeacherCheckinForm(request.GET)
            if form.is_valid():
                when = form.cleaned_data['when']
                if when is not None:
                    context['when'] = when
                    context['url_when'] = request.GET['when']
        else:
            form = TeacherCheckinForm()
        
        context['module'] = self
        context['form'] = form
        
        context['time_slots'] = prog.getTimeSlots()
        now = prog.getTimeSlots().filter(start__gte=datetime.now()).order_by('start')
        if now.exists():
            context['now'] = now[0]
        else:
            context['now'] = None
        
        return render_to_response(self.baseDir()+'teachercheckin.html', request, context)
    
    @aux_call
    @needs_onsite
    def ajaxteachercheckin(self, request, tl, one, two, module, extra, prog):
        """
        POST to this view to change the check-in status of a teacher on a given day.

        POST data:
          'teacher':          The teacher's username.
          'undo' (optional):  If 'true', undoes a previous check-in.
                              Otherwise, the teacher is checked in.
          'when' (optional):  If given, processes checkIn or undoCheckIn as if
                              it were that time.  Should be given in the format
                              "%m/%d/%Y %H:%M".
        """
        json_data = {}
        if 'teacher' in request.POST:
            teachers = ESPUser.objects.filter(username=request.POST['teacher'])
            if not teachers.exists():
                json_data['message'] = 'User not found!'
            else:
                json_data['name'] = teachers[0].name()
                when = None
                if 'when' in request.POST:
                    try:
                        when = datetime.strptime(request.POST['when'], "%m/%d/%Y %H:%M")
                    except:
                        pass
                if 'undo' in request.POST and request.POST['undo'].lower() == 'true':
                    json_data['message'] = self.undoCheckIn(teachers[0], prog, when)
                else:
                    json_data['message'] = self.checkIn(teachers[0], prog, when)
        return HttpResponse(json.dumps(json_data), mimetype='text/json')
    
    def getMissingTeachers(self, prog, starttime=None, when=None):
        """Return a list of class sections with missing teachers"""
        sections = prog.sections().annotate(begin_time=Min("meeting_times__start")) \
                                  .filter(status=10, parent_class__status=10, begin_time__isnull=False)
        if starttime is not None:
            sections = sections.filter(begin_time=starttime.start)
        teachers = ESPUser.objects.filter(classsubject__sections__in=sections)
        arrived = teachers.filter(record__program=prog,
                                  record__event='teacher_checked_in')
        missing = teachers.exclude(id__in=arrived)
        missing_sections = sections.filter(parent_class__teachers__in=missing,)
        teacher_tuples = ESPUser.objects.filter(classsubject__sections__in=missing_sections) \
                                          .distinct() \
                                          .values_list('id', 'classsubject__id', 'classsubject__title') \
                                          .order_by('last_name', 'first_name')
        
        teacher_dict = {}
        for teacher in list(arrived) + list(missing):
            contact = teacher.getLastProfile().contact_user
            if contact is None:
                contact = ContactInfo(phone_cell='N/A')
            teacher_dict[teacher.id] = {'username': teacher.username,
                                        'name': teacher.name(),
                                        'last_name': teacher.last_name,
                                        'phone': contact.phone_cell or contact.phone_day,
                                        'arrived': True}
        for teacher in missing:
            teacher_dict[teacher.id]['arrived'] = False
        
        class_dict = {}
        class_arr = []
        for teacher_id, class_id, class_name in teacher_tuples:
            if class_id not in class_dict:
                class_dict[class_id] = {'id': ClassSubject.objects.get(id=class_id).emailcode(),
                                        'name': class_name,
                                        'teachers': [],
                                        'any_arrived': False}
                class_arr.append(class_dict[class_id])
            class_dict[class_id]['teachers'].append(teacher_dict[teacher_id])
        
        for sec in missing_sections:
            if sec.parent_class.id in class_dict:
                class_ = class_dict[sec.parent_class.id]
                class_['room'] = (sec.prettyrooms() or [None])[0]
                if 'time' in class_:
                    class_['time'] = min(class_['time'], sec.begin_time)
                else:
                    class_['time'] = sec.begin_time
        
        #Move sections where at least one teacher showed up to end of list
        for sec in class_arr:
            for teacher in sec['teachers']:
                if teacher['arrived']:
                    sec['any_arrived'] = True
                    break
        class_arr = [sec for sec in class_arr if sec['any_arrived'] == False] + \
                    [sec for sec in class_arr if sec['any_arrived'] == True]
        
        return class_arr, teacher_dict
    
    @aux_call
    @needs_onsite
    def missingteachers(self, request, tl, one, two, module, extra, prog):
        if 'start' in request.GET:
            starttime = Event.objects.get(id=request.GET['start'])
        else:
            starttime = None
        context = {}
        form = TeacherCheckinForm(request.GET)
        if form.is_valid():
            when = form.cleaned_data['when']
            if when is not None:
                context['when'] = when
                context['url_when'] = request.GET['when']
        else:
            when = None
        context['sections'], teachers = self.getMissingTeachers(prog, starttime, when)
        context['arrived'] = [teacher for teacher in teachers.values() if teacher['arrived']]
        context['start_time'] = starttime
        return render_to_response(self.baseDir()+'missingteachers.html', request, context)
    
    class Meta:
        abstract = True
