
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

import json

from django.contrib.auth.decorators import login_required
from django.forms import formset_factory
from django.http import HttpResponseBadRequest, HttpResponse
from django.template.loader import render_to_string

from esp.utils.web import render_to_response
from esp.utils.decorators import json_response

from esp.cal.models import Event
from esp.tagdict.models import Tag
from esp.resources.models import ResourceType, Resource, ResourceAssignment
from esp.program.models import ClassSubject, ClassSection, Program
from esp.users.models import ESPUser
from esp.middleware import ESPError

from esp.program.modules.base import ProgramModuleObj, needs_admin, usercheck_usetl, main_call, aux_call
from esp.program.modules import module_ext

from esp.program.modules.forms.resources import ClassroomForm, TimeslotForm, ResourceTypeForm, ResourceChoiceForm, EquipmentForm, FurnishingFormForProgram, ClassroomImportForm, TimeslotImportForm, ResTypeImportForm, EquipmentImportForm

from esp.program.controllers.resources import ResourceController

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
            "seq": 10,
            "choosable": 1,
            }

    """
    Resource module handler functions

    Each returns a tuple (response, context).  Typically the response is None, in which
    case we have performed the desired operations and rendering can continue.  If the
    response is not None, it should be returned (e.g.to display a confirmation page).
    """
    def resources_timeslot(self, request, tl, one, two, module, extra, prog):
        context = {}
        response = None

        controller = ResourceController(prog)

        if request.GET.get('op') == 'edit':
            #   pre-fill form
            current_slot = Event.objects.get(id=request.GET['id'])
            context['timeslot_form'] = TimeslotForm()
            context['timeslot_form'].load_timeslot(current_slot)

        if request.GET.get('op') == 'delete':
            #   show delete confirmation page
            context['prog'] = self.program
            context['timeslot'] = Event.objects.get(id=request.GET['id'])
            response = render_to_response(self.baseDir()+'timeslot_delete.html', request, context)

        if request.method == 'POST':
            data = request.POST

            if data['command'] == 'reallyremove':
                controller.delete_timeslot(data['id'])

            elif data['command'] == 'addedit':
                #   add/edit timeslot
                form = TimeslotForm(data)
                if form.is_valid():
                    controller.add_or_edit_timeslot(form)
                else:
                    context['timeslot_form'] = form

        return (response, context)

    def resources_restype(self, request, tl, one, two, module, extra, prog):
        context = {}
        response = None

        controller = ResourceController(prog)

        if request.GET.get('op') == 'edit':
            #   pre-fill form
            current_slot = ResourceType.objects.get(id=request.GET['id'])
            context['restype_form'] = ResourceTypeForm()
            context['restype_form'].load_restype(current_slot)
            choices = [{'choice': choice} for choice in current_slot.choices]
            ResourceChoiceSet = formset_factory(ResourceChoiceForm, max_num = 10, extra = 0 if len(choices) else 1)
            context['reschoice_formset'] = ResourceChoiceSet(initial=choices, prefix='resourcechoices')

        if request.GET.get('op') == 'delete':
            #   show delete confirmation page
            context['prog'] = self.program
            context['restype'] = ResourceType.objects.get(id=request.GET['id'])
            response = render_to_response(self.baseDir()+'restype_delete.html', request, context)

        if request.method == 'POST':
            data = request.POST

            if data['command'] == 'reallyremove':
                controller.delete_restype(data['id'])

            elif data['command'] == 'addedit':
                #   add/edit restype
                form = ResourceTypeForm(data)
                num_choices = int(data.get('resourcechoices-TOTAL_FORMS', '0'))
                ResourceChoiceSet = formset_factory(ResourceChoiceForm, max_num = 10, extra = 0 if num_choices else 1)
                choices, choices_list = [],[]
                for i in range(0,num_choices):
                    choice = data['resourcechoices-'+str(i)+'-choice']
                    choices.append({'choice': choice})
                    choices_list.append(choice)
                context['reschoice_formset'] = ResourceChoiceSet(initial=choices, prefix='resourcechoices')
                if form.is_valid():
                    controller.add_or_edit_restype(form, choices_list)
                else:
                    context['restype_form'] = form

        return (response, context)

    def resources_classroom(self, request, tl, one, two, module, extra, prog):
        context = {}
        response = None

        controller = ResourceController(prog)

        if request.GET.get('op') == 'edit':
            #   pre-fill form
            current_room = Resource.objects.get(id=request.GET['id'])
            context['classroom_form'] = ClassroomForm(self.program)
            context['classroom_form'].load_classroom(self.program, current_room)
            furnishings = [{'furnishing': furnishing.res_type.id, 'choice': furnishing.attribute_value} for furnishing in current_room.associated_resources()]
            FurnishingFormSet = formset_factory(FurnishingFormForProgram(prog), max_num = 1000, extra = 0)
            context['furnishing_formset'] = FurnishingFormSet(initial=furnishings, prefix='furnishings')

        if request.GET.get('op') == 'delete':
            #   show delete confirmation page
            context['prog'] = self.program
            context['classroom'] = Resource.objects.get(id=request.GET['id'])
            resources = self.program.getClassrooms().filter(name=context['classroom'].name)
            context['timeslots'] = [r.event for r in resources]
            sections = ClassSection.objects.filter(resourceassignment__resource__id__in=resources.values_list('id', flat=True)).distinct()

            context['sections'] = sections
            response = render_to_response(self.baseDir()+'classroom_delete.html', request, context)

        if request.method == 'POST':
            data = request.POST

            if data['command'] == 'reallyremove':
                controller.delete_classroom(data['id'])

            elif data['command'] == 'addedit':
                form = ClassroomForm(self.program, data)
                num_forms = int(data.get('furnishings-TOTAL_FORMS', '0'))
                FurnishingFormSet = formset_factory(FurnishingFormForProgram(prog), max_num = 1000, extra = 0)
                furnishings = []
                for i in range(0,num_forms):
                    #   Filter out blank furnishings or choices
                    if 'furnishings-'+str(i)+'-furnishing' in data:
                        furnishing = data['furnishings-'+str(i)+'-furnishing']
                        if 'furnishings-'+str(i)+'-choice' in data:
                            choice = data['furnishings-'+str(i)+'-choice']
                        else:
                            choice = ''
                        furnishings.append({'furnishing': furnishing, 'choice': choice})
                #   Filter out duplicates
                furnishings = list(map(dict, frozenset(frozenset(i.items()) for i in furnishings)))
                if form.is_valid():
                    controller.add_or_edit_classroom(form, furnishings)
                else:
                    context['classroom_form'] = form
                    context['furnishing_formset'] = FurnishingFormSet(initial=furnishings, prefix='furnishings')

        return (response, context)

    def resources_timeslot_import(self, request, tl, one, two, module, extra, prog):
        context = {}
        response = None

        import_mode = 'preview'
        to_import = []
        if 'import_confirm' in request.POST and request.POST['import_confirm'] == 'yes':
            import_mode = 'save'
            to_import = request.POST.getlist('to_import')

        import_form = TimeslotImportForm(request.POST, cur_prog = prog)
        if not import_form.is_valid():
            context['import_timeslot_form'] = import_form
        else:
            past_program = import_form.cleaned_data['program']
            start_date = import_form.cleaned_data['start_date']

            if past_program == prog:
                raise ESPError("You're trying to import timeslots from a program"
                               " to itself! Try a different program instead.",
                               log=False)

            #   Figure out timeslot dates
            new_timeslots = []
            prev_timeslots = past_program.getTimeSlots().order_by('start')
            time_delta = start_date - prev_timeslots[0].start.date()
            for orig_timeslot in prev_timeslots:
                new_timeslot = Event(
                    program = self.program,
                    event_type = orig_timeslot.event_type,
                    short_description = orig_timeslot.short_description,
                    description = orig_timeslot.description,
                    priority = orig_timeslot.priority,
                    start = orig_timeslot.start + time_delta,
                    end   = orig_timeslot.end + time_delta,
                )
                #   Save the new timeslot only if it doesn't duplicate an existing one
                if import_mode == 'save' and not Event.objects.filter(program=new_timeslot.program, start=new_timeslot.start, end=new_timeslot.end).exists() and str(orig_timeslot.id) in to_import:
                    new_timeslot.save()
                else:
                    new_timeslot.old_id = orig_timeslot.id
                new_timeslots.append(new_timeslot)

            #   Render a preview page showing the resources for the previous program if desired
            context['past_program'] = past_program
            context['start_date'] = start_date.strftime('%m/%d/%Y')
            context['new_timeslots'] = new_timeslots
            if import_mode == 'preview':
                context['prog'] = self.program
                response = render_to_response(self.baseDir()+'timeslot_import.html', request, context)
            else:
                extra = 'timeslot'

        return (response, context)

    def resources_restype_import(self, request, tl, one, two, module, extra, prog):
        context = {}
        response = None

        import_mode = 'preview'
        to_import = []
        if 'import_confirm' in request.POST and request.POST['import_confirm'] == 'yes':
            import_mode = 'save'
            to_import = request.POST.getlist('to_import')

        import_form = ResTypeImportForm(request.POST, cur_prog = prog)
        if not import_form.is_valid():
            context['import_restype_form'] = import_form
        else:
            past_program = import_form.cleaned_data['program']
            res_type_list = []
            res_types = ResourceType.objects.filter(program = past_program)
            for res_type in res_types:
                #   Create new ResourceType in case it doesn't exist yet
                new_res_type = ResourceType(
                    name = res_type.name,
                    description = res_type.description,
                    consumable = res_type.consumable,
                    priority_default = res_type.priority_default,
                    only_one = res_type.only_one,
                    attributes_pickled = res_type.attributes_pickled,
                    program = self.program,
                    autocreated = res_type.autocreated,
                    hidden = res_type.hidden
                )
                if import_mode == 'save' and not ResourceType.objects.filter(name=new_res_type.name, description = new_res_type.description, program = self.program).exists() and str(res_type.id) in to_import:
                    new_res_type.save()
                else:
                    new_res_type.old_id = res_type.id
                res_type_list.append(new_res_type)
            context['past_program'] = past_program
            if import_mode == 'preview':
                context['prog'] = self.program
                context['new_restypes'] = sorted(res_type_list, key = lambda x: (not x.hidden, x.priority_default), reverse = True)
                response = render_to_response(self.baseDir()+'restype_import.html', request, context)
            else:
                extra = 'restype'

        return (response, context)

    def resources_classroom_import(self, request, tl, one, two, module, extra, prog):
        context = {}
        response = None

        import_mode = 'preview'
        to_import = []
        if 'import_confirm' in request.POST and request.POST['import_confirm'] == 'yes':
            import_mode = 'save'
            to_import = request.POST.getlist('to_import')

        import_form = ClassroomImportForm(request.POST, cur_prog = prog)
        if not import_form.is_valid():
            context['import_classroom_form'] = import_form
        else:
            past_program = import_form.cleaned_data['program']
            complete_availability = import_form.cleaned_data['complete_availability']
            import_furnishings = import_form.cleaned_data['import_furnishings']

            resource_list = []
            furnishing_dict = {}
            if complete_availability:
                #   Make classrooms available at all of the new program's timeslots
                for resource in past_program.groupedClassrooms():
                    furnishing_dict[resource.name] = set()
                    for timeslot in self.program.getTimeSlots():
                        new_res = Resource(
                            name = resource.name,
                            res_type = resource.res_type,
                            num_students = resource.num_students,
                            is_unique = resource.is_unique,
                            user = resource.user,
                            event = timeslot
                        )
                        if import_mode == 'save' and not Resource.objects.filter(name=new_res.name, event=new_res.event).exists() and str(resource.id) in to_import:
                            new_res.save()
                        else:
                            new_res.old_id = resource.id
                        if import_furnishings:
                            new_furns = self.furnishings_import(resource, new_res, self.program, import_mode, to_import)
                            furnishing_dict[resource.name].update(new_furn.res_type.name + (" (Hidden)" if new_furn.res_type.hidden else "") + ((": " + new_furn.attribute_value) if new_furn.attribute_value else "") for new_furn in new_furns)
                        resource_list.append(new_res)
            else:
                #   Attempt to match timeslots for the programs
                ts_old = past_program.getTimeSlots().filter(event_type__description__icontains='class').order_by('start')
                ts_new = self.program.getTimeSlots().filter(event_type__description__icontains='class').order_by('start')
                ts_map = {}
                for i in range(min(len(ts_old), len(ts_new))):
                    ts_map[ts_old[i].id] = ts_new[i]

                #   Iterate over the classrooms in the previous program
                for resource in past_program.groupedClassrooms():
                    furnishing_dict[resource.name] = set()
                    for event in resource.timegroup:
                        #   If we know what timeslot to put it in, make a copy
                        if event.id in ts_map:
                            new_res = Resource(
                                name = resource.name,
                                res_type = resource.res_type,
                                num_students = resource.num_students,
                                is_unique = resource.is_unique,
                                user = resource.user,
                                event = ts_map[event.id]
                            )
                            #   Check to avoid duplicating rooms (so the process is idempotent)
                            if import_mode == 'save' and not Resource.objects.filter(name=new_res.name, event=new_res.event).exists() and str(resource.id) in to_import:
                                new_res.save()
                            else:
                                new_res.old_id = resource.id
                            if import_furnishings:
                                new_furns = self.furnishings_import(resource, new_res, self.program, import_mode, to_import)
                                furnishing_dict[resource.name].update(new_furn.res_type.name + (" (Hidden)" if new_furn.res_type.hidden else "") + ((": " + new_furn.attribute_value) if new_furn.attribute_value else "") for new_furn in new_furns)
                            resource_list.append(new_res)

            #   Render a preview page showing the resources for the previous program if desired
            context['past_program'] = past_program
            context['complete_availability'] = complete_availability
            context['import_furnishings'] = import_furnishings
            if import_mode == 'preview':
                context['prog'] = self.program
                result = self.program.collapsed_dict(resource_list)
                key_list = result.keys()
                key_list.sort()
                new_rooms = []
                for key in key_list:
                    room = result[key]
                    room.furnishings = furnishing_dict[room.name]
                    new_rooms.append(room)
                context['new_rooms'] = new_rooms
                response = render_to_response(self.baseDir()+'classroom_import.html', request, context)
            else:
                extra = 'classroom'

        return (response, context)

    @staticmethod
    def furnishings_import(old_res, new_res, prog, import_mode, to_import):
        furnishings = old_res.associated_resources()
        new_furnishings = []
        for f in furnishings:
            res_type = f.res_type
            #   Create new ResourceType in case it doesn't exist yet
            res_types = ResourceType.objects.filter(name=res_type.name, program = prog)
            if res_types.exists():
                new_res_type = res_types[0]
            else:
                new_res_type = ResourceType(
                    name = res_type.name,
                    description = res_type.description,
                    consumable = res_type.consumable,
                    priority_default = res_type.priority_default,
                    only_one = res_type.only_one,
                    attributes_pickled = res_type.attributes_pickled,
                    program = prog,
                    autocreated = res_type.autocreated,
                    hidden = res_type.hidden
                )
            if import_mode == 'save':
                new_res_type.save()
            #   Create associated furnishing
            new_furnishing = Resource(
                event = new_res.event,
                res_type = new_res_type,
                name = f.name,
                #   Classrooms only have assigned res_groups once they have been saved
                res_group = new_res.res_group,
                attribute_value = f.attribute_value
            )
            if import_mode == 'save' and not Resource.objects.filter(name=new_furnishing.name, event=new_res.event, attribute_value=new_furnishing.attribute_value).exists() and str(old_res.id) in to_import:
                new_furnishing.save()
            new_furnishings.append(new_furnishing)
        return new_furnishings

    def resources_equipment(self, request, tl, one, two, module, extra, prog):
        context = {}
        response = None

        controller = ResourceController(prog)

        if request.GET.get('op') == 'edit':
            #   pre-fill form
            equip = Resource.objects.get(id=request.GET['id'])
            context['equipment_form'] = EquipmentForm(self.program)
            context['equipment_form'].load_equipment(self.program, equip)

        if request.GET.get('op') == 'delete':
            #   show delete confirmation page
            context['prog'] = self.program
            context['equipment'] = Resource.objects.get(id=request.GET['id'])
            response = render_to_response(self.baseDir()+'equipment_delete.html', request, context)

        if request.method == 'POST':
            data = request.POST

            if data['command'] == 'reallyremove':
                controller.delete_equipment(data['id'])

            elif data['command'] == 'addedit':
                #   add/edit restype
                form = EquipmentForm(self.program, data)

                if form.is_valid():
                    form.save_equipment(self.program)
                else:
                    context['equipment_form'] = form

        return (response, context)

    def resources_equipment_import(self, request, tl, one, two, module, extra, prog):
        context = {}
        response = None

        import_mode = 'preview'
        to_import = []
        if 'import_confirm' in request.POST and request.POST['import_confirm'] == 'yes':
            import_mode = 'save'
            to_import = request.POST.getlist('to_import')

        import_form = EquipmentImportForm(request.POST, cur_prog = prog)
        if not import_form.is_valid():
            context['import_equipment_form'] = import_form
        else:
            past_program = import_form.cleaned_data['program']
            complete_availability = import_form.cleaned_data['complete_availability']

            new_equipment_list = []
            if complete_availability:
                #   Make floating resources available at all of the new program's timeslots
                for equipment in past_program.getFloatingResources():
                    res_type = equipment.res_type
                    for timeslot in self.program.getTimeSlots():
                        res_types = ResourceType.objects.filter(name=res_type.name, program = self.program)
                        if res_types.exists():
                            new_res_type = res_types[0]
                        else:
                            new_res_type = ResourceType(
                                name = res_type.name,
                                description = res_type.description,
                                consumable = res_type.consumable,
                                priority_default = res_type.priority_default,
                                only_one = res_type.only_one,
                                attributes_pickled = res_type.attributes_pickled,
                                program = self.program,
                                autocreated = res_type.autocreated,
                                hidden = res_type.hidden
                            )
                        if import_mode == 'save':
                            new_res_type.save()
                        new_equip = Resource(
                            name = equipment.name,
                            res_type = new_res_type,
                            user = equipment.user,
                            event = timeslot
                        )
                        if import_mode == 'save' and not Resource.objects.filter(name=new_equip.name, event=new_equip.event).exists() and str(equipment.id) in to_import:
                            new_equip.save()
                        else:
                            new_equip.old_id = equipment.id
                        new_equipment_list.append(new_equip)
            else:
                #   Attempt to match timeslots for the programs
                ts_old = past_program.getTimeSlots().filter(event_type__description__icontains='class').order_by('start')
                ts_new = self.program.getTimeSlots().filter(event_type__description__icontains='class').order_by('start')
                ts_map = {}
                for i in range(min(len(ts_old), len(ts_new))):
                    ts_map[ts_old[i].id] = ts_new[i]

                #   Iterate over the floating resources in the previous program
                for equipment in past_program.getFloatingResources():
                    res_type = equipment.res_type
                    res_types = ResourceType.objects.filter(name=res_type.name, program = self.program)
                    if res_types.exists():
                        new_res_type = res_types[0]
                    else:
                        new_res_type = ResourceType(
                            name = res_type.name,
                            description = res_type.description,
                            consumable = res_type.consumable,
                            priority_default = res_type.priority_default,
                            only_one = res_type.only_one,
                            attributes_pickled = res_type.attributes_pickled,
                            program = self.program,
                            autocreated = res_type.autocreated,
                            hidden = res_type.hidden
                        )
                    if import_mode == 'save' and str(equipment.id) in to_import:
                        new_res_type.save()
                    for event in equipment.timegroup:
                        #   If we know what timeslot to put it in, make a copy
                        if event.id in ts_map:
                            new_equip = Resource(
                                name = equipment.name,
                                res_type = new_res_type,
                                user = equipment.user,
                                event = ts_map[event.id],
                                attribute_value = equipment.attribute_value
                            )
                            if import_mode == 'save' and not Resource.objects.filter(name=new_equip.name, event=new_equip.event).exists() and str(equipment.id) in to_import:
                                new_equip.save()
                            else:
                                new_equip.old_id = equipment.id
                            new_equipment_list.append(new_equip)

            context['past_program'] = past_program
            context['complete_availability'] = complete_availability
            if import_mode == 'preview':
                context['prog'] = self.program
                result = self.program.collapsed_dict(new_equipment_list)
                context['new_equipment'] = [result[key] for key in sorted(result.iterkeys())]
                response = render_to_response(self.baseDir()+'equipment_import.html', request, context)
            else:
                extra = 'equipment'

        return(response, context)

    @aux_call
    @json_response(None)
    @needs_admin
    def ajaxfurnishingchoices(self, request, tl, one, two, module, extra, prog):
        """
        POST to this view to get the choices for a particular furnishing.
         POST data:
          'furnishing':     The ID of the furnishing of interest.
        """
        if 'furnishing' in request.POST:
            res_type = ResourceType.objects.get(id = int(request.POST['furnishing']))
            return {'choices': res_type.choices}

    @main_call
    @needs_admin
    def resources(self, request, tl, one, two, module, extra, prog):
        """ Main view for the resource module.
            Besides displaying resource information, the 'extra' slug at the
            end of the URL selects which aspect of resources to perform
            more detailed operations on.
        """

        #   First, run the handler specified at the end of the URL.
        #   (The handler specifies which type of model we are working with.)
        handlers = {
            'timeslot': self.resources_timeslot,
            'restype': self.resources_restype,
            'classroom': self.resources_classroom,
            'timeslot_import': self.resources_timeslot_import,
            'restype_import': self.resources_restype_import,
            'classroom_import': self.resources_classroom_import,
            'equipment': self.resources_equipment,
            'equipment_import': self.resources_equipment_import
        }
        if extra in handlers:
            (response, context) = handlers[extra](request, tl, one, two, module, extra, prog)
        else:
            response = None
            context = {}

        #   Display the immediate response (e.g. a confirmation page) if the handler provided one
        if response:
            return response

        #   Group contiguous blocks of time for the program
        time_options = self.program.getTimeSlots(types=['Class Time Block','Open Class Time Block'])
        time_groups = Event.group_contiguous(list(time_options))

        #   Retrieve remaining context information
        context['timeslots'] = [{'selections': group} for group in time_groups]

        if 'timeslot_form' not in context:
            context['timeslot_form'] = TimeslotForm()

        res_types = self.program.getResourceTypes(include_global=Tag.getBooleanTag('allow_global_restypes'))
        context['resource_types'] = sorted(res_types, key = lambda x: (not x.hidden, x.priority_default), reverse = True)
        for c in context['resource_types']:
            if c.program is None:
                c.is_global = True

        if 'restype_form' not in context:
            ResourceChoiceSet = formset_factory(ResourceChoiceForm, max_num = 10)
            context['reschoice_formset'] = ResourceChoiceSet(prefix='resourcechoices')
            context['restype_form'] = ResourceTypeForm()

        if 'classroom_form' not in context:
            FurnishingFormSet = formset_factory(FurnishingFormForProgram(prog), max_num = 1000, extra = 0)
            context['furnishing_formset'] = FurnishingFormSet(prefix='furnishings')
            context['classroom_form'] = ClassroomForm(self.program)

        if 'equipment_form' not in context:
            context['equipment_form'] = EquipmentForm(self.program)

        if 'import_classroom_form' not in context:
            context['import_classroom_form'] = ClassroomImportForm(cur_prog = prog)

        if 'import_timeslot_form' not in context:
            context['import_timeslot_form'] = TimeslotImportForm(cur_prog = prog)

        if 'import_restype_form' not in context:
            context['import_restype_form'] = ResTypeImportForm(cur_prog = prog)

        if 'import_equipment_form' not in context:
            context['import_equipment_form'] = EquipmentImportForm(cur_prog = prog)

        context['open_section'] = extra
        context['prog'] = self.program
        context['module'] = self

        #   Display default form
        return render_to_response(self.baseDir()+'resource_main.html', request, context)

    @aux_call
    @needs_admin
    def newassignment(self, request, tl, one, two, module, extra, prog):
        '''Create a resource assignment from the POST data, and return its detail display.'''
        if request.method != 'POST' or 'resource' not in request.POST or 'target' not in request.POST:
            return HttpResponseBadRequest('')
        results = ClassSection.objects.filter(id=request.POST['target'])
        if not len(results): #Use len() since we will evaluate it anyway
            return HttpResponseBadRequest('')
        section = results[0]
        res_name = request.POST['resource']
        res_list = []
        for ts in section.meeting_times.all():
            avail_res = [res for res in prog.getAvailableResources(ts, queryset=True) if res.name==res_name]
            if not len(avail_res):
                return HttpResponseBadRequest('')
            res_list.append(avail_res[0])
        group = None
        for res in res_list:
            assignment = res.assign_to_section(section, group = group)
            if group is None:
                group = assignment.assignment_group
        context = { 'assignment' : assignment }
        response = json.dumps({
            'assignment_name': render_to_string(self.baseDir()+'assignment_name.html', context = context, request = request),
        })
        return HttpResponse(response, content_type='application/json')

    @aux_call
    @needs_admin
    def editassignment(self, request, tl, one, two, module, extra, prog):
        '''Given a post request, take extra as the id of the resource assignment, update whether it's returned using the post data, and return its new name display.'''
        if request.method != 'POST' or 'id' not in request.POST or 'returned' not in request.POST:
            return HttpResponseBadRequest('')
        results = ResourceAssignment.objects.filter(id=request.POST['id'])
        if not len(results): #Use len() since we will evaluate it anyway
            return HttpResponseBadRequest('')
        assignments = ResourceAssignment.objects.filter(assignment_group = results[0].assignment_group)
        for assignment in assignments:
            assignment.returned = request.POST['returned'] == "true"
            assignment.save()
        context = { 'assignment' : assignment }
        return render_to_response(self.baseDir()+'assignment_name.html', request, context)

    @aux_call
    @needs_admin
    def getavailableequipment(self, request, tl, one, two, module, extra, prog):
        if request.method != 'POST' or 'secid' not in request.POST:
            return HttpResponseBadRequest('')
        results = ClassSection.objects.filter(id=request.POST['secid'])
        if not len(results): #Use len() since we will evaluate it anyway
            return HttpResponseBadRequest('')
        section = results[0]
        ts_res_list = []
        # filter to only resources available for all timeslots for specified section
        for ts in section.meeting_times.all():
            ts_res_list.append([res.name for res in prog.getAvailableResources(ts, queryset=True)])
        resource_list = set.intersection(*[set(x) for x in ts_res_list])
        # Maybe include number remaining of each available resource?
        response = json.dumps({res:res for res in resource_list})
        return HttpResponse(response, content_type='application/json')

    @aux_call
    @needs_admin
    def deleteassignment(self, request, tl, one, two, module, extra, prog):
        '''Given a post request with the ID, delete the resource assignment.'''
        if request.method != 'POST' or 'id' not in request.POST:
            return HttpResponseBadRequest('')
        results = ResourceAssignment.objects.filter(id=request.POST['id'])
        if not len(results): #Use len() since we will evaluate it anyway
            return HttpResponseBadRequest('')
        ResourceAssignment.objects.filter(assignment_group = results[0].assignment_group).delete()
        return HttpResponse('')

    class Meta:
        proxy = True
        app_label = 'modules'
