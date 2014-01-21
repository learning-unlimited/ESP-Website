
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
  Email: web-team@lists.learningu.org
"""
from esp.program.modules.base    import ProgramModuleObj, needs_teacher, needs_admin, meets_deadline, main_call, aux_call
from esp.program.modules         import module_ext
from esp.program.models          import Program, ClassSection
from esp.program.controllers.classreg import ClassCreationController
from esp.middleware              import ESPError
from esp.datatree.models import *
from esp.web.util                import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django                      import forms
from esp.cal.models              import Event, EventType
from esp.tagdict.models          import Tag
from django.db.models.query      import Q
from esp.users.models            import User, ESPUser, UserAvailability
from esp.resources.models        import ResourceType, Resource
from django.conf import settings
from django.template.loader      import render_to_string
from esp.dbmail.models           import send_mail
from datetime                    import timedelta, datetime
from esp.middleware.threadlocalrequest import get_current_request
from esp.users.forms.generic_search_form import GenericSearchForm

class AvailabilityModule(ProgramModuleObj):
    """ This program module allows teachers to indicate their availability for the program. """

    @classmethod
    def module_properties(cls):
        return [ {
            "admin_title": "Teacher Availability",
            "link_title": "Indicate Your Availability",
            "module_type": "teach",
            "required": True,
            "seq": 0
            }, {
            "admin_title": "Teacher Availability Checker",
            "link_title": "Check Teacher Availability",
            "module_type": "manage",
            "seq": 0
            } ]
    
    def event_type(self):
        et, created = EventType.objects.get_or_create(description='Class Time Block')
        return et
    
    def prepare(self, context={}):
        """ prepare returns the context for the main availability page. 
            Everything else can be gotten from hooks in this module. """
        if context is None: context = {}
        
        context['availabilitymodule'] = self 
        return context

    def isCompleted(self):
        """ Make sure that they have indicated sufficient availability for all classes they have signed up to teach. """
        available_slots = get_current_request().user.getAvailableTimes(self.program, ignore_classes=True)
        
        #   Check number of timeslots against Tag-specified minimum
        if Tag.getTag('min_available_timeslots'):
            min_ts_count = int(Tag.getTag('min_available_timeslots'))
            if len(available_slots) < min_ts_count:
                return False
        
        # Round durations of both classes and timeslots to nearest 30 minutes
        total_time = get_current_request().user.getTaughtTime(self.program, include_scheduled=True, round_to=0.5)
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
            return {'availability': self.getQForUser(qf)}
        
        teacher_list = ESPUser.objects.filter(qf).distinct()
        
        return {'availability': teacher_list }#[t['user'] for t in teacher_list]}

    def teacherDesc(self):
        return {'availability': """Teachers who have indicated their scheduled availability for the program."""}

    def getTimes(self):
        #   Get a list of tuples with the id and name of each of the program's timeslots
        times = self.program.getTimeSlots(types=[self.event_type()])
        return [(str(t.id), t.short_description) for t in times]

    @main_call
    @needs_teacher
    @meets_deadline('/Availability')
    def availability(self, request, tl, one, two, module, extra, prog):
        #   Renders the teacher availability page and handles submissions of said page.
        
        if tl == "manage":
        	# They probably want to be check someone's availability instead-
        	return HttpResponseRedirect( '/manage/%s/%s/check_availability' % (one, two) )
        else:
            return self.availabilityForm(request, tl, one, two, prog, ESPUser(request.user), False)

    def availabilityForm(self, request, tl, one, two, prog, teacher, isAdmin):
        time_options = self.program.getTimeSlots(types=[self.event_type()])
        #   Group contiguous blocks
        if Tag.getTag('availability_group_timeslots', default=True) == 'False':
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
        user_sections = teacher.getTaughtSections(self.program)
        conflict_found = False
        for section in user_sections:
            for timeslot in section.get_meeting_times():
                taken_slots.append(timeslot)
                if timeslot not in available_slots:
                    conflict_found = True
                else:
                    avail_and_teaching.append(timeslot)

        if request.method == 'POST':
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
            
            blank = (not (bool(len(timeslot_ids))))
            if not blank:
                for timeslot in timeslots:
                    teacher.addAvailableTime(self.program, timeslot)
                
                #   Send an e-mail showing availability to the teacher (and the archive)
                ccc = ClassCreationController(self.program)
                ccc.send_availability_email(teacher)
                
                if isAdmin:
                    #   Return to the relevant check_availability page
                    return HttpResponseRedirect( '/manage/%s/%s/check_availability?user=%s' % (one, two, teacher.id) )
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

        context = {'groups': [{'selections': [{'checked': (t in available_slots), 'taken': (t in taken_slots), 'slot': t} for t in group]} for group in time_groups]}
        context['num_groups'] = len(context['groups'])
        context['prog'] = self.program
        context['is_overbooked'] = (not self.isCompleted() and (teacher.getTaughtTime(self.program) > timedelta(0)))
        context['submitted_blank'] = blank
        context['conflict_found'] = conflict_found
        context['teacher_user'] = teacher
        
        return render_to_response(self.baseDir()+'availability_form.html', request, context)

    @aux_call
    @needs_admin
    def check_availability(self, request, tl, one, two, module, extra, prog):
        """
        Check availability of the specified user.
        """
        
        teacher = None
        form = None
        
        if request.method == 'POST':
            form = GenericSearchForm(request.POST)
            if form.is_valid():
                teacher = form.cleaned_data['target_user']
        
        if teacher is None:
            if request.GET.has_key('user'):
                target_id = request.GET['user']
            elif request.POST.has_key('user'):
                target_id = request.POST['user']
            else:
                form = GenericSearchForm()
                context = {'form': form}
                return render_to_response(self.baseDir()+'check_availability.html', request, context)

            form = GenericSearchForm(initial={'target_user': target_id})

            try:
                teacher = ESPUser.objects.get(id=target_id)
            except:
                try:
                    teacher = ESPUser.objects.get(username=target_id)
                except:
                    raise ESPError("The user with id/username=" + str(target_id) + " does not appear to exist!", log=False)
        
        if teacher is None:
            form = GenericSearchForm()
            context = {'form': form}
            return render_to_response(self.baseDir()+'check_availability.html', request, context)

        timeslots = self.program.getTimeSlotList()

        # Get the times that the teacher is marked as available
        marked_available = set(teacher.getAvailableTimes(self.program, True))

        # Now get times that teacher is teaching
        # Also keep track of what class it is
        teaching_sections = teacher.getTaughtSections(self.program)
        teaching_times = {}
        unscheduled_classes = []
        for s in teaching_sections:
            sec_times = s.get_meeting_times()
            if len(sec_times) == 0:
                unscheduled_classes.append((s.parent_class.id, s.emailcode(), s.parent_class.title, s.prettyDuration()))
            for t in sec_times:
                rooms = ""
                for r in s.prettyrooms():
                    rooms = rooms + r
                    if r != s.prettyrooms()[-1]:
                        rooms = rooms + ", "
                teaching_times[t]=(s.parent_class.id, s.emailcode(), s.parent_class.title, rooms)


        # Check the availability and teaching status of each timeslot, and mark in tuple accordingly as (start time, end time, available, teaching)
        available = []
        
        for t in timeslots:
            if t in teaching_times:
                if t in marked_available:
                    available.append((t.start, t.end, True, True, teaching_times.get(t)[0], \
                                          teaching_times.get(t)[1], teaching_times.get(t)[2], \
                                          teaching_times.get(t)[3]))
                else:
                    available.append((t.start, t.end, False, True, teaching_times.get(t)[0], \
                                          teaching_times.get(t)[1], teaching_times.get(t)[2], \
                                          teaching_times.get(t)[3]))
            else:
                if t in marked_available:
                    available.append((t.start, t.end, True, False, None, None, None, None))
                else:
                    available.append((t.start, t.end, False, False, None, None, None, None))

        context = {'available': available, 'unscheduled': unscheduled_classes, 'teacher_name': teacher.first_name + ' ' + teacher.last_name, 'teaching_times': teaching_times, 'edit_path': '/manage/%s/%s/edit_availability?user=%s' % (one, two, teacher.username), 'form': form }
        return render_to_response(self.baseDir()+'check_availability.html', request, context)

    @aux_call
    @needs_admin
    def edit_availability(self, request, tl, one, two, module, extra, prog):
        """
        Admins edits availability of the specified user.
        """
        
        target_id = None
        
        if request.GET.has_key('user'):
            target_id = request.GET['user']
        elif request.POST.has_key('user'):
            target_id = request.POST['user']
        else:
            context = {}
            return render_to_response(self.baseDir()+'check_availability.html', request, context)
        
        try:
            teacher = ESPUser.objects.get(id=target_id)
        except:
        	try:
        		teacher = ESPUser.objects.get(username=target_id)
        	except:
        		raise ESPError("The user with id/username=" + str(target_id) + " does not appear to exist!", log=False)

        return self.availabilityForm(request, tl, one, two, prog, teacher, True)

    class Meta:
        proxy = True
