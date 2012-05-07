
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
from esp.users.models    import ESPUser, UserBit, User, ContactInfo
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

    
    def checkIn(self, teacher, prog):
        """Check teacher into program for the rest of the day"""
        if teacher.isTeacher() and teacher.getTaughtClassesFromProgram(prog).exists():
            now = datetime.now()
            endtime = datetime(now.year, now.month, now.day) + timedelta(days=1, seconds=-1)
            new_bit, created = UserBit.objects.get_or_create(user=teacher,
                                                                qsc=prog.anchor,
                                                                verb=GetNode('V/Flags/Registration/Teacher/Arrived'),
                                                                enddate=endtime)
            if created:
                return '%s is checked in until %s.' % (teacher.name(), str(endtime))
            else:
                return '%s has already been checked in until %s.' % (teacher.name(), str(endtime))
        else:
            return '%s is not a teacher for %s.' % (teacher.name(), prog.niceName())
    
    def undoCheckIn(self, teacher, prog):
        """Undo what checkIn does"""
        userbits = UserBit.valid_objects().filter(user=teacher,
                                                qsc=prog.anchor,
                                                verb=GetNode('V/Flags/Registration/Teacher/Arrived'))
        if userbits:
            userbits.update(enddate=datetime.now())
            UserBit.updateCache(teacher.id)
            return '%s is no longer checked in.' % teacher.name()
        else:
            return '%s was not checked in for %s.' % (teacher.name(), prog.niceName())
    
    @main_call
    @needs_admin
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
        
        return render_to_response(self.baseDir()+'teachercheckin.html', request, (prog, tl), context)
    
    @aux_call
    @needs_admin
    def ajaxteachercheckin(self, request, tl, one, two, module, extra, prog):
        json_data = {}
        if 'teacher' in request.POST:
            teachers = ESPUser.objects.filter(username=request.POST['teacher'])
            if not teachers.exists():
                json_data['message'] = 'User not found!'
            else:
                json_data['name'] = teachers[0].name()
                if 'undo' in request.POST and request.POST['undo'].lower() == 'true':
                    json_data['message'] = self.undoCheckIn(teachers[0], prog)
                else:
                    json_data['message'] = self.checkIn(teachers[0], prog)
        return HttpResponse(json.dumps(json_data), mimetype='text/json')
    
    def getMissingTeachers(self, prog, starttime=None, when=None):
        """Return a list of class sections with missing teachers"""
        sections = prog.sections().annotate(begin_time=Min("meeting_times__start")) \
                                  .filter(status=10, parent_class__status=10, begin_time__isnull=False)
        if starttime is not None:
            sections = sections.filter(begin_time=starttime.start)
        teachers = ESPUser.objects.filter(userbit__in=UserBit.valid_objects(when),
                                          userbit__qsc__classsubject__sections__in=sections,
                                          userbit__verb=GetNode('V/Flags/Registration/Teacher'))
        arrived = teachers.filter(userbit__in=UserBit.valid_objects(when),
                                  userbit__qsc=prog.anchor,
                                  userbit__verb=GetNode('V/Flags/Registration/Teacher/Arrived'))
        missing = teachers.exclude(id__in=arrived)
        missing_sections = sections.filter(parent_class__anchor__userbit_qsc__in=UserBit.valid_objects(when),
                                           parent_class__anchor__userbit_qsc__user__in=missing,
                                           parent_class__anchor__userbit_qsc__verb=GetNode('V/Flags/Registration/Teacher'))
        userbits = UserBit.valid_objects(when).filter(qsc__classsubject__sections__in=missing_sections,
                                                  verb=GetNode('V/Flags/Registration/Teacher')) \
                                          .distinct() \
                                          .values_list('user', 'qsc__classsubject', 'qsc__friendly_name') \
                                          .order_by('user__last_name', 'user__first_name')
        
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
        for teacher_id, class_id, class_name in userbits:
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
    @needs_admin
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
        return render_to_response(self.baseDir()+'missingteachers.html', request, (prog, tl), context)
    
    class Meta:
        abstract = True
