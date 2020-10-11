
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
import datetime
import logging
from django.db.models import signals
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.models import StudentRegistration, RegistrationType
from esp.users.models import ESPUser
from esp.utils.decorators import cached_module_view, json_response
from esp.utils.web import render_to_response

logger = logging.getLogger(__name__)

class UnenrollModule(ProgramModuleObj):
    """ Frontend to kick students from classes. """

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Unenroll Students",
            "link_title": "Unenroll Students",
            "module_type": "onsite",
            "seq": 100,
            "choosable": 1,
        }

    class Meta:
        proxy = True
        app_label = 'modules'

    @main_call
    @needs_admin
    def unenroll_students(self, request, tl, one, two, module, extra, prog):
        """
        A form for selecting which students to kick from which sections,
        based on the students' first class times and the sections' start
        times.

        """
        if request.method == 'POST':
            selected_enrollments = request.POST['selected_enrollments']
            ids = [int(id) for id in selected_enrollments.split(',')]
            registrations = StudentRegistration.objects.filter(id__in=ids)
            registrations.update(end_date=datetime.datetime.now())
            logger.info("Expired student registrations: %s", ids)
            # send signal to expire caches
            # XXX: sending all of them is actually kind of
            # expensive and mostly redundant; it would be
            # preferable to have a way to say "just invalidate the
            # whole table".
            for reg in registrations:
                signals.post_save.send(
                    sender=StudentRegistration, instance=reg)
            context = {}
            context['ids'] = ids
            return render_to_response(
                self.baseDir()+'result.html', request, context)

        timeslots = prog.getTimeSlotList()
        now = datetime.datetime.now()
        hour = datetime.timedelta(minutes=60)
        selections = [{
            'slot': timeslot,
            'seq': seq,
            'passed': timeslot.start < now - hour,
            'upcoming': timeslot.start < now + hour,
        } for seq, timeslot in enumerate(timeslots)]
        context = {}
        context['selections'] = selections
        return render_to_response(
            self.baseDir()+'select.html', request, context)

    @aux_call
    @json_response(None)
    @needs_admin
    @cached_module_view
    def unenroll_status(prog):
        """
        Assemble the data necessary to compute the set of enrollments to
        expire for a given combination of student first class times
        and section start times.

        Returns:
        enrollments: { enrollment id -> (user id, section id) }
        student_timeslots: { user id -> event id of first class timeslot }
        section_timeslots: { section id -> event id of first timeslot }

        """
        enrolled = RegistrationType.objects.get(name='Enrolled')

        sections = prog.sections().filter(
            status__gt=0, parent_class__status__gt=0)
        sections = sections.exclude(
            parent_class__category__category='Lunch')

        enrollments = StudentRegistration.valid_objects().filter(
            relationship=enrolled, section__in=sections)

        # students not checked in
        students = ESPUser.objects.filter(
            id__in=enrollments.values('user'))
        students = students.exclude(
            record__program=prog, record__event='attended')

        # enrollments for those students
        relevant = enrollments.filter(user__in=students).values_list(
            'id', 'user', 'section', 'section__meeting_times')
        relevant = relevant.order_by('section__meeting_times__start')

        section_timeslots = {}  # section -> starting timeslot id
        student_timeslots = {}  # student -> starting timeslot id
        enrollments = {}        # id -> (student, section)
        for id, student, section, ts in relevant:
            if ts is None:
                continue

            if section not in section_timeslots:
                section_timeslots[section] = ts

            if student not in student_timeslots:
                student_timeslots[student] = ts

            enrollments[id] = (student, section)

        return {
            'section_timeslots': section_timeslots,
            'student_timeslots': student_timeslots,
            'enrollments': enrollments
        }
    cache = unenroll_status.method.cached_function
    cache.depend_on_row(StudentRegistration,
        lambda sr: {'prog': sr.section.parent_class.parent_program})
    cache.depend_on_row('users.Record',
        lambda record: {'prog': record.program},
        lambda record: record.event == 'attended')
    cache.depend_on_model('program.ClassSection')
    cache.depend_on_model('program.ClassSubject')
    cache.depend_on_model('cal.Event')
    cache.depend_on_m2m('program.ClassSection', 'meeting_times',
        lambda sec, event: {})
