
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

import json
from datetime import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.query import Q
from django.http import HttpResponse

from argcache import cache_function_for

from esp.program.modules.base import ProgramModuleObj, needs_onsite, main_call, aux_call
from esp.program.models import ClassSubject, ClassSection, StudentRegistration
from esp.program.models.class_ import OPEN, CLOSED
from esp.program.class_status import ClassStatus
from esp.users.models import ESPUser, Record
from esp.utils.web import render_to_response
from esp.utils.query_utils import nest_Q
from esp.cal.models import Event


class OnSiteAdminWebApp(ProgramModuleObj):
    doc = """Mobile-friendly admin dashboard for onsite event management.
    Provides live monitoring of class enrollments and check-ins,
    per-class registration toggles, and overenrollment controls."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Admin Onsite Webapp",
            "link_title": "Onsite Admin Dashboard",
            "module_type": "onsite",
            "seq": 5,
            "choosable": 1,
        }

    @main_call
    @needs_onsite
    def onsiteadmin(self, request, tl, one, two, module, extra, prog):
        """Main admin onsite dashboard view."""
        timeslots = prog.getTimeSlots().order_by('start')
        context = {
            'program': prog,
            'timeslots': timeslots,
            'one': one,
            'two': two,
        }
        return render_to_response(self.baseDir() + 'dashboard.html', request, context)

    @aux_call
    @needs_onsite
    def onsiteadmin_sections_api(self, request, tl, one, two, module, extra, prog):
        """JSON API: returns all sections with enrollment/attendance data."""
        timeslot_id = request.GET.get('timeslot', None)

        sections_qs = ClassSection.objects.filter(
            parent_class__parent_program=prog,
            parent_class__status=ClassStatus.ACCEPTED,
            status__gt=0,
        ).select_related('parent_class', 'parent_class__category')

        if timeslot_id:
            sections_qs = sections_qs.filter(meeting_times__id=timeslot_id).distinct()

        sections_data = []
        for sec in sections_qs:
            enrolled = sec.num_students()
            attending = sec.count_attending_students()
            capacity = sec.capacity
            teachers = ', '.join([t.name() for t in sec.parent_class.get_teachers()])
            rooms = ', '.join(sec.prettyrooms()) if sec.prettyrooms() else 'TBD'
            times = sec.friendly_times()

            sections_data.append({
                'id': sec.id,
                'emailcode': sec.emailcode(),
                'title': sec.title(),
                'category': sec.parent_class.category.category if sec.parent_class.category else '',
                'category_symbol': sec.parent_class.category.symbol if sec.parent_class.category else '',
                'teachers': teachers,
                'rooms': rooms,
                'times': times,
                'enrolled': enrolled,
                'attending': attending,
                'capacity': capacity if capacity else 0,
                'is_full': sec.isFull(),
                'registration_status': sec.registration_status,
                'is_reg_open': sec.isRegOpen(),
            })

        # Program-level stats
        total_enrolled = sum(s['enrolled'] for s in sections_data)
        total_capacity = sum(s['capacity'] for s in sections_data)
        total_attending = sum(s['attending'] for s in sections_data)
        checked_in = Record.objects.filter(
            program=prog, event__name='attended'
        ).values('user').distinct().count()

        data = {
            'sections': sections_data,
            'stats': {
                'total_enrolled': total_enrolled,
                'total_capacity': total_capacity,
                'total_attending': total_attending,
                'checked_in_students': checked_in,
                'num_sections': len(sections_data),
            },
            'timestamp': datetime.now().isoformat(),
        }

        return HttpResponse(
            json.dumps(data, cls=DjangoJSONEncoder),
            content_type='application/json'
        )

    @aux_call
    @needs_onsite
    def onsiteadmin_toggle_registration(self, request, tl, one, two, module, extra, prog):
        """Toggle registration open/closed for a section."""
        if request.method != 'POST':
            return HttpResponse(
                json.dumps({'success': False, 'message': 'POST required'}),
                content_type='application/json',
                status=405,
            )

        section_id = request.POST.get('section_id')
        action = request.POST.get('action')  # 'open' or 'close'

        try:
            section = ClassSection.objects.get(
                id=section_id,
                parent_class__parent_program=prog,
            )
        except ClassSection.DoesNotExist:
            return HttpResponse(
                json.dumps({'success': False, 'message': 'Section not found'}),
                content_type='application/json',
                status=404,
            )

        if action == 'open':
            section.registration_status = OPEN
        elif action == 'close':
            section.registration_status = CLOSED
        else:
            return HttpResponse(
                json.dumps({'success': False, 'message': 'Invalid action. Use "open" or "close".'}),
                content_type='application/json',
                status=400,
            )

        section.save()

        return HttpResponse(
            json.dumps({
                'success': True,
                'section_id': section.id,
                'registration_status': section.registration_status,
                'is_reg_open': section.isRegOpen(),
                'message': 'Registration %s for %s' % (
                    'opened' if action == 'open' else 'closed',
                    section.emailcode(),
                ),
            }),
            content_type='application/json'
        )

    @aux_call
    @needs_onsite
    def onsiteadmin_section_detail(self, request, tl, one, two, module, extra, prog):
        """Mini class management page for a single section."""
        section_id = extra
        try:
            section = ClassSection.objects.get(
                id=section_id,
                parent_class__parent_program=prog,
            )
        except ClassSection.DoesNotExist:
            from django.http import Http404
            raise Http404

        enrolled_regs = StudentRegistration.valid_objects().filter(
            section=section,
            relationship__name='Enrolled',
        ).select_related('user')
        enrolled_students = [reg.user for reg in enrolled_regs]

        attending_regs = StudentRegistration.valid_objects().filter(
            section=section,
            relationship__name='Attended',
        ).select_related('user')
        attending_students = [reg.user for reg in attending_regs]

        attending_ids = set(s.id for s in attending_students)

        context = {
            'program': prog,
            'section': section,
            'cls': section.parent_class,
            'enrolled_students': enrolled_students,
            'attending_students': attending_students,
            'attending_ids': attending_ids,
            'enrolled_count': len(enrolled_students),
            'attending_count': len(attending_students),
            'capacity': section.capacity or 0,
            'teachers': section.parent_class.get_teachers(),
            'rooms': section.prettyrooms(),
            'times': section.friendly_times(),
            'one': one,
            'two': two,
        }
        return render_to_response(self.baseDir() + 'section_detail.html', request, context)

    @aux_call
    @needs_onsite
    def onsiteadmin_set_capacity(self, request, tl, one, two, module, extra, prog):
        """Update the max capacity (overenrollment) for a section."""
        if request.method != 'POST':
            return HttpResponse(
                json.dumps({'success': False, 'message': 'POST required'}),
                content_type='application/json',
                status=405,
            )

        section_id = request.POST.get('section_id')
        try:
            new_capacity = int(request.POST.get('capacity', 0))
        except (ValueError, TypeError):
            return HttpResponse(
                json.dumps({'success': False, 'message': 'Invalid capacity value'}),
                content_type='application/json',
                status=400,
            )

        try:
            section = ClassSection.objects.get(
                id=section_id,
                parent_class__parent_program=prog,
            )
        except ClassSection.DoesNotExist:
            return HttpResponse(
                json.dumps({'success': False, 'message': 'Section not found'}),
                content_type='application/json',
                status=404,
            )

        section.max_class_capacity = new_capacity
        section.save()

        return HttpResponse(
            json.dumps({
                'success': True,
                'section_id': section.id,
                'capacity': new_capacity,
                'message': 'Capacity updated to %d for %s' % (new_capacity, section.emailcode()),
            }),
            content_type='application/json'
        )

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
