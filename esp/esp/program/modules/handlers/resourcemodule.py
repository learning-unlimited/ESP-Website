
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

from django.contrib.auth.decorators import login_required

from esp.web.util        import render_to_response

from esp.cal.models import Event
from esp.resources.models import ResourceType, Resource, ResourceAssignment
from esp.program.models import ClassSubject, ClassSection, Program
from esp.users.models import UserBit, ESPUser
from esp.middleware import ESPError

from esp.program.modules.base import ProgramModuleObj, needs_admin, usercheck_usetl, main_call, aux_call
from esp.program.modules import module_ext

from esp.program.modules.forms.resources import ClassroomForm, TimeslotForm, ResourceTypeForm, EquipmentForm, ClassroomImportForm

class ResourceModule(ProgramModuleObj):
    doc = """ Manage the resources used by a program.  This includes classrooms and LCD equipment.
    Also use this module to set up the time blocks for classes.
    """
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Resource Management",
            "link_title": "Manage Times and Rooms",
            "module_type": "manage",
            "seq": 10
            }

    @main_call
    @needs_admin
    def resources(self, request, tl, one, two, module, extra, prog):
	context = {}
        
        #   Process commands.  I know the code is mostly copied between the three options, and
        #   I will try to condense it intelligently when  I get the chance.
        if extra == 'timeslot':
            if request.GET.has_key('op') and request.GET['op'] == 'edit':
                #   pre-fill form
                current_slot = Event.objects.get(id=request.GET['id'])
                context['timeslot_form'] = TimeslotForm()
                context['timeslot_form'].load_timeslot(current_slot)
                
            if request.GET.has_key('op') and request.GET['op'] == 'delete':
                #   show delete confirmation page
                context['prog'] = self.program
                context['timeslot'] = Event.objects.get(id=request.GET['id'])
                return render_to_response(self.baseDir()+'timeslot_delete.html', request, (prog, tl), context)
            
            if request.method == 'POST':
                data = request.POST
                
                if data['command'] == 'reallyremove':
                    #   delete timeslot
                    ts = Event.objects.get(id=data['id'])
                    ts.delete()
                    
                elif data['command'] == 'addedit':
                    #   add/edit timeslot
                    form = TimeslotForm(data)
                    if form.is_valid():
                        if form.cleaned_data['id'] is not None:
                            new_timeslot = Event.objects.get(id=form.cleaned_data['id'])
                        else:
                            new_timeslot = Event()
                            
                        form.save_timeslot(self.program, new_timeslot)
                    else:
                        context['timeslot_form'] = form
                
        elif extra == 'restype':
            if request.GET.has_key('op') and request.GET['op'] == 'edit':
                #   pre-fill form
                current_slot = ResourceType.objects.get(id=request.GET['id'])
                context['restype_form'] = ResourceTypeForm()
                context['restype_form'].load_restype(current_slot)
                
            if request.GET.has_key('op') and request.GET['op'] == 'delete':
                #   show delete confirmation page
                context['prog'] = self.program
                context['restype'] = ResourceType.objects.get(id=request.GET['id'])
                return render_to_response(self.baseDir()+'restype_delete.html', request, (prog, tl), context)
                
            if request.method == 'POST':
                data = request.POST
                
                if data['command'] == 'reallyremove':
                    #   delete restype
                    ts = ResourceType.objects.get(id=data['id'])
                    ts.delete()
                    
                elif data['command'] == 'addedit':
                    #   add/edit restype
                    form = ResourceTypeForm(data)

                    if form.is_valid():
                        if form.cleaned_data['id'] is not None:
                            new_restype = ResourceType.objects.get(id=form.cleaned_data['id'])
                        else:
                            new_restype = ResourceType()
                            
                        form.save_restype(self.program, new_restype)
                    else:
                        context['restype_form'] = form
                
        elif extra == 'classroom':
            if request.GET.has_key('op') and request.GET['op'] == 'edit':
                #   pre-fill form
                current_room = Resource.objects.get(id=request.GET['id'])
                context['classroom_form'] = ClassroomForm(self.program)
                context['classroom_form'].load_classroom(self.program, current_room)
                
            if request.GET.has_key('op') and request.GET['op'] == 'delete':
                #   show delete confirmation page
                context['prog'] = self.program
                context['classroom'] = Resource.objects.get(id=request.GET['id'])
                resources = self.program.getClassrooms().filter(name=context['classroom'].name)
                context['timeslots'] = [r.event for r in resources]
                sections = ClassSection.objects.filter(resourceassignment__resource__id__in=resources.values_list('id', flat=True)).distinct()
                
                context['sections'] = sections
                return render_to_response(self.baseDir()+'classroom_delete.html', request, (prog, tl), context)
                
            if request.method == 'POST':
                data = request.POST
                
                if data['command'] == 'reallyremove':
                    #   delete classroom and associated resources
                    target_resource = Resource.objects.get(id=data['id'])
                    rooms = prog.getClassrooms().filter(name=target_resource.name)
                    for room in rooms:
                        room.associated_resources().delete()
                    rooms.delete()
                    
                elif data['command'] == 'addedit':
                    #   add/edit restype
                    form = ClassroomForm(self.program, data)

                    if form.is_valid():
                        form.save_classroom(self.program)
                    else:
                        context['classroom_form'] = form

        elif extra == 'classroom_import':
            import_mode = 'preview'
            if 'import_confirm' in request.POST and request.POST['import_confirm'] == 'yes':
                import_mode = 'save'
                
            import_form = ClassroomImportForm(request.POST)
            if not import_form.is_valid():
                context['import_form'] = import_form
            else:
                #   Attempt to match timeslots for the programs
                past_program = import_form.cleaned_data['program']
                ts_old = past_program.getTimeSlots().filter(event_type__description__icontains='class').order_by('start')
                ts_new = self.program.getTimeSlots().filter(event_type__description__icontains='class').order_by('start')
                ts_map = {}
                for i in range(min(len(ts_old), len(ts_new))):
                    ts_map[ts_old[i].id] = ts_new[i]
                
                resource_list = []
                #   Iterate over the resources in the previous program
                for res in past_program.getClassrooms():
                    #   If we know what timeslot to put it in, make a copy
                    if res.event.id in ts_map:
                        new_res = Resource()
                        new_res.name = res.name
                        new_res.res_type = res.res_type
                        new_res.num_students = res.num_students
                        new_res.is_unique = res.is_unique
                        new_res.user = res.user
                        new_res.event = ts_map[res.event.id]
                        #   Check to avoid duplicating rooms (so the process is idempotent)
                        if import_mode == 'save' and not Resource.objects.filter(name=new_res.name, event=new_res.event).exists():
                            new_res.save()
                        #   Note: furnishings are messed up, so don't bother copying those yet.
                        resource_list.append(new_res)
                
                #   Render a preview page showing the resources for the previous program if desired
                context['past_program'] = past_program
                if import_mode == 'preview':
                    context['prog'] = self.program
                    result = self.program.collapsed_dict(resource_list)
                    key_list = result.keys()
                    key_list.sort()
                    context['new_rooms'] = [result[key] for key in key_list]
                    return render_to_response(self.baseDir()+'classroom_import.html', request, (prog, tl), context)
                else:
                    extra = 'classroom'

        elif extra == 'equipment':
            if request.GET.has_key('op') and request.GET['op'] == 'edit':
                #   pre-fill form
                equip = Resource.objects.get(id=request.GET['id'])
                context['equipment_form'] = EquipmentForm(self.program)
                context['equipment_form'].load_equipment(self.program, equip)
                
            if request.GET.has_key('op') and request.GET['op'] == 'delete':
                #   show delete confirmation page
                context['prog'] = self.program
                context['equipment'] = Resource.objects.get(id=request.GET['id'])
                return render_to_response(self.baseDir()+'equipment_delete.html', request, (prog, tl), context)
                
            if request.method == 'POST':
                data = request.POST
                
                if data['command'] == 'reallyremove':
                    #   delete this resource for all time blocks within the program
                    rl = Resource.objects.get(id=data['id']).identical_resources().filter(event__anchor=self.program_anchor_cached())
                    for r in rl:
                        r.delete()
                    
                elif data['command'] == 'addedit':
                    #   add/edit restype
                    form = EquipmentForm(self.program, data)

                    if form.is_valid():
                        form.save_equipment(self.program)
                    else:
                        context['equipment_form'] = form

        #   Group contiguous blocks of time for the program
        time_options = self.program.getTimeSlots(exclude_types=[])
        time_groups = Event.group_contiguous(list(time_options))

        #   Retrieve remaining context information
        context['timeslots'] = [{'selections': group} for group in time_groups]
        
        if 'timeslot_form' not in context:
            context['timeslot_form'] = TimeslotForm()
        
        context['resource_types'] = self.program.getResourceTypes().exclude(priority_default=0).order_by('priority_default')
        for c in context['resource_types']:
            if c.program is None:
                c.is_global = True
        
        if 'restype_form' not in context:
            context['restype_form'] = ResourceTypeForm()
    
        if 'classroom_form' not in context:
            context['classroom_form'] = ClassroomForm(self.program)
        
        if 'equipment_form' not in context:
            context['equipment_form'] = EquipmentForm(self.program)
        
        if 'import_form' not in context:
            context['import_form'] = ClassroomImportForm()
        
        context['open_section'] = extra
        context['prog'] = self.program
        context['module'] = self

        #   Display default form
        return render_to_response(self.baseDir()+'resource_main.html', request, (prog, tl), context)
    

    class Meta:
        abstract = True

