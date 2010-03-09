from django import forms

from datetime import timedelta

from esp.resources.models import ResourceType, Resource, ResourceAssignment
from esp.cal.models import EventType, Event
from esp.program.models import Program
from esp.utils.widgets import DateTimeWidget

class TimeslotForm(forms.Form):
    id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    name = forms.CharField(help_text='Approximate time block (i.e. "Sat 9 - 10 AM")')
    description = forms.CharField(required=False, widget=forms.Textarea, help_text='Include the exact times here (i.e. "First class period: Sat 9:05 - 9:55 AM)"')
    start = forms.DateTimeField(label='Start Time', help_text='Format: YYYY-MM-DD HH:MM:SS <br />Example: 2007-10-14 14:00:00', widget=DateTimeWidget)
    hours = forms.IntegerField(widget=forms.TextInput(attrs={'size':'6'}))
    minutes = forms.IntegerField(widget=forms.TextInput(attrs={'size':'6'}))
    
    def load_timeslot(self, slot):
        self.fields['name'].initial = slot.short_description
        self.fields['description'].initial = slot.description
        self.fields['start'].initial = slot.start
        self.fields['id'].initial = slot.id
        length = (slot.end - slot.start).seconds
        self.fields['hours'].initial = int(length / 3600)
        self.fields['minutes'].initial = int(length / 60 - 60 * self.fields['hours'].initial)
        
    def save_timeslot(self, program, slot):
        slot.short_description = self.cleaned_data['name']
        slot.description = self.cleaned_data['description']
        slot.start = self.cleaned_data['start']
        slot.end = slot.start + timedelta(hours=self.cleaned_data['hours'], minutes=self.cleaned_data['minutes'])
        slot.event_type = EventType.objects.all()[0]    # default event type for now
        slot.anchor = program.anchor
        slot.save()
       

class ResourceTypeForm(forms.Form):
    id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    name = forms.CharField()
    description = forms.CharField(required=False,widget=forms.Textarea)
    priority = forms.IntegerField(required=False, help_text='Assign this a unique number in relation to the priority of other resource types')
    is_global = forms.BooleanField(label='Global?', required=False)
        
    def load_restype(self, res_type):
        self.fields['name'].initial = res_type.name
        self.fields['description'].initial = res_type.description
        self.fields['priority'].initial = res_type.priority_default
        self.fields['is_global'].initial = (res_type.program == None)
        self.fields['id'].initial = res_type.id
        
    def save_restype(self, program, res_type):
        res_type.name = self.cleaned_data['name']
        res_type.description  = self.cleaned_data['description']
        if self.cleaned_data['is_global']:
            res_type.program = None
        else:
            res_type.program = program
        res_type.priority_default = self.cleaned_data['priority']
        res_type.save()
        
       
def setup_furnishings(restype_list):
    #   Populate the available choices for furnishings based on a particular program.
    return ((str(r.id), r.name) for r in restype_list) 
    
def setup_timeslots(program):
    return ((str(e.id), e.short_description) for e in program.getTimeSlots())
       
       
class EquipmentForm(forms.Form):
    id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    name = forms.CharField()
    times_available = forms.MultipleChoiceField()
    resource_type = forms.ChoiceField()
    
    def __init__(self, *args, **kwargs):
        if isinstance(args[0], Program):
            self.base_fields['resource_type'].choices = setup_furnishings(args[0].getResourceTypes())
            self.base_fields['times_available'].choices = setup_timeslots(args[0])
            super(EquipmentForm, self).__init__(*args[1:], **kwargs)
        else:
            super(EquipmentForm, self).__init__(*args, **kwargs)
            
    def load_equipment(self, program, resource):
        self.fields['id'].initial = resource.id
        self.fields['name'].initial = resource.name
        self.fields['times_available'].initial = [mt.short_description for mt in resource.matching_times()]
        self.fields['resource_type'].initial = resource.res_type.name
        
    def save_equipment(self, program):
        initial_resources = list(Resource.objects.filter(name=self.cleaned_data['name'], event__anchor=program.anchor))
        new_timeslots = [Event.objects.get(id=int(id_str)) for id_str in self.cleaned_data['times_available']]
        new_restype = ResourceType.objects.get(id=int(self.cleaned_data['resource_type'][0]))
        
        for t in new_timeslots:
            new_res = Resource()
            new_res.res_type = new_restype
            new_res.event = t
            new_res.name = self.cleaned_data['name']
            new_res.save()
            
        for r in initial_resources:
            r.delete()
          
class ClassroomForm(forms.Form):
    id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    orig_room_number = forms.CharField(widget=forms.HiddenInput)
    room_number = forms.CharField(widget=forms.TextInput(attrs={'size':'15'}))
    furnishings = forms.MultipleChoiceField(required=False)
    times_available = forms.MultipleChoiceField()
    num_students = forms.IntegerField(widget=forms.TextInput(attrs={'size':'6'}))
       
    def __init__(self, *args, **kwargs):
        
        if isinstance(args[0], Program):
            self.base_fields['furnishings'].choices = setup_furnishings(args[0].getResourceTypes())
            self.base_fields['times_available'].choices = setup_timeslots(args[0])
            super(ClassroomForm, self).__init__(*args[1:], **kwargs)
        else:
            super(ClassroomForm, self).__init__(*args, **kwargs)
    

    
    #   The next two functions are interesting because there is not a simple one to one
    #   relationship between the form and the classroom (Resource).  Instead, the form
    #   creates a list of grouped resources for the classroom and copies each resource for
    #   the different timeslots that it is available for.
    def load_classroom(self, program, room):
        self.fields['id'].initial = room.id
        self.fields['orig_room_number'].initial = room.name
        self.fields['room_number'].initial = room.name
        self.fields['num_students'].initial = room.num_students
        self.fields['times_available'].initial = [mt.id for mt in room.matching_times()]
        self.fields['furnishings'].initial = [f.res_type.id for f in room.associated_resources()]
        
    def save_classroom(self, program):
        """ Steps for saving a classroom:
        -   Find the previous list of resources
        -   Create a new list of resources
        -   Move over resource assignments
        -   Delete old resources
        """

        orig_room_number = self.cleaned_data['orig_room_number']
        if orig_room_number == "":
            orig_room_number = self.cleaned_data['room_number']

        initial_rooms = program.getClassrooms().filter(name=orig_room_number).distinct()
        initial_furnishings = {}
        for r in initial_rooms:
            initial_furnishings[r] = list(r.associated_resources())
        
        timeslots = Event.objects.filter(id__in=[int(id_str) for id_str in self.cleaned_data['times_available']])
        furnishings = ResourceType.objects.filter(id__in=[int(id_str) for id_str in self.cleaned_data['furnishings']])

        rooms_to_keep = list(initial_rooms.filter(event__in=timeslots))
        rooms_to_delete = list(initial_rooms.exclude(event__in=timeslots))

        new_timeslots = timeslots.exclude(id__in=[x.event_id for x in rooms_to_keep])
        
        #   Make up new rooms specified by the form
        for t in new_timeslots:
            #   Create room
            new_room = Resource()
            new_room.num_students = self.cleaned_data['num_students']
            new_room.event = t
            new_room.res_type = ResourceType.get_or_create('Classroom')
            new_room.name = self.cleaned_data['room_number']
            new_room.save()
            t.new_room = new_room
            
            for f in furnishings:
                #   Create associated resource
                new_resource = Resource()
                new_resource.event = t
                new_resource.res_type = f
                new_resource.name = f.name + ' for ' + self.cleaned_data['room_number']
                new_resource.group_id = new_room.group_id
                new_resource.save()
                f.new_resource = new_resource
                
                
        #   Delete old, no-longer-valid resources
        for rm in rooms_to_delete:
            #   Find assignments pertaining to the old room
            ra_room = rm.assignments()
            for ra in ra_room:
                if ra.resource.event in new_timeslots:
                    ra.resource = timeslots[new_timeslots.index(ra.resource.event)].new_room
                    ra.save()

            #   Delete old resources... associated resources, then the room itself
            for f in initial_furnishings[rm]:
                f.delete()
            rm.delete()

        
        #   Sync existing rooms
        for room in rooms_to_keep:
            room.num_students = self.cleaned_data['num_students']
            room.name = self.cleaned_data['room_number']
            room.save()
            
            # Add furnishings that we didn't have before
            for f in furnishings.exclude(resource__group_id=room.group_id):
                #   Create associated resource
                new_resource = Resource()
                new_resource.event = room.event
                new_resource.res_type = f
                new_resource.name = f.name + ' for ' + self.cleaned_data['room_number']
                new_resource.group_id = room.group_id
                new_resource.save()
                f.new_resource = new_resource

            # Delete furnishings that we don't have any more
            for f in Resource.objects.filter(group_id=room.group_id).exclude(id=room.id).exclude(res_type__in=furnishings):
                f.delete()
