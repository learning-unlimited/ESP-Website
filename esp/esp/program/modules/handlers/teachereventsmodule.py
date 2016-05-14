
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, meets_deadline, main_call
from esp.program.modules.forms.teacherreg import TeacherEventSignupForm
from esp.utils.web import render_to_response
from esp.dbmail.models import send_mail
from django.db.models.query import Q
from esp.cal.models import EventType
from esp.users.models import ESPUser, UserAvailability
from esp.middleware.threadlocalrequest import get_current_request
from django.contrib.auth.models import Group


class TeacherEventsModule(ProgramModuleObj):
    def availability_role(self):
        return Group.objects.get(name='Teacher')

    # General Info functions
    @classmethod
    def module_properties(cls):
        return [{
            "module_type": "teach",
            'required': False,
            'admin_title': 'Teacher Training and Interview Signups',
            'link_title': 'Sign up for Teacher Training and Interviews',
            'seq': 5,
        }]

    def teachers(self, QObject=False):
        """ Returns lists of teachers who've signed up for interviews and for teacher training. """

        q_objs = {
            name: Q(useravailability__event__event_type=obj,
                    useravailability__event__program=self.program)
            for name, obj in EventType.teacher_event_types()
        }
        if QObject:
            return q_objs
        else:
            return {
                name: ESPUser.objects.filter(q_obj).distinct()
                for name, q_obj in q_objs
            }

    def teacherDesc(self):
        return {
            'interview': """Teachers who have signed up for an interview.""",
            'training':  """Teachers who have signed up for teacher training.""",
        }

    # Helper functions
    def entriesByTeacher(self, user):
        return {
            name: UserAvailability.objects.filter(
                event__event_type=obj, user=user, event__program=self.program)
            for name, obj in EventType.teacher_event_types()
        }

    # Per-user info
    def isCompleted(self):
        """
        Return true iff user has signed up for everything possible.
        If there are teacher training timeslots, requires signing up for them.
        If there are teacher interview timeslots, requires those too.
        """
        entries = self.entriesByTeacher(get_current_request().user)
        return (self.program.get_teacher_event_times('interview').count() == 0 or entries['interview'].count() > 0) and (self.program.get_teacher_event_times('training').count() == 0 or entries['training'].count() > 0)

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
                event_types = EventType.teacher_event_types().values()
                UserAvailability.objects.filter(user=request.user, event__event_type__in=event_types).delete()
                # Register for interview
                if data['interview']:
                    ua, created = UserAvailability.objects.get_or_create( user=request.user, event=data['interview'], role=self.availability_role())
                    # Send the directors an e-mail
                    if self.program.director_email and created:
                        event_name = data['interview'].description
                        send_mail('['+self.program.niceName()+'] Teacher Interview for ' + request.user.first_name + ' ' + request.user.last_name + ': ' + event_name, \
                              """Teacher Interview Registration Notification\n--------------------------------- \n\nTeacher: %s %s\n\nTime: %s\n\n""" % \
                              (request.user.first_name, request.user.last_name, event_name) , \
                              ('%s <%s>' % (request.user.first_name + ' ' + request.user.last_name, request.user.email,)), \
                              [self.program.getDirectorCCEmail()], True)

                # Register for training
                if data['training']:
                    ua, created = UserAvailability.objects.get_or_create( user=request.user, event=data['training'], role=self.availability_role())
                return self.goToCore(tl)
        else:
            data = {}
            entries = self.entriesByTeacher(request.user)
            if entries['interview'].count() > 0:
                data['interview'] = entries['interview'][0].event.id
            if entries['training'].count() > 0:
                data['training'] = entries['training'][0].event.id
            form = TeacherEventSignupForm(self, initial=data)
        return render_to_response( self.baseDir()+'event_signup.html', request, {'prog':prog, 'form': form} )

    class Meta:
        proxy = True
        app_label = 'modules'
