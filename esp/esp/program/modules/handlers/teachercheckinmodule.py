
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
from esp.program.modules.handlers.grouptextmodule import GroupTextModule
from esp.program.models import RegistrationProfile
from esp.program.models.class_ import ClassSubject, ClassSection
from esp.program.models.flags import ClassFlagType
from esp.utils.web import render_to_response
from esp.utils.decorators import json_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser, PersistentQueryFilter, Record, ContactInfo
from esp.cal.models import Event
from django              import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string, get_template
from django.db.models.aggregates import Min, Max
from django.db.models.query   import Q
from datetime import datetime, timedelta, time

import collections
import json

class TeacherCheckinModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Teacher Check-In",
            "link_title": "Check in teachers",
            "module_type": "onsite",
            "seq": 10,
            "choosable": 1,
            }

    def checkIn(self, teacher, prog, when=None):
        """Check teacher into program for the rest of the day (given by 'when').

        'when' defaults to datetime.now()."""
        if when is None:
            when = datetime.now()
        if teacher.getTaughtClassesFromProgram(prog).exists():
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
        return HttpResponse(json.dumps(json_data), content_type='text/json')

    @aux_call
    @json_response(None)
    @needs_onsite
    def ajaxteachertext(self, request, tl, one, two, module, extra, prog):
        """
        POST to this view to text a teacher a reminder to check in.

        POST data:
          'username':       The teacher's username.
          'section':        Section ID number.
        """
        if GroupTextModule.is_configured():
            if 'username' in request.POST and 'section' in request.POST:
                sec = ClassSection.objects.get(id=request.POST['section'])
                teacher = PersistentQueryFilter.create_from_Q(ESPUser, Q(username=request.POST['username']))
                template = get_template(self.baseDir() + 'teachertext.txt')
                context = {'prog': prog, 'one': one, 'two': two, 'sec': sec, 'teacher': teacher}
                message = template.render(context)
                log = GroupTextModule.sendMessages(teacher, message, True)
                if "error" in log:
                    return {'message': "Error texting teacher"}
                else:
                    return {'message': "Texted teacher"}
            else:
                return {'message': "Username and/or section not provided"}
        else:
            return {'message': "Twilio not configured"}

    @aux_call
    @needs_onsite
    def ajaxclassdetail(self, request, tl, one, two, module, extra, prog):
        """
        AJAX to this endpoint to get the details for a class, as an HTML
        snippet
        """
        context = {}
        context['class'] = ClassSubject.objects.get(id=request.GET['class'])
        if request.GET['show_flags']:
            context['show_flags'] = True
            context['flag_types'] = ClassFlagType.get_flag_types(self.program)
        return render_to_response(self.baseDir()+'classdetail.html', request, context)

    @staticmethod
    def get_phones(users, default = '(missing contact info)'):
        """
        Given a list or QuerySet of users, create a dictionary that maps user
        ids to phone numbers for displaying.
        """

        # This is an optimized version of doing this for each user:

        #   contact_info = user.getLastProfile().contact_user
        #   if contact_info:
        #       return contact_info.phone_cell or contact_info.phone_day or default
        #   return default

        # Only Postgres supports the following fancy database operation! See
        # http://stackoverflow.com/a/20129229/3243497 .

        profiles = (RegistrationProfile.objects
                .filter(user__in=users)
                .order_by('user__id', '-last_ts')
                .distinct('user__id')
                .values_list('user', 'contact_user__phone_cell', 'contact_user__phone_day'))
        phone_entries = ((user, cell or day or default) for (user, cell, day) in profiles)
        return collections.defaultdict(lambda _: default, phone_entries)

    def getMissingTeachers(self, prog, date=None, starttime=None, when=None,
                           show_flags=True, default_phone = '(missing contact info)'):
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
          default_phone (string, opt):  A string that should be used if there
                                        is no valid phone number for a teacher.

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
            'parent_class__parent_program',
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
            classsubject__sections__in=sections).distinct()
        arrived_teachers = teachers.filter(
            record__program=prog,
            record__event='teacher_checked_in',
            record__time__lte=when,
            record__time__year=when.year,
            record__time__month=when.month,
            record__time__day=when.day).distinct()

        # To save multiple calls to getLastProfile, precompute the teacher
        # phones.
        teacher_phones = self.get_phones(teachers, default_phone)
        arrived = dict()
        for teacher in arrived_teachers:
            teacher.phone = teacher_phones.get(teacher.id, default_phone)
            arrived[teacher.id] = teacher

        sections_by_class = {}
        for section in sections:
            # Put the first section of each class into sections_by_class
            if (section.parent_class.id not in sections_by_class
                    or sections_by_class[section.parent_class_id].begin_time > section.begin_time):
                # Precompute some things and pack them on the section.
                teacher_status = [teacher.id in arrived for teacher in section.teachers]
                section.all_arrived = all(teacher_status) and section.teachers.count() > 0
                section.any_arrived = any(teacher_status) and section.teachers.count() > 0
                section.room = (section.prettyrooms() or [None])[0]
                section.unique_resources = section.resourceassignments().order_by('assignment_group').distinct('assignment_group')
                # section.teachers is a property, so we can't add extra
                # data to the ESPUser objects and have them stick. We must
                # make a new list and then modify that.
                section.teachers_list = list(section.teachers)
                for teacher in section.teachers_list:
                    teacher.phone = teacher_phones.get(teacher.id, default_phone)
                sections_by_class[section.parent_class_id] = section

        sections = [
            section for section in sections_by_class.values()
            if not section.any_arrived
        ] + [
            section for section in sections_by_class.values()
            if section.any_arrived and not section.all_arrived
        ] + [
            section for section in sections_by_class.values()
            if section.all_arrived
        ]

        return sections, arrived

    def getMissingResources(self, prog, date=None, starttime=None, default_phone = '(missing contact info)'):
        """Return a list of class sections that have ended but have not returned their floating resources.

        Parameters:
          prog (Program):                 The program.
          date (date, optional):          If given, the return only includes
                                          missing resources for sections that ended
                                          on a previous day.
          starttime (datetime, optional): If given, the return only includes
                                          missing resources for sections that ended
                                          before this time. Overrides date if
                                          both are given.
          default_phone (string, opt):    A string that should be used if there
                                          is no valid phone number for a teacher.

        Returns:
          sections_list:  A list of all sections that have ended but have not returned
                          their resources as of starttime or date. Each item of the list
                          has an attribute `missing_resources` that is a list of the
                          floating resources that have not been returned.
        """

        sections = prog.sections().annotate(end_time=Max("meeting_times__end")) \
                                  .filter(status=10, parent_class__status=10, end_time__isnull=False) \
                                  .order_by('end_time')
        if starttime is None and date is not None:
            starttime = datetime.combine(date, time())
        if starttime is not None:
            sections = sections.filter(end_time__lt=starttime)

        teachers = ESPUser.objects.filter(classsubject__sections__in=sections).distinct()
        teacher_phones = self.get_phones(teachers, default_phone)

        sections_list = []
        for section in sections:
            # Use distinct() to avoid showing duplicate resource assignments for sections that are multiple blocks long
            resources = section.resourceassignments().filter(returned=False).order_by('assignment_group').distinct('assignment_group')
            if len(resources):
                section.missing_resources = resources
                section.room = (section.prettyrooms() or [None])[-1]
                section.teachers_list = list(section.teachers)
                for teacher in section.teachers_list:
                    teacher.phone = teacher_phones.get(teacher.id, default_phone)
                sections_list.append(section)

        return sections_list

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
          'default_phone' (optional): A string that should be used if there
                              is no valid phone number for a teacher.
        """
        starttime = date = next = previous = None
        default_phone = request.GET.get('default_phone', '(missing contact info)')
        if 'start' in request.GET:
            starttime = Event.objects.get(id=request.GET['start'])
            date = starttime.start.date()
            times = prog.getTimeSlotList()
            i = times.index(starttime)
            if i > 0:
                previous = times[i - 1]
            if i < len(times) - 1:
                next = times[i + 1]
        elif 'date' in request.GET:
            date = datetime.strptime(request.GET['date'], "%m/%d/%Y").date()
            dates = prog.dates()
            i = dates.index(date)
            if i > 0:
                previous = dates[i - 1].strftime('%m/%d/%Y')
            if i < len(dates) - 1:
                next = dates[i + 1].strftime('%m/%d/%Y')
        context = {}
        context['default_phone'] = default_phone
        context['text_configured'] = GroupTextModule.is_configured()
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
            prog, date, starttime, when, show_flags, default_phone)
        context['missing_resources'] = self.getMissingResources(prog, date, getattr(starttime, "start", None))
        if show_flags:
            context['show_flags'] = True
            context['flag_types'] = ClassFlagType.get_flag_types(self.program)
        context['res_types'] = prog.getFloatingResources()
        context['start_time'] = starttime
        context['next'] = next
        context['previous'] = previous
        return render_to_response(self.baseDir()+'missingteachers.html',
                                  request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
