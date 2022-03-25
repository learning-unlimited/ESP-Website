from django import forms
from django.utils.safestring import mark_safe
from django.db.models import IntegerField, Case, When, Count
from django.core.validators import MinValueValidator

from datetime import timedelta

from esp.resources.models import ResourceType, Resource, ResourceAssignment
from esp.cal.models import EventType, Event
from esp.program.models import Program
from esp.utils.widgets import DateTimeWidget, DateWidget
from esp.tagdict.models import Tag

class TimeslotForm(forms.Form):
    id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    name = forms.CharField(help_text='Approximate time block (e.g. "Sat 9 - 10 AM")')
    description = forms.CharField(required=False, widget=forms.Textarea, help_text='Include the exact times here (e.g. "First class period: Sat 9:05 - 9:55 AM")')
    start = forms.DateTimeField(label='Start Time', help_text=mark_safe('Format: MM/DD/YYYY HH:MM:SS <br />Example: 10/14/2007 14:00:00'), widget=DateTimeWidget)
    hours = forms.IntegerField(widget=forms.TextInput(attrs={'size':'6'}))
    minutes = forms.IntegerField(widget=forms.TextInput(attrs={'size':'6'}))
    openclass = forms.BooleanField(required=False, label='Open Class Time Block', help_text="Check this if the time block should be used for open classes only. If in doubt, don't check this.")

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
        if self.cleaned_data['openclass']:
            slot.event_type = EventType.get_from_desc("Open Class Time Block")
        else:
            slot.event_type = EventType.get_from_desc("Class Time Block")    # default event type for now
        slot.program = program
        slot.save()


class ResourceTypeForm(forms.Form):
    id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    name = forms.CharField()
    description = forms.CharField(required=False,widget=forms.Textarea)
    priority = forms.IntegerField(required=False, help_text='Assign this a unique number in relation to the priority of other resource types')
    only_one = forms.BooleanField(label='Only one?', required=False, help_text='Limit teachers to selecting only one of the options?')
    is_global = forms.BooleanField(label='Global?', required=False, help_text='Should this resource be associated with all programs?')
    hidden = forms.BooleanField(label='Hidden?', required=False, help_text='Should this resource type be hidden during teacher registration?')

    def __init__(self, *args, **kwargs):
        super(ResourceTypeForm, self).__init__(*args, **kwargs)
        if not Tag.getBooleanTag('allow_global_restypes'):
            self.fields['is_global'].widget = forms.HiddenInput()

    def load_restype(self, res_type):
        self.fields['name'].initial = res_type.name
        self.fields['description'].initial = res_type.description
        self.fields['priority'].initial = res_type.priority_default
        self.fields['is_global'].initial = (res_type.program == None)
        self.fields['only_one'].initial = res_type.only_one
        self.fields['hidden'].initial = res_type.hidden
        self.fields['id'].initial = res_type.id

    def save_restype(self, program, res_type, choices = None):
        res_type.name = self.cleaned_data['name']
        res_type.description  = self.cleaned_data['description']
        if self.cleaned_data['is_global']:
            res_type.program = None
        else:
            res_type.program = program
        if self.cleaned_data['only_one']:
            res_type.only_one = self.cleaned_data['only_one']
        else:
            res_type.only_one = False
        if self.cleaned_data['hidden']:
            res_type.hidden = self.cleaned_data['hidden']
        else:
            res_type.hidden = False
        if self.cleaned_data['priority']:
            res_type.priority_default = self.cleaned_data['priority']
        if choices and filter(None, choices):
            res_type.choices = filter(None, choices)
        else:
            """ This is already set by default when making a new resource type,
                but if you remove all of the choices from a pre-existing resource type
                you need to reset the default. Setting attributes_pickled is equivalent to
                setting choices. """
            res_type.attributes_pickled = ResourceType._meta.get_field('attributes_pickled').default

        res_type.save()

class ResourceChoiceForm(forms.Form):
    choice = forms.CharField(required=False, max_length=50, widget=forms.TextInput)


def setup_furnishings(restype_list):
    #   Populate the available choices for furnishings based on a particular program.
    return ((str(r.id), r.name + (" (Hidden)" if r.hidden else "")) for r in restype_list)

def setup_timeslots(program):
    return ((str(e.id), e.short_description) for e in program.getTimeSlots())


class EquipmentForm(forms.Form):
    id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    name = forms.CharField()
    times_available = forms.MultipleChoiceField()
    num_items = forms.IntegerField(label = "Number of unique items", validators=[MinValueValidator(1)])
    resource_type = forms.ChoiceField()
    choice = forms.CharField(label = "Choice (optional)", required=False, max_length=200)

    def __init__(self, *args, **kwargs):
        if isinstance(args[0], Program):
            self.base_fields['resource_type'].choices = tuple([(u'', '(type)')] + list(setup_furnishings(args[0].getResourceTypes())))
            self.base_fields['times_available'].choices = setup_timeslots(args[0])
            super(EquipmentForm, self).__init__(*args[1:], **kwargs)
        else:
            super(EquipmentForm, self).__init__(*args, **kwargs)

    def load_equipment(self, program, resource):
        self.fields['id'].initial = resource.id
        self.fields['name'].initial = resource.name
        self.fields['times_available'].initial = [mt.id for mt in resource.matching_times()]
        self.fields['num_items'].initial = resource.number_duplicates()
        self.fields['resource_type'].initial = resource.res_type.id
        self.fields['choice'].initial = resource.attribute_value

    def save_equipment(self, program):
        initial_resources = list(Resource.objects.filter(name=self.cleaned_data['name'], event__program=program))
        new_timeslots = [Event.objects.get(id=int(id_str)) for id_str in self.cleaned_data['times_available']]
        new_restype = ResourceType.objects.get(id=int(self.cleaned_data['resource_type']))
        num_items = self.cleaned_data['num_items']

        for i in range(0, num_items):
            for t in new_timeslots:
                new_res = Resource()
                new_res.res_type = new_restype
                new_res.event = t
                new_res.name = self.cleaned_data['name']
                new_res.attribute_value = self.cleaned_data['choice']
                new_res.save()

        for r in initial_resources:
            r.delete()

class ClassroomForm(forms.Form):
    id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    orig_room_number = forms.CharField(required=False, widget=forms.HiddenInput)
    room_number = forms.CharField(widget=forms.TextInput(attrs={'size':'15'}))
    times_available = forms.MultipleChoiceField()
    num_students = forms.IntegerField(widget=forms.TextInput(attrs={'size':'6'}))

    def __init__(self, *args, **kwargs):

        if isinstance(args[0], Program):
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

    def save_classroom(self, program, furnishings):
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
                res_type = ResourceType.objects.get(id=int(f['furnishing']))
                new_resource.res_type = res_type
                new_resource.name = res_type.name + ' for ' + self.cleaned_data['room_number']
                new_resource.res_group = new_room.res_group
                new_resource.attribute_value = f['choice']
                new_resource.save()
                res_type.new_resource = new_resource

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
            for f in furnishings:
                res_type = ResourceType.objects.get(id=int(f['furnishing']))
                if Resource.objects.filter(res_type=res_type, res_group=room.res_group, attribute_value=f['choice']).count() == 0:
                    #   Create associated resource
                    new_resource = Resource()
                    new_resource.event = room.event
                    new_resource.res_type = res_type
                    new_resource.name = res_type.name + ' for ' + self.cleaned_data['room_number']
                    new_resource.res_group = room.res_group
                    new_resource.attribute_value = f['choice']
                    new_resource.save()
                    res_type.new_resource = new_resource

            # Delete furnishings that we don't have any more
            for f in initial_furnishings[room]:
                if {'furnishing': str(f.res_type.id), 'choice': f.attribute_value} not in furnishings:
                    f.delete()

# This would be easier in Django 1.9
# https://docs.djangoproject.com/en/1.9/topics/forms/formsets/#passing-custom-parameters-to-formset-forms
def FurnishingFormForProgram(prog):
    class FurnishingForm(forms.Form):
        furnishing = forms.ChoiceField()
        choice = forms.CharField(required=False, max_length=200, widget=forms.TextInput(attrs={'placeholder': '(option)', 'style': 'margin-left: 8px'}))
        def __init__(self, *args, **kwargs):
            furnishings = setup_furnishings(prog.getResourceTypes())
            self.base_fields['furnishing'].choices = tuple([(u'', '(furnishing)')] + list(furnishings))
            super(FurnishingForm, self).__init__(*args, **kwargs)
    return FurnishingForm

class ClassroomImportForm(forms.Form):
    program = forms.ModelChoiceField(queryset=None)
    complete_availability = forms.BooleanField(required=False, help_text='Check this box if you would like the new classrooms to be available at all times during the program, rather than attempting to replicate their availability from the previous program.')
    import_furnishings = forms.BooleanField(required=False, help_text='Check this box if you would like the new classrooms to have the same furnishings as they did for the previous program.')

    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        super(ClassroomImportForm, self).__init__(*args, **kwargs)
        progs = Resource.objects.filter(res_type=ResourceType.get_or_create('Classroom')).values_list('event__program', flat = True).distinct()
        qs = Program.objects.filter(id__in=progs)
        if cur_prog is not None:
            qs = qs.exclude(id=cur_prog.id)
        self.fields['program'].queryset = qs

class TimeslotImportForm(forms.Form):
    program = forms.ModelChoiceField(queryset=None)
    start_date = forms.DateField(label='First Day of New Program', widget=DateWidget)

    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        super(TimeslotImportForm, self).__init__(*args, **kwargs)
        qs = Program.objects.annotate(vr_count = Count(
            Case(When(event__event_type__description='Class Time Block', then=1), default=None, output_field=IntegerField()
            ))).filter(vr_count__gt=0)
        if cur_prog is not None:
            qs = qs.exclude(id=cur_prog.id)
        self.fields['program'].queryset = qs

class ResTypeImportForm(forms.Form):
    program = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        super(ResTypeImportForm, self).__init__(*args, **kwargs)
        qs = Program.objects.annotate(rt_count = Count('resourcetype')).filter(rt_count__gt=0)
        if cur_prog is not None:
            qs = qs.exclude(id=cur_prog.id)
        self.fields['program'].queryset = qs

class EquipmentImportForm(forms.Form):
    program = forms.ModelChoiceField(queryset=None)
    complete_availability = forms.BooleanField(required=False, help_text='Check this box if you would like the new floating resources to be available at all times during the program, rather than attempting to replicate their availability from the previous program.')

    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        super(EquipmentImportForm, self).__init__(*args, **kwargs)
        progs = Resource.objects.filter(is_unique=True).exclude(res_type=ResourceType.get_or_create('Classroom')).values_list('event__program', flat = True).distinct()
        qs = Program.objects.filter(id__in=progs)
        if cur_prog is not None:
            qs = qs.exclude(id=cur_prog.id)
        self.fields['program'].queryset = qs
