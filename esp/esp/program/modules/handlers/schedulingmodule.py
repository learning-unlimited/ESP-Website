
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
from esp.datatree.models import *
from esp.web.util                import render_to_response
from django                      import forms
from django.http                 import HttpResponseRedirect
from esp.cal.models              import Event
from django.core.cache           import cache
from django.db.models.query      import Q
from esp.users.models            import User, ESPUser
from esp.middleware              import ESPError
from esp.resources.models        import ResourceRequest, ResourceType, Resource, ResourceAssignment
from esp.program.templatetags.scheduling import schedule_key_func, options_key_func
from datetime                    import timedelta

class SchedulingModule(ProgramModuleObj):
    """ This program module allows teachers to indicate their availability for the program. """

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Scheduling",
            "module_type": "manage",
            "main_call": "scheduling",
            "aux_calls": "force_availability,view_requests,securityschedule",
            "seq": 8
            }
    
    def prepare(self, context={}):
        if context is None: context = {}
        
        context['schedulingmodule'] = self 
        return context

    @main_call
    @needs_admin
    def scheduling(self, request, tl, one, two, module, extra, prog):
        #   Renders the teacher availability page and handles submissions of said page.
        context = {}
        context['prog'] = self.program
        context['module'] = self
        
        if extra == 'refresh':
            #   Clear out all of those inclusion tags.
            for cls in self.program.classes():
                cache_key = options_key_func(cls)
                cache.delete(cache_key)
                for sec in cls.sections.all():
                    sec.clear_resource_cache()
                for teacher in cls.teachers():
                    # This probably isn't needed anymore, but oh well
                    ESPUser.getAvailableTimes.delete_key_set(self=teacher, program=self.program)
            for room in self.program.getClassrooms():
                room.clear_schedule_cache(self.program)
            return HttpResponseRedirect(self.get_full_path())
        
        if request.method == 'POST':
            #   Build up expected post variables: starttime_[clsid], room_[clsid]
            new_dict = request.POST.copy()

            obj_ids_to_process = set([ x[:-6] for x in new_dict.keys() if x[-6:] == "-dirty" and new_dict[x] == "True" ])
            class_ids_to_process = [x[4:] for x in obj_ids_to_process if x[:4] == 'cls-']
            section_ids_to_process = [x[4:] for x in obj_ids_to_process if x[:4] == 'sec-']
  
            key_list = new_dict.keys()
            key_list = filter(lambda a: a.endswith('new'), key_list)
            key_list.sort()
            # assert False, '\n'.join([str((k, new_dict[k])) for k in key_list])
            # sec_update_list = []
            # assert False, section_ids_to_process
            for key in key_list:
                #   Find the variables that differ from existing data (something_new vs. something_old).
                commands = key.split('_')
                needs_update = False

                #   Check whether this key applies to a section.
                #   (Subjects currently don't have any options to change.)
                if (len(commands) > 2) and (commands[1] in section_ids_to_process) and (commands[2] == 'new'):
                    compare_to_key = commands[0] + '_' + commands[1] + '_old'
                    if compare_to_key in new_dict:
                        if int(new_dict[key]) != int(new_dict[compare_to_key]):
                            needs_update = True
                    else:
                        needs_update = True
                
                if needs_update:
                    sec = ClassSection.objects.get(id=commands[1])
                    cls = sec.parent_class
                    
                    #   Clear the availability cache for the teachers.
                    for teacher in cls.teachers():
                        # This probably isn't needed anymore, but oh well
                        ESPUser.getAvailableTimes.delete_key_set(self=teacher, program=self.program)
                    
                    #   Clear the cached data for the rooms that the class has, so the class is removed from those.
                    if (sec.initial_rooms().count() > 0):
                        for room in sec.initial_rooms(): room.clear_schedule_cache(self.program)
                    
                    #   Hope you don't mind this extra temporary attribute.
                    sec.time_changed = False
                    if commands[0] == 'starttime':
                        #   Assign a new set of times to the class, clearing the rooms.
                        sec.time_changed = True
                        if int(new_dict[key]) == -1:
                            sec.meeting_times.clear()
                        else:
                            sec.assign_start_time(Event.objects.get(id=int(new_dict[key])))

                    elif commands[0] == 'room' and not sec.time_changed:
                        #   Assign a new classroom to the class, clearing others first.
                        if int(new_dict[key]) == -1:
                            sec.clearRooms()
                        else:
                            new_room = Resource.objects.get(id=int(new_dict[key]))
                            (status, errors) = sec.assign_room(new_room, compromise=True, clear_others=True)
                            if status is False:
                                raise ESPError(False), 'Classroom assignment errors: <ul><li>%s</li></ul>' % '</li><li>'.join(errors)

                    #   Clear the cache for this class and its new room.
                    sec.clear_resource_cache()
                    opt_key = options_key_func(cls)
                    cache.delete(opt_key)
                    if (sec.initial_rooms().count() > 0):
                        for room in sec.initial_rooms(): room.clear_schedule_cache(self.program)

        def count(fn, lst):
            return reduce(lambda count, item: fn(item) and count + 1 or count, lst, 0)

        #   Provide some helpful statistics.  This should be totally reliant on cache.
        cls_list = list(self.program.classes())
        sec_list = list(self.program.sections())
        for c in sec_list: c.temp_status = c.scheduling_status()
        context['num_total_classes'] = len(sec_list)
        context['num_assigned_classes'] = len(filter(lambda x: x.temp_status == 'Needs resources', sec_list))
        context['num_scheduled_classes'] = len(filter(lambda x: x.temp_status == 'Needs room', sec_list))
        context['num_finished_classes'] = len(filter(lambda x: x.temp_status == 'Happy', sec_list))

        #   So far, this page shows you the same stuff no matter what you do.
        return render_to_response(self.baseDir()+'main.html', request, (prog, tl), context)

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
    def view_requests(self, request, tl, one, two, module, extra, prog):
        """ Show summary information useful to directors scheduling a program:
            - classroom type/equipment requests (those checked off)
            - special requests (those entered in optionally)
            - desired rooms (entered in optionally)
        """
        
        context = {}
        context['prog'] = prog
        context['classes'] = prog.classes()
        context['sections'] = prog.sections()
        
        if extra == 'csv':
            from django.template import loader
            from django.http import HttpResponse
            content = loader.render_to_string(self.baseDir()+'requests.csv', context)
            response = HttpResponse(content, mimetype='text/csv')
            response['Content-Disposition'] = 'attachment; filename=requests.csv'
            return response
        else:
            return render_to_response(self.baseDir()+'requests.html', request, (prog, tl), context)

    @aux_call
    @needs_admin
    def securityschedule(self, request, tl, one, two, module, extra, prog):
        """ Display a list of classes (by classroom) for each timeblock in a program """
        events = Event.objects.filter(anchor=prog.anchor).order_by('start')
        events_ctxt = [ { 'event': e, 'classes': ClassSection.objects.filter(meeting_times=e).select_related() } for e in events ]

        context = { 'events': events_ctxt }

        return render_to_response(self.baseDir()+'securityschedule.html', request, (prog, tl), context)
            
        
