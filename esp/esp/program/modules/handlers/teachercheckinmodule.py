
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

from esp.program.modules.forms.onsite import TeacherCheckinForm
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules import module_ext
from esp.program.models.class_ import ClassSubject
from esp.program.models.flags import ClassFlagType
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
        when = None
        if 'when' in request.GET:
            form = TeacherCheckinForm(request.GET)
            if form.is_valid():
                when = form.cleaned_data['when']
                if when is not None:
                    context['when'] = when
                    context['url_when'] = request.GET['when']
        else:
            form = TeacherCheckinForm()

        if when is None:
            when = datetime.now()
        context['now'] = when

        context['module'] = self
        context['form'] = form
        
        context['time_slots'] = prog.getTimeSlots()
        
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

    @staticmethod
    def get_phone(user):
        """Get the phone number to display for a user."""
        contact_info = user.getLastProfile().contact_user
        default = '(missing contact info)'
        if contact_info:
            return contact_info.phone_cell or contact_info.phone_day or default
        return default

    def getMissingTeachers(self, prog, date=None, starttime=None, when=None,
                           show_flags=True):
        """Return a list of class sections with missing teachers as of 'when'.

        Parameters:
          prog (Program):               The program.
          date (date, optional):        A teacher needs to check in if they have
                                        a class on 'date'. Of those teachers, a
                                        teacher is considered to have arrived if
                                        they have an appropriate Record on
                                        when.date(). The missing teachers is the
                                        complement of that set.
                                        If 'starttime' is passed, should pass
                                        starttime.start.date() as 'date'.
                                        If 'date' is None, classes on all days
                                        are considered.
          starttime (Event, optional):  If given, the return only includes
                                        missing teachers for classes that start
                                        at this time.
          when (datetime, optional):    The return reflects the state of
                                        teacher check-ins on this date, as of
                                        this time.
                                        Defaults to datetime.now().
          show_flags (bool, optional):  If True, prefetch class flags
                                        information for the list of class
                                        sections.

        NOTE: For multi-week programs, classes are only scheduled once on the
        website, even though they meet multiple times and teachers need to be
        checked in each week. Thus, 'date' is the date that the website thinks
        the class is scheduled for, and is used only to filter the set of
        classes that are shown; and 'when' is the current date (or a past one),
        and is used to filter the set of checked-in Records, so that the view
        shows who is not checked in yet for the day.

        Returns the 2-tuple (sections, arrived):
            sections: A list of all sections starting at the given time or on
                      the given date which do not have all teachers checked in,
                      with those with no teachers checked in first.  If a date
                      was given, includes only the first section of each class
                      on that date.
            arrived:  A dict of id -> teacher for all teachers who have already
                      checked in.
        """
        if when is None:
            when = datetime.now()

        sections = prog.sections().annotate(begin_time=Min("meeting_times__start")) \
                                  .filter(status=10, parent_class__status=10, begin_time__isnull=False)
        if date is not None:
            # Only consider classes happening on this date.
            sections = sections.filter(meeting_times__start__year  = date.year,
                                       meeting_times__start__month = date.month,
                                       meeting_times__start__day   = date.day)
        if starttime is not None:
            sections = sections.filter(begin_time=starttime.start)
        sections = sections.select_related(
            'parent_class',
            'parent_class__category',
        ).prefetch_related(
            'parent_class__teachers',
            'parent_class__sections',
        )
        if show_flags:
            sections = sections.prefetch_related(
                'parent_class__flags',
                'parent_class__flags__flag_type',
                'parent_class__flags__modified_by',
                'parent_class__flags__created_by',
            )
        sections = sections.distinct()

        # A teacher is considered to have arrived if:
        # - They have a "teacher_checked_in" Record for the program
        # - which is from before 'when' (since we are considering the state of
        #   check-in at this time).
        # - which is from the same date as 'when'.
        teachers = ESPUser.objects.filter(
            classsubject__sections__in=sections,
            record__program=prog,
            record__event='teacher_checked_in',
            record__time__lte=when,
            record__time__year=when.year,
            record__time__month=when.month,
            record__time__day=when.day).distinct()

        # To save multiple calls to getLastProfile, precompute the teacher
        # phones.
        teacher_phones = {}
        for section in sections:
            for teacher in section.teachers:
                if teacher.id not in teacher_phones:
                    teacher_phones[teacher.id] = self.get_phone(teacher)

        arrived = {}
        for teacher in teachers:
            if teacher.id not in teacher_phones:
                teacher_phones[teacher.id] = self.get_phone(teacher)
            teacher.phone = teacher_phones[teacher.id]
            arrived[teacher.id] = teacher

        sections_by_class = {}
        for section in sections:
            if not all(teacher.id in arrived for teacher in section.teachers):
                # Put the first section of each class into sections_by_class
                if (section.parent_class.id not in sections_by_class
                        or sections_by_class[section.parent_class_id].begin_time > section.begin_time):
                    # Precompute some things and pack them on the section.
                    section.any_arrived = any(teacher.id in arrived
                                              for teacher in section.teachers)
                    section.room = (section.prettyrooms() or [None])[0]
                    # section.teachers is a property, so we can't add extra
                    # data to the ESPUser objects and have them stick. We must
                    # make a new list and then modify that.
                    section.teachers_list = list(section.teachers)
                    for teacher in section.teachers_list:
                        teacher.phone = teacher_phones[teacher.id]
                    sections_by_class[section.parent_class_id] = section

        sections = [
            section for section in sections_by_class.values()
            if not section.any_arrived
        ] + [
            section for section in sections_by_class.values()
            if section.any_arrived
        ]

        return sections, arrived

    @aux_call
    @needs_onsite
    def missingteachers(self, request, tl, one, two, module, extra, prog):
        """
        View that displays the teacher check-in page for missing teachers.

        GET data:
          'date' (optional):  See documentation for getMissingTeachers().
                              Should be given in the format "%m/%d/%Y".
          'start' (optional): See the documentation for the 'starttime'
                              parameter for getMissingTeachers().
                              Should be given as the id number of the Event.
          'when' (optional):  See documentation for getMissingTeachers().
                              getMissingTeachers(). Should be given in the
                              format "%m/%d/%Y %H:%M".
        """
        starttime = date = None
        if 'start' in request.GET:
            starttime = Event.objects.get(id=request.GET['start'])
            date = starttime.start.date()
        elif 'date' in request.GET:
            date = datetime.strptime(request.GET['date'], "%m/%d/%Y").date()
        context = {}
        form = TeacherCheckinForm(request.GET)
        if form.is_valid():
            when = form.cleaned_data['when']
            if when is not None:
                context['when'] = when
                context['url_when'] = request.GET['when']
        else:
            when = None
        show_flags = self.program.program_modules.filter(handler='ClassFlagModule').exists()
        context['date'] = date
        context['sections'], context['arrived'] = self.getMissingTeachers(
            prog, date, starttime, when, show_flags)
        if show_flags:
            context['show_flags'] = True
            context['flag_types'] = ClassFlagType.get_flag_types(self.program)
        context['start_time'] = starttime
        return render_to_response(self.baseDir()+'missingteachers.html',
                                  request, context)

    class Meta:
        proxy = True
