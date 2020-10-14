
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
from esp.program.modules.base    import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.modules         import module_ext
from esp.program.models          import Program, ClassSubject, ClassSection, ClassCategories, ClassSizeRange
from esp.utils.web               import render_to_response
from django                      import forms
from django.http                 import HttpResponseRedirect, HttpResponse
from django.template.loader      import render_to_string
from esp.cal.models              import Event
from esp.users.models            import User, ESPUser, UserAvailability
from esp.middleware              import ESPError
from esp.resources.models        import Resource, ResourceRequest, ResourceType, ResourceAssignment
from datetime                    import timedelta, time
import json
from collections                 import defaultdict
from argcache                    import cache_function
from uuid                        import uuid4 as get_uuid
from esp.utils.decorators         import json_response
import calendar, time, datetime

class AJAXSchedulingModule(ProgramModuleObj):
    """ This program module allows teachers to indicate their availability for the program. """

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "AJAX Scheduling",
            "module_type": "manage",
            "seq": 7,
            "choosable": 1,
            }
    def prepare(self, context={}):
        if context is None: context = {}

        context['schedulingmodule'] = self
        return context

    @main_call
    @needs_admin
    def ajax_scheduling(self, request, tl, one, two, module, extra, prog):
        """
        Serve the scheduling page.

        This is just a static page;
        it gets all of its content from AJAX callbacks.
        """

        #trim the log here.
        #Nothing special about right here, but putting it here makes sure it's done regularly, without
        #doing it really really often, and without having an extra thread just for that.

        self.get_change_log(prog).prune()

        #actually return the page
        context = {
            "has_autoscheduler_frontend":
                prog.hasModule("AutoschedulerFrontendModule")}

        return render_to_response(self.baseDir()+'ajax_scheduling.html', request, context)

    @aux_call
    @needs_admin
    def ajax_schedule_assignments_csv(self, request, tl, one, two, module, extra, prog):
        lst = []
        for s in prog.sections():
            if s.resourceassignment_set.all().count() > 0:
                ra = s.resourceassignment_set.all().order_by('resource__event__id')[0]
                lst.append((s.id, ra.resource.name, ra.resource.event.id))

        return HttpResponse('\n'.join([','.join(['"%s"' % v for v in x]) for x in lst]), content_type='text/csv')

    #helper functions for ajax_schedule_class
    #seperated out here to make code more readeable and enable testing
    def makeret(self, prog, **kwargs):
        last_changed = self.ajax_schedule_last_changed_helper(prog).raw_value
        kwargs['val'] = last_changed['val']
        response = HttpResponse(content_type="application/json")
        json.dump(kwargs, response)
        return response

    def ajax_schedule_deletereg(self, prog, cls, user=None):
        cls.clearRooms()
        cls.clear_meeting_times()
        self.get_change_log(prog).appendScheduling([], "", int(cls.id), user)

        return self.makeret(prog, ret=True, msg="Schedule removed for Class Section '%s'" % cls.emailcode())

    def ajax_schedule_assignreg(self, prog, cls, timeslot_ids, classroom_ids, user=None, override=False):
        if len(timeslot_ids) < 1:
            return self.makeret(prog, ret=False, msg="No times specified!, can't assign to a timeblock")

        if len(classroom_ids) < 1:
            return self.makeret(prog, ret=False, msg="No classrooms specified!, can't assign to a timeblock")

        basic_cls = classroom_ids[0]
        for c in classroom_ids:
            if c != basic_cls:
                return self.makeret(prog, ret=False, msg="Assigning one section to multiple rooms.  This interface doesn't support this feature currently; assign it to one room for now and poke a Webmin to do this for you manually.")

        times = Event.objects.filter(id__in=timeslot_ids).order_by('start')
        if len(times) < 1:
            return self.makeret(prog, ret=False, msg="Specified Events not found in the database")

        classrooms = Resource.objects.filter(id=basic_cls, res_type__name="Classroom")
        if len(classrooms) < 1:
            return self.makeret(prog, ret=False, msg="Specified Classrooms not found in the database")

        classroom = classrooms[0]

        cannot_schedule = False
        if not override:
            cannot_schedule = cls.cannotSchedule(times, ignore_classes=False)
        if cannot_schedule:
            return self.makeret(prog, ret=False, msg=cannot_schedule)

        cls.assign_meeting_times(times)
        status, errors = cls.assign_room(classroom, clear_others=True)

        if not status: # If we failed any of the scheduling-constraints checks in assign_room()
            cls.clear_meeting_times()
            return self.makeret(prog, ret=False, msg=" | ".join(errors))

        #add things to the change log here
        self.get_change_log(prog).appendScheduling([int(t.id) for t in times], classroom_ids[0], int(cls.id), user)

        return self.makeret(prog, ret=True, msg="Class Section '%s' successfully scheduled" % cls.emailcode())

    @aux_call
    @needs_admin
    @json_response()
    def ajax_change_log(self, request, tl, one, two, module, extra, prog):
        cl = self.get_change_log(prog)
        last_fetched_index = int(request.GET['last_fetched_index'])

        #check whether we have a log entry at least as old as the last fetched time
        #if not, we return a command to reload instead of the log
        #note: negative number implies we want to debug dump changelog
        if cl.get_earliest_index() is not None and last_fetched_index !=0 and cl.get_earliest_index() > last_fetched_index:
            return { "other" : [ { 'command' : "reload", 'earliest_index' : cl.get_earliest_index(), 'latest_index' : cl.get_latest_index(), 'time' : time.time() } ] }

        return { "changelog" : cl.get_log(last_fetched_index), 'other' : [ { 'time': time.time() } ] }

    @aux_call
    @needs_admin
    def ajax_clear_change_log(self, request, tl, one, two, module, extra, prog):
        """ This call exists for debugging and testing purposes.  It's not a disaster if it's
        called in production, but it is annoying.
        Clears the change log for this program. """

        self.get_change_log(prog).entries.all().delete()
        return HttpResponse('')

    def get_change_log(self, prog):
        change_log = module_ext.AJAXChangeLog.objects.filter(program=prog)

        if change_log.count() == 0:
            change_log = module_ext.AJAXChangeLog()
            change_log.update(prog)
            change_log.save()
        else:
            change_log = change_log[0]

        return change_log

    @aux_call
    @needs_admin
    @json_response()
    def ajax_section_details(self, request, tl, one, two, module, extra, prog):
        sectionDetails = {}
        for sectionDetail in module_ext.AJAXSectionDetail.objects.filter(program=prog):
            sectionDetails[sectionDetail.cls_id] = [{'comment': sectionDetail.comment, 'locked': sectionDetail.locked}]
        return sectionDetails

    @aux_call
    @needs_admin
    def ajax_schedule_class(self, request, tl, one, two, module, extra, prog):
        # DON'T CACHE this function!
        # It's supposed to have side effects, that's the whole point!
        if not 'action' in request.POST:
            raise ESPError("This URL is intended to be used for client<->server communication; it's not for human-readable content.", log=False)

        # Pull relevant data out of the JSON structure
        cls_id = request.POST['cls']
        cls = ClassSection.objects.get(id=cls_id)
        action = request.POST['action']

        if action == 'deletereg':
            times = []
            classrooms = [ None ]
            retval =  self.ajax_schedule_deletereg(prog, cls, request.user)

        elif action == 'assignreg':
            blockrooms = request.POST['block_room_assignments'].split("\n")
            times = []
            classrooms = []
            for br in blockrooms:
                timeslot, classroom = br.split(",", 1)
                times.append(timeslot)
                classrooms.append(classroom)
            override = request.POST['override'] == "true"
            retval = self.ajax_schedule_assignreg(prog, cls, times, classrooms, request.user, override)
        else:
            return self.makeret(prog, ret=False, msg="Unrecognized command: '%s'" % action)

        return retval

    @aux_call
    @needs_admin
    def ajax_set_comment(self, request, tl, one, two, module, extra, prog):
        if not 'comment' in request.POST:
            raise ESPError("This URL is intended to be used for client<->server communication; it's not for human-readable content.", log=False)

        # Pull relevant data out of the JSON structure
        cls_id = request.POST['cls']
        comment = request.POST['comment']
        locked = 'locked' in request.POST

        try:
            module_ext.AJAXSectionDetail.objects.get(cls_id=cls_id).update(comment, locked)
        except module_ext.AJAXSectionDetail.DoesNotExist:
            sectionDetail = module_ext.AJAXSectionDetail()
            sectionDetail.initialize(prog, cls_id, comment, locked)

        self.get_change_log(prog).appendComment(comment, locked, cls_id, request.user)
        return self.makeret(prog, ret=True, msg="Class Section #%s successfully updated" % cls_id)

    @aux_call
    @needs_admin
    def ajax_schedule_last_changed(self, request, tl, one, two, module, extra, prog):
        return self.ajax_schedule_last_changed_helper(prog)

    def ajax_schedule_last_changed_helper(self, prog):
        ret = { 'val': str(self.ajax_schedule_get_uuid(prog)),
                'msg': 'UUID that changes every time the schedule is updated',
                'time' : time.time(),
                'latest_index' : self.get_change_log(prog).get_latest_index() }

        response = HttpResponse(content_type="application/json")
        json.dump(ret, response)
        response.raw_value = ret  # So that other functions can call this view and get the original return value back
        return response

    @cache_function
    def ajax_schedule_get_uuid(self, prog):
        return get_uuid()

    # This function should be called iff the data returned by any of the other ajax_ JSON functions changes.
    # So, cache it; and have the cache expire whenever any of the relevant models changes.
    # Yeah, the cache will get expired quite often...; but, eh, it's a cheap function.
    ajax_schedule_get_uuid.get_or_create_token(('prog',))
    ajax_schedule_get_uuid.depend_on_model('resources.ResourceAssignment')
    ajax_schedule_get_uuid.depend_on_model('resources.Resource')
    ajax_schedule_get_uuid.depend_on_model('resources.ResourceRequest')
    ajax_schedule_get_uuid.depend_on_model('cal.Event')
    ajax_schedule_get_uuid.depend_on_model('program.ClassSection')
    ajax_schedule_get_uuid.depend_on_model('program.ClassSubject')
    ajax_schedule_get_uuid.depend_on_model('users.UserAvailability')

    @cache_function
    def ajax_lunch_timeslots_cached(self, prog):
        data = list(Event.objects.filter(meeting_times__parent_class__category__category="Lunch", meeting_times__parent_class__parent_program=prog).values_list('id', flat=True))
        response = HttpResponse(content_type="application/json")
        json.dump(data, response)
        return response
    ajax_lunch_timeslots_cached.depend_on_model('cal.Event')
    ajax_lunch_timeslots_cached.depend_on_model('program.ClassSection')
    ajax_lunch_timeslots_cached.depend_on_model('program.ClassSubject')
    ajax_lunch_timeslots_cached.depend_on_model('program.ClassCategories')
    ajax_lunch_timeslots_cached.depend_on_m2m('program.ClassSection', 'meeting_times', lambda sec, event: {'prog': sec.parent_class.parent_program})

    @aux_call
    @needs_admin
    def ajax_lunch_timeslots(self, request, tl, one, two, module, extra, prog):
        return self.ajax_lunch_timeslots_cached(prog)

    @aux_call
    @needs_admin
    def ajax_clear_schedule(self, request, tl, one, two, module, extra, prog):
        """ A view that you can use to remove schedule assignments for all class
            sections below a certain lock level.
            Be very careful using this view since it can sometimes work quite well,
            and there is currently no backup.
        """
        try:
            lock_level = int(request.POST.get('lock_level', '0'))
        except:
            lock_level = 0

        if request.method == 'POST':
            num_affected_sections = self.clear_schedule_logic(prog, lock_level)
            data = {'message': 'Cleared schedule assignments for %d sections.' % (num_affected_sections)}
            response = HttpResponse(content_type="application/json")
            json.dump(data, response)
        else:
            context = {}
            context['num_affected_sections'] = self._get_affected_sections(prog, lock_level).count()
            response = render_to_response(self.baseDir()+'clear_schedule_confirmation.html', request, context)

        return response

    def _get_affected_sections(self, prog, lock_level=0):
        """
        Returns a QuerySet for ClassSection instances filtered  by parent_program and lock_level
        """
        return ClassSection.objects.filter(parent_class__parent_program=prog, resourceassignment__lock_level__lte=lock_level)

    def clear_schedule_logic(self, prog, lock_level=0):
        affected_sections = self._get_affected_sections(prog, lock_level)

        ResourceAssignment.objects.filter(target__in=affected_sections, lock_level__lte=lock_level).delete()
        ResourceAssignment.objects.filter(target__isnull=True, target_subj__isnull=True).delete()

        num_affected_sections = 0
        for section in affected_sections:
            section.meeting_times.clear()
            num_affected_sections += 1

        return num_affected_sections

    class Meta:
        proxy = True
        app_label = 'modules'
