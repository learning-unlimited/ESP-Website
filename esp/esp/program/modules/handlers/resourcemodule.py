
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

from django.contrib.auth.decorators import login_required

from esp.web.util        import render_to_response

from esp.cal.models import Event
from esp.resources.models import ResourceType, Resource
from esp.program.models import ClassSubject, ClassSection, Program
from esp.users.models import UserBit, ESPUser
from esp.middleware import ESPError

from esp.program.modules.base import ProgramModuleObj, needs_admin, usercheck_usetl, main_call, aux_call
from esp.program.modules import module_ext

from esp.program.modules.forms.resources import ClassroomForm, TimeslotForm, ResourceTypeForm, EquipmentForm

class ResourceModule(ProgramModuleObj):
    doc = """ Manage the resources used by a program.  This includes classrooms and LCD equipment.
    Also use this module to set up the time blocks for classes.
    """
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Manage Times and Rooms",
            "module_type": "manage",
            "seq": 10
            }

    @main_call
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
                data = request.POST.copy()
                
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
                data = request.POST.copy()
                
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
                return render_to_response(self.baseDir()+'classroom_delete.html', request, (prog, tl), context)
                
            if request.method == 'POST':
                data = request.POST.copy()
                self.program.clear_classroom_cache()
                
                if data['command'] == 'reallyremove':
                    #   delete classroom and associated resources
                    raise ESPError(), 'Sorry, deletion of classrooms creates problems with the existing resources assignments, so it is not yet enabled.  Please contact the webmasters to delete a classroom.'
                    
                elif data['command'] == 'addedit':
                    #   add/edit restype
                    form = ClassroomForm(self.program, data)

                    if form.is_valid():
                        form.save_classroom(self.program)
                    else:
                        context['classroom_form'] = form

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
                data = request.POST.copy()
                
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
        time_options = self.program.getTimeSlots()
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
        
        context['open_section'] = extra
        context['prog'] = self.program
        context['module'] = self

        #   Display default form
        return render_to_response(self.baseDir()+'resource_main.html', request, (prog, tl), context)
    
