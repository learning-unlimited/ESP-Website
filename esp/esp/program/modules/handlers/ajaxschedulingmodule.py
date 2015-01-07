
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
from esp.datatree.models         import *
from esp.web.util                import render_to_response
from django                      import forms
from django.http                 import HttpResponseRedirect, HttpResponse
from django.template.loader      import render_to_string
from esp.cal.models              import Event
from esp.users.models            import User, ESPUser, UserAvailability
from esp.middleware              import ESPError
from esp.resources.models        import Resource, ResourceRequest, ResourceType, ResourceAssignment
from esp.datatree.models         import DataTree
from datetime                    import timedelta, time
from django.utils                import simplejson
from collections                 import defaultdict
from esp.cache                   import cache_function
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
            "seq": 7
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
        context = {}
        
        return render_to_response(self.baseDir()+'ajax_scheduling.html', request, context)

    @aux_call
    @needs_admin
    def ajax_sections(self, request, tl, one, two, module, extra, prog):
        return self.ajax_sections_cached(prog, request.GET.has_key('accepted_only'))

    @cache_function
    def ajax_sections_cached(self, prog, accepted_only=False):
        if accepted_only:
            sections = prog.sections().filter(status__gt=0, parent_class__status__gt=0).select_related() 
        else:
            sections = prog.sections().select_related()

        rrequests = ResourceRequest.objects.filter(target__in = sections)

        rrequest_dict = defaultdict(list)
        for r in rrequests:
            rrequest_dict[r.target_id].append((r.res_type_id, r.desired_value))
        
        sections_dicts = [
            {   'id': s.id,
                'class_id': s.parent_class_id,
                'emailcode': s.emailcode(),
                'text': s.title(),
                'category': s.category.category,
                'length': float(s.duration),
                'teachers': [t.id for t in s.parent_class.get_teachers()],
                'resource_requests': rrequest_dict[s.id],
                'max_class_capacity': s.max_class_capacity,
                'capacity': s.capacity,
                'class_size_max': s.parent_class.class_size_max,
                'optimal_class_size': s.parent_class.class_size_optimal,
                'optimal_class_size_range': s.parent_class.optimal_class_size_range.range_str() if s.parent_class.optimal_class_size_range else None,
                'allowable_class_size_ranges': [ cr.range_str() for cr in s.parent_class.get_allowable_class_size_ranges() ],
                'status': s.status,
                'parent_status': s.parent_class.status,
                'grades': [s.parent_class.grade_min, s.parent_class.grade_max],
                'prereqs': s.parent_class.prereqs,
                'comments': s.parent_class.message_for_directors,
            } for s in sections ]

        response = HttpResponse(content_type="application/json")
        simplejson.dump(sections_dicts, response)
        return response
    ajax_sections_cached.get_or_create_token(('prog',))
    ajax_sections_cached.depend_on_model('program.ClassSubject')
    ajax_sections_cached.depend_on_model('program.ClassSection')
    ajax_sections_cached.depend_on_model('program.ClassSizeRange')
    ajax_sections_cached.depend_on_model('resources.ResourceRequest')

    @aux_call
    @needs_admin
    def ajax_rooms(self, request, tl, one, two, module, extra, prog):
        return self.ajax_rooms_cached(prog)

    @cache_function
    def ajax_rooms_cached(self, prog):
        classrooms = prog.getResources().filter(res_type__name="Classroom")

        classrooms_grouped = defaultdict(list)

        for room in classrooms:
            classrooms_grouped[room.name].append(room)

        classrooms_dicts = [
            {   'uid': room_id,
                'text': classrooms_grouped[room_id][0].name,
                'availability': [ r.event_id for r in classrooms_grouped[room_id] ],
                'associated_resources': [ar.res_type.id for ar in classrooms_grouped[room_id][0].associated_resources()],
                'num_students': classrooms_grouped[room_id][0].num_students,
            } for room_id in classrooms_grouped.keys() ]

        response = HttpResponse(content_type="application/json")
        simplejson.dump(classrooms_dicts, response)
        return response
    ajax_rooms_cached.get_or_create_token(('prog',))
    ajax_rooms_cached.depend_on_model('resources.Resource')
    

    @aux_call
    @needs_admin
    def ajax_teachers(self, request, tl, one, two, module, extra, prog):
        return self.ajax_teachers_cached(prog)

    @cache_function
    def ajax_teachers_cached(self, prog):
        teachers = ESPUser.objects.filter(classsubject__parent_program=prog).distinct()
        resources = UserAvailability.objects.filter(user__in=teachers).filter(event__program = prog).values('user_id', 'event_id')
        resources_for_user = defaultdict(list)

        for resource in resources:
            resources_for_user[resource['user_id']].append(resource['event_id'])
        
        teacher_dicts = [
            {   'uid': t.id,
                'text': t.name(),
                'availability': resources_for_user[t.id]
            } for t in teachers ]

        response = HttpResponse(content_type="application/json")
        simplejson.dump(teacher_dicts, response)
        return response
    ajax_teachers_cached.get_or_create_token(('prog',))
    ajax_teachers_cached.depend_on_model(UserAvailability)
    ajax_teachers_cached.depend_on_m2m(ClassSubject, 'teachers', lambda sub, teacher: {'prog': sub.parent_program})
    
    @aux_call
    @needs_admin
    def ajax_times(self, request, tl, one, two, module, extra, prog):
        return self.ajax_times_cached(prog)

    @cache_function
    def ajax_times_cached(self, prog):
        times = list( [ dict(e) for e in prog.getTimeSlots().values('id', 'short_description', 'description', 'start', 'end') ] )

        for t in times:
            t['start'] = t['start'].timetuple()[:6]
            t['end'] = t['end'].timetuple()[:6]
        
        response = HttpResponse(content_type="application/json")
        simplejson.dump(times, response)
        return response
    ajax_times_cached.get_or_create_token(('prog',))
    ajax_times_cached.depend_on_model(Event)


    @aux_call
    @needs_admin
    def ajax_resourcetypes(self, request, tl, one, two, module, extra, prog):
        return self.ajax_resourcetypes_cached(prog)

    @cache_function
    def ajax_resourcetypes_cached(self, prog):
        resourcetypes = ResourceType.objects.filter(program=prog)
        if len(resourcetypes) == 0:
            resourcetypes = ResourceType.objects.filter(program__isnull=True)

        resourcetypes_dicts = [
            {
                'uid': rt.id,
                'name': rt.name,
                'description': rt.description,
                'attributes': rt.attributes_pickled.split("|"),  ## .attributes wasn't working properly; so just using this for now -- aseering 10/21/2010
                }
            for rt in resourcetypes ]


        response = HttpResponse(content_type="application/json")
        simplejson.dump(resourcetypes_dicts, response)
        return response
    ajax_times_cached.get_or_create_token(('prog',))
    ajax_times_cached.depend_on_model(ResourceType)

    @aux_call
    @needs_admin
    def ajax_resources(self, request, tl, one, two, module, extra, prog):
        return self.ajax_resources_cached(prog)

    @cache_function
    def ajax_resources_cached(self, prog):
        resources = Resource.objects.filter(event__program=self.program).exclude(res_type__name__in=["Classroom", "Teacher Availability"])

        resources_grouped = defaultdict(list)

        for resource in resources:
            resources_grouped[resource.name].append(resource)

        classrooms_dicts = [
            {   'uid': rsrc_id,
                'text': resources_grouped[rsrc_id][0].name,
                'availability': [ r.event_id for r in resources_grouped[rsrc_id] ],
                'associated_resources': []
            } for rsrc_id in resources_grouped.keys() ]

        response = HttpResponse(content_type="application/json")
        simplejson.dump(classrooms_dicts, response)
        return response
    ajax_resources_cached.get_or_create_token(('prog',))
    ajax_resources_cached.depend_on_model('resources.Resource')


    @aux_call
    @needs_admin
    def ajax_schedule_assignments(self, request, tl, one, two, module, extra, prog):
        resource_assignments = ResourceAssignment.objects.filter(target__parent_class__parent_program=prog, resource__res_type__name="Classroom").select_related('resource')

        resassign_dicts = [
            { 'uid': r.id,
              'resource_id': r.resource.name,
              'resource_time_id': r.resource.event_id,
              'classsection_id': r.target_id,
              'classsubject_id': r.target_subj_id
              } for r in resource_assignments ]

        response = HttpResponse(content_type="application/json")
        simplejson.dump(resassign_dicts, response)
        return response
    
    @aux_call
    @needs_admin
    def ajax_schedule_assignments_csv(self, request, tl, one, two, module, extra, prog):
        lst = []
        for s in prog.sections():
            if s.resourceassignment_set.all().count() > 0:
                ra = s.resourceassignment_set.all().order_by('resource__event__id')[0]
                lst.append((s.id, ra.resource.name, ra.resource.event.id))

        return HttpResponse('\n'.join([','.join(['"%s"' % v for v in x]) for x in lst]), mimetype='text/csv')

    #helper functions for ajax_schedule_class
    #seperated out here to make code more readeable and enable testing
    def makeret(self, prog, **kwargs):
        last_changed = self.ajax_schedule_last_changed_helper(prog).raw_value
        kwargs['val'] = last_changed['val']
        response = HttpResponse(content_type="application/json")
        simplejson.dump(kwargs, response)
        return response            

    def ajax_schedule_deletereg(self, prog, cls, user=None):
        cls.clearRooms()
        cls.clear_meeting_times()
        self.get_change_log(prog).append([], "", int(cls.id), user)

        return self.makeret(prog, ret=True, msg="Schedule removed for Class Section '%s'" % cls.emailcode())

    def ajax_schedule_assignreg(self, prog, cls, blockrooms, times, classrooms, user=None):
        classroom_names = classrooms

        if len(times) < 1:
            return self.makeret(prog, ret=False, msg="No times specified!, can't assign to a timeblock")

        if len(classrooms) < 1:
            return self.makeret(prog, ret=False, msg="No classrooms specified!, can't assign to a timeblock")

        #TODO:  this loom modifies classrooms from within the loop.  That seems like a bad idea.  
        #we should figure out why
        basic_cls = classrooms[0]
        for c in classrooms:
            if c != basic_cls:
                return self.makeret(prog, ret=False, msg="Assigning one section to multiple rooms.  This interface doesn't support this feature currently; assign it to one room for now and poke a Webmin to do this for you manually.")
            
            times = Event.objects.filter(id__in=times).order_by('start')
            if len(times) < 1:
                return self.makeret(prog, ret=False, msg="Specified Events not found in the database")

            classrooms = Resource.objects.filter(name=basic_cls, res_type__name="Classroom")
            if len(classrooms) < 1:
                return self.makeret(prog, ret=False, msg="Specified Classrooms not found in the database")

            classroom = classrooms[0]

            cannot_schedule = cls.cannotSchedule(times, ignore_classes=False)
            if cannot_schedule:
                return self.makeret(prog, ret=False, msg=cannot_schedule)
            
            cls.assign_meeting_times(times)
            status, errors = cls.assign_room(classroom)

            if not status: # If we failed any of the scheduling-constraints checks in assign_room()
                cls.clear_meeting_times()
                return self.makeret(prog, ret=False, msg=" | ".join(errors))
            
            #add things to the change log here
            self.get_change_log(prog).append([int(t.id) for t in times], classroom_names[0], int(cls.id), user)

            return self.makeret(prog, ret=True, msg="Class Section '%s' successfully scheduled" % cls.emailcode())

    @aux_call
    @needs_admin
    @json_response()
    def ajax_change_log(self, request, tl, one, two, module, extra, prog):
        cl = self.get_change_log(prog)
        last_fetched_index = int(request.GET['last_fetched_index'])
        
        #print "schedule_time", cl[0]['schedule_time']
        #print "last fetched time", last_fetched_time
        #print "len(cl)", len(cl)

        #check whether we have a log entry at least as old as the last fetched time
        #if not, we return a command to reload instead of the log
        #note: negative number implies we want to debug dump changelog
        if cl.get_earliest_index() is not None and cl.get_earliest_index() > last_fetched_index:
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
    def ajax_schedule_class(self, request, tl, one, two, module, extra, prog):
        # DON'T CACHE this function!
        # It's supposed to have side effects, that's the whole point!
        if not request.POST.has_key('action'):
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
            blockrooms = [b.split(",") for b in blockrooms if b]
            blockrooms = [{'time_id': b[0], 'room_id': b[1]} for b in blockrooms]
            
            times = [br['time_id'] for br in blockrooms]
            classrooms = [br['room_id'] for br in blockrooms]
            retval = self.ajax_schedule_assignreg(prog, cls, blockrooms, times, classrooms, request.user)
        else:
            return self.makeret(prog, ret=False, msg="Unrecognized command: '%s'" % action)

        return retval
    
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
        simplejson.dump(ret, response)
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
        simplejson.dump(data, response)
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
    def securityschedule(self, request, tl, one, two, module, extra, prog):
        """ Display a list of classes (by classroom) for each timeblock in a program """
        events = Event.objects.filter(program=prog).order_by('start')
        events_ctxt = [ { 'event': e, 'classes': ClassSection.objects.filter(meeting_times=e).select_related() } for e in events ]

        context = { 'events': events_ctxt }

        return render_to_response(self.baseDir()+'securityschedule.html', request, context)
            
    @aux_call
    @needs_admin
    def ajax_clear_schedule(self, request, tl, one, two, module, extra, prog):
        """ A view that you can use to remove schedule assignments for all class
            sections below a certain lock level.
            Be very careful using this view since it can sometimes work quite well,
            and there is currently no backup.
        """
        
        try:
            lock_level = int(request.GET.get('lock_level', '0'))
        except:
            lock_level = 0
        print lock_level
            
        num_affected_sections = self.clear_schedule_logic(prog, lock_level)

        data = {'message': 'Cleared schedule assignments for %d sections.' % (num_affected_sections)}
        response = HttpResponse(content_type="application/json")
        simplejson.dump(data, response)
        return response

    def clear_schedule_logic(self, prog, lock_level=0):
        affected_sections = ClassSection.objects.filter(parent_class__parent_program=prog, resourceassignment__lock_level__lte=lock_level)
        num_affected_sections = affected_sections.distinct().count()
        ResourceAssignment.objects.filter(target__in=affected_sections, lock_level__lte=lock_level).delete()
        ResourceAssignment.objects.filter(target__isnull=True, target_subj__isnull=True).delete()
        for section in affected_sections:
            section.meeting_times.clear()
        
        return num_affected_sections

    class Meta:
        proxy = True
