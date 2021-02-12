
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
from esp.program.modules.base    import ProgramModuleObj, needs_teacher, meets_deadline, main_call
from esp.program.controllers.classreg import ClassCreationController
from esp.middleware              import ESPError
from esp.utils.web               import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django                      import forms
from esp.cal.models              import Event, EventType
from esp.tagdict.models          import Tag
from django.db.models.query      import Q
from esp.users.models            import ESPUser, UserAvailability
from datetime                    import timedelta
from esp.middleware.threadlocalrequest import get_current_request
from esp.users.forms.generic_search_form import TeacherSearchForm


class AvailabilityModule(ProgramModuleObj):
    """ This program module allows teachers to indicate their availability for the program. """

    @classmethod
    def module_properties(cls):
        return [ {
            "admin_title": "Teacher Availability",
            "link_title": "Indicate Your Availability",
            "module_type": "teach",
            "required": True,
            "seq": 0,
            "choosable": 1,
            } ]

    def event_type(self):
        et = EventType.get_from_desc('Class Time Block')
        return et

    def prepare(self, context={}):
        """ prepare returns the context for the main availability page.
            Everything else can be gotten from hooks in this module. """
        if context is None: context = {}

        context['availabilitymodule'] = self
        return context

    def isCompleted(self, user = None):
        """ Make sure that they have indicated sufficient availability for all classes they have signed up to teach. """
        if user is None:
            user = get_current_request().user
        available_slots = user.getAvailableTimes(self.program, ignore_classes=True)

        #   Check number of timeslots against Tag-specified minimum
        if Tag.getTag('min_available_timeslots'):
            min_ts_count = int(Tag.getTag('min_available_timeslots'))
            if len(available_slots) < min_ts_count:
                return False

        # Round durations of both classes and timeslots to nearest 30 minutes
        total_time = user.getTaughtTime(self.program, include_scheduled=True, round_to=0.5)
        available_time = timedelta()
        for a in available_slots:
            available_time = available_time + timedelta( seconds = 1800 * round( a.duration().seconds / 1800.0 ) )

        if (total_time > available_time) or (available_time == timedelta()):
            return False
        else:
            return True

    def teachers(self, QObject = False):
        """ Returns a list of teachers who have indicated at least one segment of teaching availability for this program. """

        qf = Q(useravailability__event__program=self.program, useravailability__role__name='Teacher')
        if QObject is True:
            return {'availability': qf}

        teacher_list = ESPUser.objects.filter(qf).distinct()

        return {'availability': teacher_list }#[t['user'] for t in teacher_list]}

    def teacherDesc(self):
        return {'availability': """Teachers who have indicated their scheduled availability for the program"""}

    @main_call
    @needs_teacher
    @meets_deadline('/Availability')
    def availability(self, request, tl, one, two, module, extra, prog):
        #   Renders the teacher availability page and handles submissions of said page.

        if tl == "manage":
            # They probably want to be check or edit someone's availability instead
            return HttpResponseRedirect( '/manage/%s/%s/edit_availability' % (one, two) )
        else:
            return self.availabilityForm(request, tl, one, two, prog, request.user, False)

    def availabilityForm(self, request, tl, one, two, prog, teacher, isAdmin=False):
        time_options = self.program.getTimeSlots(types=[self.event_type()])
        #   Group contiguous blocks
        if not Tag.getBooleanTag('availability_group_timeslots'):
            time_groups = [list(time_options)]
        else:
            time_groups = Event.group_contiguous(list(time_options))

        blank = False

        available_slots = teacher.getAvailableTimes(self.program, True)
        # must set the ignore_classes=True parameter above, otherwise when a teacher tries to edit their
        # availability, it will show their scheduled times as unavailable.

        #   Fetch the timeslots the teacher is scheduled in and grey them out.
        #   If we found a timeslot that they are scheduled in but is not available, show a warning.
        taken_slots = []
        avail_and_teaching = []
        unscheduled_classes = []
        user_sections = teacher.getTaughtSections(self.program)
        teaching_times = {}
        conflict_found = False
        for section in user_sections:
            sec_times = section.get_meeting_times()
            if len(sec_times) == 0:
                unscheduled_classes.append(section)
            for timeslot in sec_times:
                taken_slots.append(timeslot)
                if timeslot not in available_slots:
                    conflict_found = True
                else:
                    avail_and_teaching.append(timeslot)
                teaching_times[timeslot]=section

        if request.method == 'POST' and 'search' not in request.POST:
            #   Process form
            post_vars = request.POST

            #   Reset teacher's availability
            teacher.clearAvailableTimes(self.program)
            #   But add back in the times they're teaching
            #   because those aren't submitted with the form
            for timeslot in avail_and_teaching:
                teacher.addAvailableTime(self.program, timeslot)

            #   Add in resources for the checked available times.
            timeslot_ids = map(int, post_vars.getlist('timeslots'))
            timeslots = Event.objects.filter(id__in=timeslot_ids).order_by('start')
            missing_tsids = set(timeslot_ids) - set(x.id for x in timeslots)
            if missing_tsids:
                raise ESPError('Received requests for the following timeslots that don\'t exist: %s' % str(list(sorted(missing_tsids))), log=False)

            blank = (not (bool(len(timeslot_ids) + len(avail_and_teaching))))
            if not blank:
                for timeslot in timeslots:
                    teacher.addAvailableTime(self.program, timeslot)

                #   Send an email showing availability to the teacher (and the archive)
                ccc = ClassCreationController(self.program)
                ccc.send_availability_email(teacher)

                if isAdmin:
                    #   Return to the relevant edit_availability page
                    return HttpResponseRedirect( '/manage/%s/%s/edit_availability?user=%s' % (one, two, teacher.id) )
                else:
                    #   Return to the main registration page
                    return self.goToCore(tl)

        #   Show new form

        if not (len(available_slots) or blank): # I'm not sure whether or not we want the "or blank"
            #   If they didn't enter anything, make everything checked by default.
            available_slots = self.program.getTimeSlots(types=[self.event_type()])
            #   The following 2 lines mark the teacher as always available.  This
            #   is sometimes helpful, but not usually the desired behavior.
            #   for a in available_slots:
            #       teacher.addAvailableTime(self.program, a)

        context =   {
                        'groups': [
                            [
                                {
                                    'checked': t in available_slots,
                                    'taken': t in taken_slots,
                                    'slot': t,
                                    'id': t.id,
                                    'section': teaching_times.get(t),
                                }
                            for t in group]
                        for group in time_groups]
                    }
        context['unscheduled'] = unscheduled_classes
        context['num_groups'] = len(context['groups'])
        context['prog'] = self.program
        context['is_overbooked'] = (not self.isCompleted(user = teacher) and (teacher.getTaughtTime(self.program) > timedelta(0)))
        context['submitted_blank'] = blank
        context['conflict_found'] = conflict_found
        context['teacher_user'] = teacher
        context['isAdmin'] = isAdmin

        if isAdmin:
            form = TeacherSearchForm(initial={'target_user': teacher.id})
            context['search_form'] = form

        return render_to_response(self.baseDir()+'availability_form.html', request, context)

    def isStep(self):
        return self.program.getTimeSlots(types=[self.event_type()]).exists()

    class Meta:
        proxy = True
        app_label = 'modules'

