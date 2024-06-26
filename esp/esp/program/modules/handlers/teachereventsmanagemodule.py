
from __future__ import absolute_import
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 by the individual contributors
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
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.utils.web import render_to_response
from esp.cal.models import Event, EventType
from esp.users.models import UserAvailability
from esp.program.modules.forms.teacherevents import TimeslotForm
from django.contrib.auth.models import Group

class TeacherEventsManageModule(ProgramModuleObj):
    doc = """Set up events (e.g. interviews, training) for teachers to sign up for. """

    # Initialization
    def __init__(self, *args, **kwargs):
        super(TeacherEventsManageModule, self).__init__(*args, **kwargs)

    def availability_role(self):
        return Group.objects.get(name='Teacher')

    # General Info functions
    @classmethod
    def module_properties(cls):
        return {
            "module_type": "manage",
            'required': False,
            'admin_title': 'Manage Teacher Training and Interviews',
            'link_title': 'Teacher Training and Interviews',
            'seq': 5,
            'choosable': 0,
        }

    @main_call
    @needs_admin
    def teacher_events(self, request, tl, one, two, module, extra, prog):
        context = {}

        if request.method == 'POST':
            data = request.POST

            if data['command'] == 'delete':
                #   delete timeslot
                ts = Event.objects.get(id=data['id'])
                ts.delete()

            elif data['command'] == 'load':
                #   load timeslot for editing
                ts = Event.objects.get(id=data['id'])
                form = TimeslotForm()
                form.load_timeslot(ts)
                context['timeslot_form'] = form
                context['editing_timeslot'] = ts

            elif data['command'] == 'edit':
                #   edit timeslot
                ts = Event.objects.get(id=data['id'])
                form = TimeslotForm(data)
                if form.is_valid():
                    form.save_timeslot(self.program, ts, ts.event_type)
                else:
                    context['timeslot_form'] = form

            elif data['command'] == 'add':
                #   add timeslot
                form = TimeslotForm(data)
                if form.is_valid():
                    new_timeslot = Event()

                    # decide type
                    type = "training"

                    if data.get('submit') == "Add Interview":
                        type = "interview"

                    form.save_timeslot(self.program, new_timeslot, type)
                else:
                    context['timeslot_form'] = form

        if 'timeslot_form' not in context:
            context['timeslot_form'] = TimeslotForm()

        interview_times = self.program.get_teacher_event_times('interview')
        training_times = self.program.get_teacher_event_times('training')

        for ts in list( interview_times ) + list( training_times ):
            ts.teachers = UserAvailability.entriesBySlot( ts )

        context['prog'] = prog
        context['interview_times'] = interview_times
        context['training_times'] = training_times

        return render_to_response( self.baseDir()+'teacher_events.html', request, context )

    def isStep(self):
        return True

    setup_title = "Set up events for teachers to attend before the program"

    def isCompleted(self):
        return Event.objects.filter(program=self.program, event_type__in=list(EventType.teacher_event_types().values())).exists()

    class Meta:
        proxy = True
        app_label = 'modules'
