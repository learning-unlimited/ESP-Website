
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
from esp.program.models          import Program, ClassSubject, ClassSection, ClassCategories
from esp.datatree.models         import *
from esp.web.util                import render_to_response
from django                      import forms
from django.http                 import HttpResponseRedirect, HttpResponse
from esp.cal.models              import Event
from esp.users.models            import User, ESPUser, UserBit
from esp.middleware              import ESPError
from esp.resources.models        import Resource, ResourceRequest, ResourceType
from esp.datatree.models         import DataTree
from datetime                    import timedelta
from django.utils                import simplejson
from collections                 import defaultdict

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
        sections = prog.sections().select_related('category')

        rrequests = ResourceRequest.objects.filter(target__in = sections)

        rrequest_dict = defaultdict(list)
        for r in rrequests:
            rrequest_dict[r.target_id].append(r.id)


        teacher_bits = UserBit.objects.filter(verb=GetNode('V/Flags/Registration/Teacher'), qsc__in = (s.parent_class.anchor_id for s in sections), user__isnull=False).values("qsc_id", "user_id").distinct()

        teacher_dict = defaultdict(list)
        for b in teacher_bits:
            teacher_dict[b["qsc_id"]].append(b["user_id"])

        sections_dicts = [
            {   'id': s.id,
                'text': s.title,
                'category': s.category.category,
                'length': float(s.duration),
                'teachers': teacher_dict[s.parent_class.anchor_id],
                'resource_requests': rrequest_dict[s.id]
            } for s in sections ]

        response = HttpResponse(content_type="text/x-json")
        simplejson.dump(sections_dicts, response)
        return response

    @aux_call
    @needs_admin
    def ajax_rooms(self, request, tl, one, two, module, extra, prog):
        classrooms = prog.getResources().filter(res_type__name="Classroom")

        classrooms_grouped = defaultdict(list)

        for room in classrooms:
            classrooms_grouped[room.name].append(room)

        classrooms_dicts = [
            {   'uid': room_id,
                'text': classrooms_grouped[room_id][0].name,
                'availability': [ r.event_id for r in classrooms_grouped[room_id] ],
                'associated_resources': []
            } for room_id in classrooms_grouped.keys() ]

        response = HttpResponse(content_type="text/x-json")
        simplejson.dump(classrooms_dicts, response)
        return response

    @aux_call
    @needs_admin
    def ajax_teachers(self, request, tl, one, two, module, extra, prog):
        teachers = ESPUser.objects.filter(userbit__verb=GetNode('V/Flags/Registration/Teacher')).filter(userbit__qsc__classsubject__isnull=False, userbit__qsc__parent__parent__program=prog).distinct()

        restype = ResourceType.get_or_create('Teacher Availability')
        resources = Resource.objects.filter(user__in = [t.id for t in teachers],
                                            res_type = restype,
                                            ).filter(
            QTree(event__anchor__below = prog.anchor)).values('user_id', 'event__id')


        resources_for_user = defaultdict(list)

        for resource in resources:
            resources_for_user[resource['user_id']].append(resource['event__id'])
        
        teacher_dicts = [
            {   'uid': t.id,
                'text': t.name(),
                'availability': resources_for_user[t.id]
            } for t in teachers ]

        response = HttpResponse(content_type="text/x-json")
        simplejson.dump(teacher_dicts, response)
        return response

    @aux_call
    @needs_admin
    def ajax_times(self, request, tl, one, two, module, extra, prog):
        times = list( [ dict(e) for e in Event.objects.filter(anchor=self.program_anchor_cached()).values('id', 'short_description', 'description', 'start', 'end') ] )

        for t in times:
            t['start'] = t['start'].timetuple()[:6]
            t['end'] = t['end'].timetuple()[:6]
        
        response = HttpResponse(content_type="text/x-json")
        simplejson.dump(times, response)
        return response

    @aux_call
    @needs_admin
    def ajax_resources(self, request, tl, one, two, module, extra, prog):
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

        response = HttpResponse(content_type="text/x-json")
        simplejson.dump(classrooms_dicts, response)
        return response        

    @aux_call
    @needs_admin
    def force_availability(self, request, tl, one, two, module, extra, prog):
        teacher_dict = prog.teachers(QObjects=True)
        
        if request.method == 'POST':
            if request.POST.has_key('sure') and request.POST['sure'] == 'True':
                
                #   Find all teachers who have not indicated their availability and do it for them.
                unavailable_teachers = User.objects.filter(teacher_dict['class_approved'] | teacher_dict['class_proposed']).exclude(teacher_dict['availability']).distinct()
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
            
        
