
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

from esp.program.modules.base import ProgramModuleObj, needs_onsite, main_call
from esp.program.models import StudentRegistration
from esp.utils.web import render_to_response
from esp.users.models import ESPUser
from esp.cal.models import Event
from esp.utils.query_utils import nest_Q

class OnSiteAttendance(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "On-Site Student Attendance",
            "link_title": "Check Student Attendance",
            "module_type": "onsite",
            "seq": 1
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
                attended = ESPUser.objects.filter(Q(studentregistration__section__meeting_times=timeslot, studentregistration__relationship__name="Attended") & nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration'))
                enrolled = ESPUser.objects.filter(Q(studentregistration__section__meeting_times=timeslot, studentregistration__relationship__name="Enrolled") & nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration'))
                checked_in = ESPUser.objects.filter(Q(record__event='attended', record__program=prog))
                checked_in_during_ts = ESPUser.objects.filter(Q(record__event='attended', record__program=prog, record__time__gt=timeslot.start, record__time__lt=timeslot.end))
                not_attending = checked_in.exclude(id__in=[user.id for user in attended])
                onsite = ESPUser.objects.filter(Q(studentregistration__section__meeting_times=timeslot, studentregistration__relationship__name="OnSite/AttendedClass") & nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration'))
                context.update({
                                'attended': attended,
                                'checked_in': checked_in,
                                'onsite': onsite,
                                'enrolled': enrolled,
                                'checked_in_ts': checked_in_during_ts,
                                'not_attending': not_attending
                               })

        return render_to_response(self.baseDir()+'attendance.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
