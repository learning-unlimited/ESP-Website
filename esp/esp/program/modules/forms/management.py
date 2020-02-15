
from django import forms

from esp.cal.models import Event
from esp.middleware import ESPError
from esp.resources.models import ResourceType, Resource
from esp.program.modules.handlers.grouptextmodule import GroupTextModule

from esp.program.models.class_ import ClassSubject, ClassSection
from decimal import Decimal

""" Forms for the new class management module.  Can be used elsewhere. """

#   Does anyone have a better idea for handling prefixes then copying the code into the __init__
#   functions?

class ManagementForm(forms.Form):
    """ A form that automatically asks the program module to populate its field
    data and choices. """
    def __init__(self, module=None, *args, **kwargs):
        super(ManagementForm, self).__init__(*args, **kwargs)
        if module:
            self.module = module
            for key in self.fields:
                if key in module.form_choice_types and isinstance(self.fields[key], forms.ChoiceField):
                    self.fields[key].choices = module.getFormChoices(key)

class ClassManageForm(ManagementForm):
    """ Class subject admin form.  When the status of a class is changed, any negative changes are
    propagated to all of the class's sections. """

    clsid = forms.IntegerField(initial=-1, widget=forms.HiddenInput)
    status = forms.ChoiceField(choices=())
    reg_status = forms.ChoiceField(required=False, choices=())
    min_grade = forms.ChoiceField(choices=())
    max_grade = forms.ChoiceField(choices=())
    duration = forms.ChoiceField(choices=())
    class_size = forms.IntegerField(label='Max. number of students')
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'cols': 60, 'rows': 8}))

    def __init__(self, *args, **kwargs):
        #   Handle the possibility of this keyword argument; not sure what to do with it yet.
        if 'subject' in kwargs:
            self.cls = kwargs.pop('subject')
            prefix = ''
            if 'prefix' in kwargs:
                prefix = kwargs['prefix'] + '-'
            initial_dict = self.load_data(self.cls, prefix)
            super(ClassManageForm, self).__init__(data=initial_dict, *args, **kwargs)
            if self.cls.hasScheduledSections():
                self.fields['duration'].widget.attrs['disabled'] = True
                self.fields['duration'].widget.attrs['title'] = "At least one section of this class has already been scheduled"
                self.fields['duration'].required = False
        else:
            super(ClassManageForm, self).__init__(*args, **kwargs)

    def load_data(self, cls, prefix=''):
        if isinstance(cls.class_size_max, int):
            csm = cls.class_size_max
        else:  csm = 0
        if cls.duration:
            dur = cls.duration
        else:  dur = Decimal(0)
        self.initial = {
            prefix+'status': cls.status,
            prefix+'reg_status': None,
            prefix+'min_grade': cls.grade_min,
            prefix+'max_grade': cls.grade_max,
            prefix+'duration': dur,
            prefix+'notes': cls.directors_notes,
            prefix+'class_size': csm ,
            prefix+'clsid': cls.id}
        return self.initial

    def save_data(self, cls):
        cls.status = self.cleaned_data['status']
        cls.grade_min = self.cleaned_data['min_grade']
        cls.grade_max = self.cleaned_data['max_grade']
        if not cls.hasScheduledSections():
            cls.duration = Decimal(self.cleaned_data['duration'])
        cls.class_size_max = self.cleaned_data['class_size']
        cls.directors_notes = self.cleaned_data['notes']

        for sec in cls.sections.all():
            sec.duration = cls.duration
            #   If the section's status has not already been marked, apply the subject's status.
            if sec.status == 0:
                sec.status = self.cleaned_data['status']
            if self.cleaned_data['reg_status']:
                sec.registration_status = self.cleaned_data['reg_status']
            #   Give the section a new capacity if the size of the class has been changed on the form.
            if self.cleaned_data['class_size'] != cls.class_size_max and sec.max_class_capacity is not None:
                sec.max_class_capacity = self.cleaned_data['class_size']
            sec.save()

        cls.save()

class SectionManageForm(ManagementForm):
    """ Class section admin form.  This allows each section to be assigned a different time and room.
    """

    secid = forms.IntegerField(initial=-1, widget=forms.HiddenInput)
    times = forms.MultipleChoiceField(required=False, choices=())
    room = forms.MultipleChoiceField(required=False, choices=())
    resources = forms.MultipleChoiceField(label='Floating Resources', required=False, choices=())
    status = forms.ChoiceField(choices=())
    class_size = forms.IntegerField(label='Max. number of students (OVERRIDE: Force the section to be this size regardless of the class or room size!)', required=False)
    reg_status = forms.ChoiceField(required=False, choices=())

    def __init__(self, *args, **kwargs):
        if 'section' in kwargs:
            self.sec = kwargs.pop('section')
            self.index = self.sec.index()
            prefix = ''
            if 'prefix' in kwargs:
                prefix = kwargs['prefix'] + '-'
            initial_dict = self.load_data(self.sec, prefix)
            super(SectionManageForm, self).__init__(data=initial_dict, *args, **kwargs)
        else:
            super(SectionManageForm, self).__init__(*args, **kwargs)

    def load_data(self, sec, prefix=''):
        self.initial = {prefix+'status': sec.status,
            prefix+'reg_status': sec.registration_status,
            prefix+'secid': sec.id,
            prefix+'class_size': sec.max_class_capacity,
            prefix+'times': [ts.id for ts in sec.meeting_times.all()]}
        ir = sec.initial_rooms()
        self.initial[prefix+'room'] = [r.name for r in ir]
        self.initial[prefix+'resources'] = [r.resource.name for r in sec.resourceassignments()]
        return self.initial

    def save_data(self, sec):
        sec.status = self.cleaned_data['status']
        if self.cleaned_data['reg_status']:
            sec.registration_status = self.cleaned_data['reg_status']
        sec.meeting_times.clear()
        for mi in self.cleaned_data['times']:
            ts = Event.objects.get(id=mi)
            ct = ResourceType.get_or_create('Classroom')
            sec.meeting_times.add(ts)
            cr = Resource.objects.filter(res_type__id=ct.id, event__id=ts.id, name__in=self.cleaned_data['room'])
            for c in cr:
                c.assign_to_section(sec, override=True)
        rooms = Resource.objects.filter(name__in=self.cleaned_data['room'])
        if rooms.count() > 0:
            sec.classroomassignments().delete()
            for r in rooms:
                sec.assign_room(r)
        sec.resourceassignments().delete()
        for r in self.cleaned_data['resources']:
            res_list = []
            #check if there's an available floating resource for each time slot
            for ts in sec.meeting_times.all():
                avails = [res for res in sec.parent_program.getFloatingResources(timeslot=ts, queryset=True).filter(name=r) if res.is_available()]
                if len(avails)== 0:
                    raise ESPError('No floating resource "%s" available for timeslot %s.' % (r, ts), log=True)
                else:
                    res_list.append(avails[0])
            #if we made it this far, the resources are available, so we can assign them
            for res in res_list:
                res.assign_to_section(sec)
        sec.max_class_capacity = self.cleaned_data['class_size']
        sec.save()

class ClassCancellationForm(forms.Form):
    target = forms.ModelChoiceField(queryset=ClassSubject.objects.all(), widget=forms.HiddenInput)
    explanation = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'cols': 60}), required=False, help_text='Optional but recommended')
    unschedule = forms.BooleanField(help_text='Check this box to unschedule all sections of this class, in order to free up space for others.  This will delete the original time and location and you won\'t be able to recover them.', required=False)
    email_lottery_students = forms.BooleanField(help_text='Check this box to email all students who applied for this class in a lottery, in addition to those that are actually enrolled.', required=False)
    text_students = forms.BooleanField(help_text='Check this box to send a text message to students who have opted to receive text messages.', required=False)
    email_teachers = forms.BooleanField(initial=True, help_text='Check this box to notify all teachers of this class that this class has been cancelled.', required=False)
    acknowledgement = forms.BooleanField(help_text='By checking this box, I acknowledge that all students in the class will be emailed and then removed from the class.  This operation cannot be undone.')

    def __init__(self, *args, **kwargs):
        initial = kwargs.pop('initial', {})
        initial['target'] = kwargs.pop('subject', None)
        kwargs['initial'] = initial
        super(ClassCancellationForm, self).__init__(*args, **kwargs)
        if not initial['target'].parent_program.hasModule('GroupTextModule') or not GroupTextModule.is_configured():
            self.fields['text_students'].widget = forms.HiddenInput()

class SectionCancellationForm(forms.Form):
    target = forms.ModelChoiceField(queryset=ClassSection.objects.all(), widget=forms.HiddenInput)
    explanation = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'cols': 60}), required=False, help_text='Optional but recommended')
    unschedule = forms.BooleanField(help_text='Check this box to unschedule this section in order to free up space for others.  This will delete the original time and location and you won\'t be able to recover them.', required=False)
    email_lottery_students = forms.BooleanField(help_text='Check this box to email students who applied for this section in a lottery, in addition to those that are actually enrolled.', required=False)
    text_students = forms.BooleanField(help_text='Check this box to send a text message to students who have opted to receive text messages.', required=False)
    email_teachers = forms.BooleanField(initial=True, help_text='Check this box to notify all teachers of this class that this section has been cancelled.', required=False)
    acknowledgement = forms.BooleanField(help_text='By checking this box, I acknowledge that all students in the section will be emailed and then removed from the class.  This operation cannot be undone.')

    def __init__(self, *args, **kwargs):
        initial = kwargs.pop('initial', {})
        initial['target'] = kwargs.pop('section', None)
        kwargs['initial'] = initial
        super(SectionCancellationForm, self).__init__(*args, **kwargs)
        if not initial['target'].parent_program.hasModule('GroupTextModule') or not GroupTextModule.is_configured():
            self.fields['text_students'].widget = forms.HiddenInput()
