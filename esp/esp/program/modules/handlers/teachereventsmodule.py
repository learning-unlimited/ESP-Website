
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, meets_deadline, main_call, aux_call, no_auth
from esp.program.modules.forms.teacherreg import TeacherEventSignupForm
from esp.utils.web import render_to_response
from django.db.models.query import Q
from esp.dbmail.models import send_mail
from esp.cal.models import Event, EventType
from esp.users.models import ESPUser, UserAvailability
from esp.middleware.threadlocalrequest import get_current_request
from django.contrib.auth.models import Group
from django.conf import settings
from django.utils import timezone

class TeacherEventsModule(ProgramModuleObj):
    doc = """Allows teachers to sign up for one or more teacher events (e.g. interviews, training)."""

    # Initialization
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @aux_call
    @no_auth
    def calendar_data(self, request, tl, one, two, module, extra, prog):
        """ Provide AJAX-compatible JSON for the calendar view. """
        from django.http import JsonResponse

        user = request.user

        # Explicit auth check: return JSON errors instead of HTML redirects
        if not user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        if not user.isTeacher() and not user.isAdmin(prog):
            return JsonResponse({'error': 'Teacher access required'}, status=403)

        data = []

        # Get exact teacher event type objects to avoid fragile string matching
        teacher_types = EventType.teacher_event_types()
        interview_type = teacher_types.get('interview')
        training_type = teacher_types.get('training')

        # Collect teacher events for this program (including past events)
        all_events = Event.objects.filter(
            program=prog,
            event_type__in=[t for t in (interview_type, training_type) if t is not None]
        ).order_by('start')

        now = timezone.now()
        for event in all_events:
            entries = UserAvailability.entriesBySlot(event)
            is_mine = entries.filter(user=user).exists()

            # Determine category and full status heavily relying on actual EventType objects
            if interview_type and event.event_type.id == interview_type.id:
                category = 'interview'
                # Interview slots are single-occupancy
                other_entries = entries.exclude(user=user)
                is_full = other_entries.exists()
            else:
                category = 'training'
                # Training slots allow multiple signups
                is_full = False
            is_past = event.start < now

            if is_mine:
                status = 'mine'
                color = '#28a745'  # Green
            elif is_full:
                status = 'full'
                color = '#dc3545'  # Red
            elif is_past:
                status = 'past'
                color = '#6c757d'  # Gray
            else:
                status = 'available'
                color = '#3788d8'  # Blue

            data.append({
                'id': event.id,
                'title': '%s: %s' % (category.capitalize(), event.name),
                'start': event.start.isoformat(),
                'end': event.end.isoformat(),
                'color': color,
                'extendedProps': {
                    'category': category,
                    'status': status,
                    'description': event.description,
                    'event_type_id': event.event_type.id
                }
            })

        return JsonResponse(data, safe=False)

    def availability_role(self):
        return Group.objects.get(name='Teacher')

    # General Info functions
    @classmethod
    def module_properties(cls):
        return {
            "module_type": "teach",
            'required': False,
            'admin_title': 'Teacher Training and Interview Signups',
            'link_title': 'Sign up for Teacher Training and Interviews',
            'seq': 5,
            'choosable': 0,
        }

    def teachers(self, QObject = False):
        """ Returns lists of teachers who've signed up for interviews and for teacher training. """
        q_objs = {
            obj.description: Q(useravailability__event__event_type=obj,
                    useravailability__event__program=self.program)
            for obj in EventType.objects.filter(is_teacher_type=True)
        }
        if QObject:
            return q_objs
        else:
            return {
                name: ESPUser.objects.filter(q_obj).distinct()
                for name, q_obj in q_objs.items()
            }

    def teacherDesc(self):
        return {
            obj.description: "Teachers who have signed up for %s" % obj.description.lower()
            for obj in EventType.objects.filter(is_teacher_type=True)
        }

    # Helper functions
    def getTimes(self, event_type):
        """ Get events of the program's teacher interview/training slots. """
        return Event.objects.filter( program=self.program, event_type=event_type ).order_by('start')

    def entriesByTeacher(self, user):
        return {
            obj.description: UserAvailability.objects.filter(user=user, event__event_type=obj, event__program=self.program)
            for obj in EventType.objects.filter(is_teacher_type=True)
        }

    # Per-user info
    def isCompleted(self, user=None):
        """
        Return true if user has signed up for everything possible.
        If there are teacher training timeslots, requires signing up for them.
        If there are teacher interview timeslots, requires those too.
        """
        user = self._resolve_user(user)
        entries = self.entriesByTeacher(user)
        for obj in EventType.objects.filter(is_teacher_type=True):
            if self.getTimes(obj).exists() and not entries[obj.description].exists():
                return False
        return True

    # Views
    @main_call
    @needs_teacher
    @meets_deadline('/Events')
    def event_signup(self, request, tl, one, two, module, extra, prog):
        if request.method == 'POST':
            form = TeacherEventSignupForm(self, request.POST)
            if form.is_valid():
                data = form.cleaned_data
                # Remove old bits
                event_types = EventType.objects.filter(is_teacher_type=True)
                UserAvailability.objects.filter(user=request.user, event__event_type__in=event_types).delete()
                for event_type in event_types:
                    field_name = 'event_type_%d' % event_type.id
                    event = data.get(field_name)
                    if event:
                        ua, created = UserAvailability.objects.get_or_create( user=request.user, event=event, role=self.availability_role())
                        # Send the directors an email
                        if self.program.director_email and created and 'interview' in event_type.description.lower():
                            event_name = event.description
                            send_mail('['+self.program.niceName()+'] Teacher Interview for ' + request.user.first_name + ' ' + request.user.last_name + ': ' + event_name, \
                                  """Teacher Interview Registration Notification\n--------------------------------- \n\nTeacher: %s %s\n\nTime: %s\n\n""" % \
                                  (request.user.first_name, request.user.last_name, event_name), \
                                  '%s Registration System <server@%s>' % (self.program.program_type, settings.EMAIL_HOST_SENDER), \
                                  [self.program.getDirectorCCEmail()], True, extra_headers = {'Reply-To': request.user.get_email_sendto_address()})
                return self.goToCore(tl)
        else:
            data = {}
            entries = self.entriesByTeacher(request.user)
            for event_type in EventType.objects.filter(is_teacher_type=True):
                desc = event_type.description
                if entries[desc].count() > 0:
                    data['event_type_%d' % event_type.id] = entries[desc][0].event.id
            form = TeacherEventSignupForm(self, initial=data)
        return render_to_response( self.baseDir()+'event_signup.html', request, {'prog':prog, 'form': form} )

    def isStep(self):
        return Event.objects.filter(program=self.program, event_type__is_teacher_type=True).exists()

    class Meta:
        proxy = True
        app_label = 'modules'
