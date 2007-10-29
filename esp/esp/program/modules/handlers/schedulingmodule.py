
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
from esp.program.modules.base    import ProgramModuleObj, needs_admin
from esp.program.modules         import module_ext
from esp.program.models          import Program, Class, ClassCategories
from esp.datatree.models         import DataTree, GetNode
from esp.web.util                import render_to_response
from django                      import newforms as forms
from django.http                 import HttpResponseRedirect
from esp.cal.models              import Event
from django.core.cache           import cache
from esp.db.models               import Q
from esp.users.models            import User, ESPUser
from esp.middleware              import ESPError
from esp.resources.models        import ResourceRequest, ResourceType, Resource, ResourceAssignment
from esp.program.templatetags.scheduling import schedule_key_func, options_key_func
from datetime                    import timedelta

class SchedulingModule(ProgramModuleObj):
    """ This program module allows teachers to indicate their availability for the program. """

    def prepare(self, context={}):
        if context is None: context = {}
        
        context['schedulingmodule'] = self 
        return context

    @needs_admin
    def scheduling(self, request, tl, one, two, module, extra, prog):
        #   Renders the teacher availability page and handles submissions of said page.
        context = {}
        context['prog'] = self.program
        context['module'] = self
        
        if extra == 'refresh':
            #   Clear out all of those inclusion tags.
            for cls in self.program.classes():
                cls.clear_resource_cache()
                for teacher in cls.teachers():
                    cache_key = teacher.availability_cache_key(self.program)
                    cache.delete(cache_key)
            for room in self.program.getClassrooms():
                room.clear_schedule_cache(self.program)
            return HttpResponseRedirect(self.get_full_path())
        
        if request.method == 'POST':
            #   Build up expected post variables: starttime_[clsid], room_[clsid]
            new_dict = request.POST.copy()
                    
            for key in new_dict:
                #   Find the variables that differ from existing data (something_new vs. something_old).
                commands = key.split('_')
                needs_update = False

                if len(commands) > 2 and commands[2] == 'new':
                    compare_to_key = commands[0] + '_' + commands[1] + '_old'
                    if compare_to_key in new_dict:
                        if int(new_dict[key]) != int(new_dict[compare_to_key]):
                            needs_update = True
                    else:
                        needs_update = True
                
                if needs_update:
                    cls = Class.objects.get(id=commands[1])
                    #   Clear the availability cache for the teachers.
                    for teacher in cls.teachers():
                        cache_key = teacher.availability_cache_key(self.program)
                        cache.delete(cache_key)
                    
                    #   Clear the cached data for the rooms that the class has, so the class is removed from those.
                    if (cls.initial_rooms() is not None):
                        for room in cls.initial_rooms(): room.clear_schedule_cache(self.program)
                    
                    #   Hope you don't mind this extra temporary attribute.
                    cls.time_changed = False
                    if commands[0] == 'starttime':
                        #   Assign a new set of times to the class, clearing the rooms.
                        cls.time_changed = True
                        if int(new_dict[key]) == -1:
                            cls.meeting_times.clear()
                        else:
                            cls.assign_start_time(Event.objects.get(id=int(new_dict[key])))

                    elif commands[0] == 'room' and not cls.time_changed:
                        #   Assign a new classroom to the class, clearing others first.
                        if int(new_dict[key]) == -1:
                            cls.clearRooms()
                        else:
                            new_room = Resource.objects.get(id=int(new_dict[key]))
                            (status, errors) = cls.assign_room(new_room, compromise=True, clear_others=True)
                            if status is False:
                                raise ESPError(False), 'Classroom assignment errors: %s' % errors

                    #   Clear the cache for this class and its new room.
                    cls.clear_resource_cache()
                    if (cls.initial_rooms() is not None):
                        for room in cls.initial_rooms(): room.clear_schedule_cache(self.program)

        #   Provide some helpful statistics.  This should be totally reliant on cache.
        cls_list = list(self.program.classes())
        for c in cls_list: c.temp_status = c.scheduling_status()
        context['num_total_classes'] = len(cls_list)
        context['num_assigned_classes'] = len(filter(lambda x: x.temp_status == 'Needs resources', cls_list))
        context['num_scheduled_classes'] = len(filter(lambda x: x.temp_status == 'Needs room', cls_list))
        context['num_finished_classes'] = len(filter(lambda x: x.temp_status == 'Happy', cls_list))

        #   So far, this page shows you the same stuff no matter what you do.
        return render_to_response(self.baseDir()+'main.html', request, (prog, tl), context)
    