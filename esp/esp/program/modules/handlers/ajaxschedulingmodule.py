
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
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
from esp.users.models            import User, ESPUser, UserBit, UserAvailability
from esp.middleware              import ESPError
from esp.resources.models        import Resource, ResourceRequest, ResourceType, ResourceAssignment
from esp.datatree.models         import DataTree
from datetime                    import timedelta
from django.utils                import simplejson
from collections                 import defaultdict
from esp.cache                   import cache_function
from uuid                        import uuid4 as get_uuid

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

        context = {}
        
        return render_to_response(self.baseDir()+'ajax_scheduling.html', request, (prog, tl), context)

    @aux_call
    @needs_admin
    def ajax_sections(self, request, tl, one, two, module, extra, prog):
        return self.ajax_sections_cached(prog)

    @cache_function
    def ajax_sections_cached(self, prog):
        sections = prog.sections().select_related('category', 'parent_class', 'optimal_class_size_range')

        rrequests = ResourceRequest.objects.filter(target__in = sections)

        rrequest_dict = defaultdict(list)
        for r in rrequests:
            rrequest_dict[r.target_id].append((r.res_type_id, r.desired_value))


        teacher_bits = UserBit.valid_objects().filter(verb=GetNode('V/Flags/Registration/Teacher'), qsc__in = (s.parent_class.anchor_id for s in sections), user__isnull=False).values("qsc_id", "user_id").distinct()

        teacher_dict = defaultdict(list)
        for b in teacher_bits:
            teacher_dict[b["qsc_id"]].append(b["user_id"])
        
        sections_dicts = [
            {   'id': s.id,
                'class_id': s.parent_class_id,
                'emailcode': s.emailcode(),
                'text': s.title(),
                'category': s.category.category,
                'length': float(s.duration),
                'teachers': teacher_dict[s.parent_class.anchor_id],
                'resource_requests': rrequest_dict[s.id],
                'max_class_capacity': s.max_class_capacity,
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
    ajax_sections_cached.depend_on_model(lambda: ClassSubject)
    ajax_sections_cached.depend_on_model(lambda: ClassSection)
    ajax_sections_cached.depend_on_model(lambda: ClassSizeRange)
    ajax_sections_cached.depend_on_model(lambda: ResourceRequest)
    ajax_sections_cached.depend_on_model(lambda: UserBit)
        

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
    ajax_rooms_cached.depend_on_model(lambda: Resource)
    

    @aux_call
    @needs_admin
    def ajax_teachers(self, request, tl, one, two, module, extra, prog):
        return self.ajax_teachers_cached(prog)

    @cache_function
    def ajax_teachers_cached(self, prog):
        teachers = ESPUser.objects.filter(userbit__verb=GetNode('V/Flags/Registration/Teacher')).filter(userbit__qsc__classsubject__isnull=False, userbit__qsc__parent__parent__program=prog).distinct()

        resources = UserAvailability.objects.filter(user__in=teachers).filter(QTree(event__anchor__below = prog.anchor)).values('user_id', 'event_id')
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
    ajax_teachers_cached.depend_on_model(UserBit)
    ajax_teachers_cached.depend_on_model(UserAvailability)
    

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
        resources = Resource.objects.filter(event__anchor=self.program_anchor_cached()).exclude(res_type__name__in=["Classroom", "Teacher Availability"])

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
    ajax_resources_cached.depend_on_model(lambda: Resource)


    @aux_call
    @needs_admin
    def ajax_schedule_assignments(self, request, tl, one, two, module, extra, prog):
        return self.ajax_schedule_assignments_cached(prog)

    @cache_function
    def ajax_schedule_assignments_cached(self, prog):
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
    ajax_schedule_assignments_cached.get_or_create_token(('prog',))
    ajax_schedule_assignments_cached.depend_on_model(lambda: ResourceAssignment)

    @aux_call
    @needs_admin
    def ajax_schedule_class(self, request, tl, one, two, module, extra, prog):
        # DON'T CACHE this function!
        # It's supposed to have side effects, that's the whole point!
        if not request.POST.has_key('action'):
            raise ESPError(False), "This URL is intended to be used for client<->server communication; it's not for human-readable content."

        # Pull relevant data out of the JSON structure
        cls = ClassSection.objects.get(id=request.POST['cls'])
        action = request.POST['action']

        def makeret(**kwargs):
            last_changed = self.ajax_schedule_last_changed_cached(prog).raw_value
            kwargs['val'] = last_changed['val']
            response = HttpResponse(content_type="application/json")
            simplejson.dump(kwargs, response)
            return response            
        
        if action == 'deletereg':
            cls.clearRooms()
            cls.clear_meeting_times()

            return makeret(ret=True, msg="Schedule removed for Class Section '%s'" % cls.emailcode())

        elif action == 'assignreg':
            blockrooms = request.POST['block_room_assignments'].split("\n")
            blockrooms = [b.split(",") for b in blockrooms if b]
            blockrooms = [{'time_id': b[0], 'room_id': b[1]} for b in blockrooms]
            
            times = [br['time_id'] for br in blockrooms]
            classrooms = [br['room_id'] for br in blockrooms]

            if len(times) < 1:
                return makeret(ret=False, msg="No times specified!, can't assign to a timeblock")

            if len(classrooms) < 1:
                return makeret(ret=False, msg="No classrooms specified!, can't assign to a timeblock")

            basic_cls = classrooms[0]
            for c in classrooms:
                if c != basic_cls:
                    return makeret(ret=False, msg="Assigning one section to multiple rooms.  This interface doesn't support this feature currently; assign it to one room for now and poke a Webmin to do this for you manually.")
                
            times = Event.objects.filter(id__in=times)
            if len(times) < 1:
                return makeret(ret=False, msg="Specified Events not found in the database")

            classrooms = Resource.objects.filter(name=basic_cls, res_type__name="Classroom")
            if len(classrooms) < 1:
                return makeret(ret=False, msg="Specified Classrooms not found in the database")

            classroom = classrooms[0]

            cls.assign_meeting_times(times)
            status, errors = cls.assign_room(classroom)

            if not status: # If we failed any of the scheduling-constraints checks in assign_room()
                return makeret(ret=False, msg=" | ".join(errors))
            
            return makeret(ret=True, msg="Class Section '%s' successfully scheduled" % cls.emailcode())
        else:
            return makeret(ret=False, msg="Unrecognized command: '%s'" % action)

        
    @aux_call
    @needs_admin
    def ajax_schedule_last_changed(self, request, tl, one, two, module, extra, prog):
        return self.ajax_schedule_last_changed_cached(prog)

    @cache_function
    def ajax_schedule_last_changed_cached(self, prog):
        # ret['val'] should be a valid nonce that's regenerated no less often than whenever the data changes
        ret = { 'val': str(get_uuid()),  
                'msg': 'UUID that changes every time the schedule is updated' }

        response = HttpResponse(content_type="application/json")
        simplejson.dump(ret, response)
        response.raw_value = ret  # So that other functions can call this view and get the original return value back
        return response

    # This function should be called iff the data returned by any of the other ajax_ JSON functions changes.
    # So, cache it; and have the cache expire whenever any of the relevant models changes.
    # Yeah, the cache will get expired quite often...; but, eh, it's a cheap function.
    ajax_schedule_last_changed_cached.get_or_create_token(('prog',))
    ajax_schedule_last_changed_cached.depend_on_model(lambda: ResourceAssignment)
    ajax_schedule_last_changed_cached.depend_on_model(lambda:Resource)
    ajax_schedule_last_changed_cached.depend_on_model(lambda: ResourceRequest)
    ajax_schedule_last_changed_cached.depend_on_model(lambda: Event)
    ajax_schedule_last_changed_cached.depend_on_model(lambda: UserBit)
    ajax_schedule_last_changed_cached.depend_on_model(lambda: ClassSection)
    ajax_schedule_last_changed_cached.depend_on_model(lambda: ClassSubject)
    ajax_schedule_last_changed_cached.depend_on_model(lambda: UserAvailability)

    
    @aux_call
    @needs_admin
    def force_availability(self, request, tl, one, two, module, extra, prog):
        teacher_dict = prog.teachers(QObjects=True)
        
        if request.method == 'POST':
            if request.POST.has_key('sure') and request.POST['sure'] == 'True':
                
                #   Find all teachers who have not indicated their availability and do it for them.
                unavailable_teachers = User.objects.filter((teacher_dict['class_approved'] | teacher_dict['class_proposed']) & ~teacher_dict['availability']).distinct()
                for t in unavailable_teachers:
                    teacher = ESPUser(t)
                    for ts in prog.getTimeSlots():
                        teacher.addAvailableTime(self.program, ts)
                        
                return self.scheduling(request, tl, one, two, module, 'refresh', prog)
            else:
                return self.scheduling(request, tl, one, two, module, '', prog)
                
        #   Normally, though, return a page explaining the issue.
        context = {'prog': self.program}
        context['good_teacher_num'] = User.objects.filter(teacher_dict['class_approved']).filter(teacher_dict['availability']).distinct().count()
        context['total_teacher_num'] = User.objects.filter(teacher_dict['class_approved']).distinct().count()

        return render_to_response(self.baseDir()+'force_prompt.html', request, (prog, tl), context)

    @aux_call
    @needs_admin
    def securityschedule(self, request, tl, one, two, module, extra, prog):
        """ Display a list of classes (by classroom) for each timeblock in a program """
        events = Event.objects.filter(anchor=prog.anchor).order_by('start')
        events_ctxt = [ { 'event': e, 'classes': ClassSection.objects.filter(meeting_times=e).select_related() } for e in events ]

        context = { 'events': events_ctxt }

        return render_to_response(self.baseDir()+'securityschedule.html', request, (prog, tl), context)
            
        
