from decimal import Decimal
from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe
from form_utils.forms import BetterForm, BetterModelForm

from esp.accounting.models import LineItemType
from esp.cal.models import Event
from esp.program.controllers.lunch_constraints import LunchConstraintGenerator
from esp.program.forms import ProgramCreationForm
from esp.program.models import RegistrationType, Program
from esp.program.modules.module_ext import ClassRegModuleInfo, StudentClassRegModuleInfo
from esp.tagdict import all_program_tags, tag_categories
from esp.tagdict.models import Tag

def get_rt_choices():
    choices = [("All","All")]
    for rt in RegistrationType.objects.all().order_by('name'):
        if rt.displayName:
            choices.append((rt.name, '%s (displayed as "%s")' % (rt.name, rt.displayName)))
        else:
            choices.append((rt.name, rt.name))
    return choices

class VisibleRegistrationTypeForm(forms.Form):
    display_names = forms.MultipleChoiceField(choices=get_rt_choices(), required=False, label='', help_text=mark_safe("<br />Select the Registration Types that should be displayed on a student's schedule on the studentreg page. To select an entry, hold Ctrl (on Windows or Linux) or Meta (on Mac), and then press it with your mouse."), widget=forms.SelectMultiple(attrs={'style':'height:150px; background:white;'}))


class LunchConstraintsForm(forms.Form):
    def __init__(self, program, *args, **kwargs):
        self.program = program

        super(LunchConstraintsForm, self).__init__(*args, **kwargs)

        #   Set choices for timeslot field
        self.fields['timeslots'].choices = [(ts.id, ts.short_description) for ts in self.program.getTimeSlots()]
        self.load_data()

    def load_data(self):
        lunch_timeslots = Event.objects.filter(meeting_times__parent_class__parent_program=self.program, meeting_times__parent_class__category__category='Lunch').distinct()
        self.initial['timeslots'] = lunch_timeslots.values_list('id', flat=True)

    def save_data(self):
        timeslots = Event.objects.filter(id__in=self.cleaned_data['timeslots']).order_by('start')
        cg = LunchConstraintGenerator(self.program, timeslots, generate_constraints=(self.cleaned_data['generate_constraints'] is True), autocorrect=(self.cleaned_data['autocorrect'] is True), include_conditions=(self.cleaned_data['include_conditions'] is True))
        cg.generate_all_constraints()

    timeslots = forms.MultipleChoiceField(choices=[], required=False, widget=forms.CheckboxSelectMultiple)

    generate_constraints=forms.BooleanField(initial=True, required=False, help_text="Check this box to generate lunch scheduling constraints. If unchecked, only lunch sections will be generated, and the other two check boxes will have no effect.")
    autocorrect = forms.BooleanField(initial=True, required=False, help_text="Check this box to attempt automatically adding lunch to a student's schedule so that they are less likely to violate the schedule constraint.")
    include_conditions = forms.BooleanField(initial=True, required=False, help_text="Check this box to allow students to schedule classes through lunch if they do not have morning or afternoon classes.")

class ProgramSettingsForm(ProgramCreationForm):
    """ Form for changing program-related settings. """
    # Remove these fields because they are editable on the deadline management page
    teacher_reg_start = None
    teacher_reg_end   = None
    student_reg_start = None
    student_reg_end   = None
    def __init__(self, *args, **kwargs):
        super(ProgramSettingsForm, self).__init__(*args, **kwargs)

    def save(self):
        prog = self.instance
        LineItemType.objects.filter(text='Program admission',program=prog
        ).update(amount_dec=Decimal('%.2f' % self.cleaned_data['base_cost']))
        prog.sibling_discount = self.cleaned_data['sibling_discount']
        return super(ProgramSettingsForm, self).save()

    class Meta:
        fieldsets = [
                     ('Program Title', {'fields': ['term', 'term_friendly'] }),
                     ('Program Constraints', {'fields':['grade_min','grade_max','program_size_max','program_allow_waitlist']}),
                     ('About Program Creator',{'fields':['director_email', 'director_cc_email', 'director_confidential_email']}),
                     ('Financial Details' ,{'fields':['base_cost','sibling_discount']}),
                     ('Program Internal Details' ,{'fields':['program_type','program_modules','program_module_questions','class_categories','flag_types']}),
                    ]# Here you can also add description for each fieldset.
        widgets = {
            'program_modules': forms.SelectMultiple(attrs={'class': 'hidden-field'}),
        }
        model = Program

class TeacherRegSettingsForm(BetterModelForm):
    """ Form for changing teacher class registration settings. """
    def __init__(self, *args, **kwargs):
        super(TeacherRegSettingsForm, self).__init__(*args, **kwargs)

    class Meta:
        fieldsets = [
                     ('Teacher Settings', {'fields': ['allow_coteach', 'set_prereqs', 'num_teacher_questions']}),
                     ('Class Duration and Size Options', {'fields': ['class_max_duration', 'class_min_cap', 'class_max_size', 'class_size_step', 'class_other_sizes']}),
                     ('Section Options', {'fields': ['allowed_sections', 'session_counts']}),
                     ('Other Options', {'fields': ['allow_lateness', 'ask_for_room', 'use_class_size_max', 'use_class_size_optimal', 'use_optimal_class_size_range', 'use_allowable_class_size_ranges', 'open_class_registration']}),
                     ('Visual Options', {'fields': ['color_code', 'progress_mode']}),
                    ]# Here you can also add description for each fieldset.
        model = ClassRegModuleInfo

class StudentRegSettingsForm(BetterModelForm):
    """ Form for changing student class registration settings. """
    def __init__(self, *args, **kwargs):
        super(StudentRegSettingsForm, self).__init__(*args, **kwargs)

    class Meta:
        fieldsets = [
                     ('Capacity Settings', {'fields': ['enforce_max', 'class_cap_multiplier', 'class_cap_offset', 'apply_multiplier_to_room_cap']}),
                     ('Priority Registration Settings', {'fields': ['use_priority', 'priority_limit']}),
                     ('Enrollment Settings', {'fields': ['use_grade_range_exceptions', 'register_from_catalog', 'visible_enrollments', 'visible_meeting_times', 'show_emailcodes']}),
                     ('Button Settings', {'fields': ['confirm_button_text', 'view_button_text', 'cancel_button_text', 'temporarily_full_text', 'cancel_button_dereg', 'send_confirmation']}),
                     ('Visual Options', {'fields': ['progress_mode','force_show_required_modules']}),
                    ]# Here you can also add description for each fieldset.
        model = StudentClassRegModuleInfo

class ProgramTagSettingsForm(BetterForm):
    """ Form for changing tags associated with a program. """
    def __init__(self, *args, **kwargs):
        self.program = kwargs.pop('program')
        self.categories = set()
        super(ProgramTagSettingsForm, self).__init__(*args, **kwargs)
        for key in all_program_tags:
            # generate field for each tag
            tag_info = all_program_tags[key]
            if tag_info.get('is_setting', False):
                self.categories.add(tag_info.get('category'))
                field = tag_info.get('field')
                if field is not None:
                    self.fields[key] = field
                elif tag_info.get('is_boolean', False):
                    self.fields[key] = forms.BooleanField()
                else:
                    self.fields[key] = forms.CharField()
                self.fields[key].help_text = tag_info.get('help_text', '')
                self.fields[key].initial = tag_info.get('default')
                self.fields[key].required = False
                set_val = Tag.getBooleanTag(key, program = self.program) if tag_info.get('is_boolean', False) else Tag.getProgramTag(key, program = self.program)
                if set_val != None and set_val != self.fields[key].initial:
                    self.fields[key].initial = set_val

    def save(self):
        prog = self.program
        for key in all_program_tags:
            # Update tags if necessary
            tag_info = all_program_tags[key]
            if tag_info.get('is_setting', False):
                set_val = self.cleaned_data[key]
                global_val = Tag.getBooleanTag(key, default = tag_info.get('default')) if tag_info.get('is_boolean', False) else Tag.getProgramTag(key, default = tag_info.get('default'))
                if not set_val in ("", "None", None, global_val):
                    # Set a [new] tag if a value was provided and the value is not the default (or if it is but there is also a global tag set)
                    Tag.setTag(key, prog, set_val)
                else:
                    # Otherwise, delete the old tag, if there is one
                    Tag.unSetTag(key, prog)

    class Meta:
        fieldsets = [(cat, {'fields': [key for key in sorted(all_program_tags.keys()) if all_program_tags[key].get('category') == cat], 'legend': tag_categories[cat]}) for cat in sorted(tag_categories.keys())]
