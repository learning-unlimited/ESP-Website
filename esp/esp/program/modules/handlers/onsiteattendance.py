
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

from django.db.models.query      import Q

from esp.program.modules.base import ProgramModuleObj, needs_onsite, main_call, aux_call
from esp.program.models import StudentRegistration, ClassSection
from esp.utils.web import render_to_response
from esp.users.models import ESPUser
from esp.cal.models import Event
from esp.utils.query_utils import nest_Q
from esp.program.modules.handlers.teacherclassregmodule import TeacherClassRegModule

import datetime

class OnSiteAttendance(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "On-Site Student Attendance",
            "link_title": "Check Student Attendance",
            "module_type": "onsite",
            "seq": 1,
            "choosable": 1,
            }

    @main_call
    @needs_onsite
    def attendance(self, request, tl, one, two, module, extra, prog):
        context = {'program': prog, 'one': one, 'two': two}

        if extra:
            tsid = extra
            timeslots = Event.objects.filter(id = tsid)
            if len(timeslots) == 1:
                timeslot = timeslots[0]
                context['timeslot'] = timeslot
                when_get = request.GET.get("when", "")
                if when_get != "":
                    # if a date is specified, use that date and the end time of the timeblock
                    date = datetime.datetime.strptime(when_get, "%Y-%m-%d").date()
                    when = datetime.datetime.combine(date, timeslot.end.time())
                else:
                    # otherwise, just use the end time (and date) of the timeblock
                    when = timeslot.end
                    date = when.date()
                context['when'] = when
                time_min = datetime.datetime.combine(date, timeslot.start_w_buffer().time())
                time_max = datetime.datetime.combine(date, timeslot.end.time())
                #Students that are marked as attending a class during this timeslot on the specified day
                attended = ESPUser.objects.filter(Q(studentregistration__section__meeting_times=timeslot, studentregistration__relationship__name="Attended") & nest_Q(StudentRegistration.is_valid_qobject(when), 'studentregistration')).distinct()
                #Students that are enrolled in a class during this timeslot on the specified day
                enrolled = ESPUser.objects.filter(Q(studentregistration__section__meeting_times=timeslot, studentregistration__relationship__name="Enrolled") & nest_Q(StudentRegistration.is_valid_qobject(when), 'studentregistration')).distinct()
                #Checked-out students
                checked_out = prog.checkedOutStudents(time_max)
                #Students that have been checked in for the program at any time before the end of this timeslot on the specified day, excluding students that have been checked out
                checked_in = ESPUser.objects.filter(Q(record__event='attended', record__program=prog, record__time__lt=time_max)).exclude(id__in=checked_out).distinct()
                #Students that have been checked in for the program during this timeslot on the specified day
                checked_in_during_ts = ESPUser.objects.filter(Q(record__event='attended', record__program=prog, record__time__range=(time_min, time_max))).distinct()
                #Students that have been checked in for the program at any time before the end of this timeslot on the specified day (and are not checked out) but are not attending a class during this timeslot on the specified day
                not_attending = checked_in.exclude(id__in=attended)
                #Get the classes that they aren't attending (if any)
                enrolled_srs = {sr.user: sr.section for sr in StudentRegistration.valid_objects(when).filter(section__meeting_times=timeslot, relationship__name="Enrolled").select_related('user')}
                for student in not_attending:
                    student.missed_class = enrolled_srs.get(student, None)
                #Students attending classes during this timeslot on the specified day that they were enrolled in because they are attending it (and were not enrolled in beforehand)
                onsite_srs = {sr.user: sr.section for sr in StudentRegistration.valid_objects(when).filter(section__meeting_times=timeslot, relationship__name="OnSite/AttendedClass").select_related('user')}
                onsite = onsite_srs.keys()
                for student in onsite:
                    student.enrolled = True
                    student.attended_class = onsite_srs.get(student, None)
                    student.enrolled_class = student.attended_class
                #Add students attending classes during this timeslot on the specified day that they aren't enrolled in
                attended_srs = {sr.user: sr.section for sr in StudentRegistration.valid_objects(when).filter(section__meeting_times=timeslot, relationship__name="Attended").select_related('user')}
                for student in attended:
                    attended_section = attended_srs.get(student, None)
                    enrolled_section = enrolled_srs.get(student, None)
                    #If they aren't enrolled in a class or the enrolled class is not the attended class
                    if enrolled_section is None or attended_section != enrolled_section:
                        #If they aren't already in the list of onsite students
                        if student not in onsite:
                            student.enrolled = False
                            student.attended_class = attended_section
                            student.enrolled_class = enrolled_section
                            onsite.append(student)
                #Sections during this timeslot with no attendance recorded on the specified day
                no_attendance = ClassSection.objects.filter(meeting_times=timeslot, status__gt=0).exclude(id__in=StudentRegistration.valid_objects(when).filter(section__meeting_times=timeslot, relationship__name="Attended").values_list('section__id', flat = True))
                context.update({
                                'attended': attended,
                                'checked_in': checked_in,
                                'onsite': onsite,
                                'enrolled': enrolled,
                                'checked_in_ts': checked_in_during_ts,
                                'not_attending': not_attending,
                                'no_attendance': no_attendance
                               })

        return render_to_response(self.baseDir()+'attendance.html', request, context)

    @aux_call
    @needs_onsite
    def section_attendance(self, request, tl, one, two, module, extra, prog):
        context = {'program': prog, 'tl': tl, 'one': one, 'two': two}

        timeslots = Event.objects.filter(id=extra, program = prog)
        if len(timeslots) == 1:
            timeslot = timeslots[0]
            context['timeslot'] = timeslot
            context['sched_sections'] = ClassSection.objects.filter(parent_class__parent_program=prog, meeting_times=timeslot).distinct().order_by('id')

            secid = 0
            if 'secid' in request.POST:
                secid = request.POST['secid']
            elif 'secid' in request.GET:
                secid = request.GET['secid']
            sections = ClassSection.objects.filter(id = secid)
            if len(sections) == 1:
                section = sections[0]
                context['section'], context['not_found'] = TeacherClassRegModule.process_attendance(section, request, prog)

        return render_to_response('program/modules/teacherclassregmodule/section_attendance.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
