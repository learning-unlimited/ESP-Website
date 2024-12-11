from __future__ import absolute_import
from django import forms
from django.conf import settings
from django.contrib import admin
from django.template import Template, Context
from django.template.loader import select_template
from django.utils.safestring import mark_safe
from form_utils.forms import BetterForm, BetterModelForm

from esp.cal.models import Event
from esp.program.controllers.lunch_constraints import LunchConstraintGenerator
from esp.program.forms import ProgramCreationForm
from esp.program.models import RegistrationType, Program, ScheduleConstraint, BooleanToken
from esp.program.modules.module_ext import ClassRegModuleInfo, StudentClassRegModuleInfo, DBReceipt
from esp.tagdict import all_program_tags, tag_categories
from esp.tagdict.models import Tag
from esp.utils.models import TemplateOverride

def get_rt_choices():
    choices = [("All", "All")]
    for rt in RegistrationType.objects.all().order_by('name'):
        if rt.displayName:
            choices.append((rt.name, '%s (displayed as "%s")' % (rt.name, rt.displayName)))
        else:
            choices.append((rt.name, rt.name))
    return choices

class VisibleRegistrationTypeForm(forms.Form):
    display_names = forms.MultipleChoiceField(choices=[], required=False, label='', help_text=mark_safe("<br />Select the Registration Types that should be displayed on a student's schedule on the studentreg page. To select an entry, hold Ctrl (on Windows or Linux) or Meta (on Mac), and then press it with your mouse."), widget=forms.SelectMultiple(attrs={'style':'height:150px; background:white;'}))
    def __init__(self, *args, **kwargs):
        super(VisibleRegistrationTypeForm, self).__init__(*args, **kwargs)
        self.fields['display_names'].choices = get_rt_choices()

class LunchConstraintsForm(forms.Form):
    def __init__(self, program, *args, **kwargs):
        self.program = program

        super(LunchConstraintsForm, self).__init__(*args, **kwargs)

        #   Set choices for timeslot field
        self.fields['timeslots'].choices = [(ts.id, ts.short_description) for ts in self.program.getTimeSlots()]
        self.load_data()

    def load_data(self):
        lunch_timeslots = Event.objects.filter(meeting_times__parent_class__parent_program=self.program, meeting_times__parent_class__category__category='Lunch').distinct()
        self.fields['timeslots'].initial = list(lunch_timeslots.values_list('id', flat=True))
        sched_constraints = ScheduleConstraint.objects.filter(program=self.program)
        # If there are any schedule constraints for this program, check that box
        if sched_constraints.exists():
            self.fields['generate_constraints'].initial = True
            # If any schedule constraints have an 'on_failure' function, check the autocorrect box
            if sched_constraints.exclude(on_failure='').exists():
                self.fields['autocorrect'].initial = True
            # If any BooleanTokens associated with the schedule cosntraints have text other than '1', check the include_conditions box
            if BooleanToken.objects.filter(exp__condition_constraint__program=2).exclude(text='1').exists():
                self.fields['include_conditions'].initial = True

    def save_data(self):
        timeslots = Event.objects.filter(id__in=self.cleaned_data['timeslots']).order_by('start')
        cg = LunchConstraintGenerator(self.program, timeslots, generate_constraints=(self.cleaned_data['generate_constraints'] is True), autocorrect=(self.cleaned_data['autocorrect'] is True), include_conditions=(self.cleaned_data['include_conditions'] is True))
        cg.generate_all_constraints()

    timeslots = forms.MultipleChoiceField(choices=[], required=False, widget=forms.CheckboxSelectMultiple)

    generate_constraints=forms.BooleanField(initial=False, required=False, help_text="Check this box to generate lunch scheduling constraints. If unchecked, only lunch sections will be generated, and the other two check boxes will have no effect.")
    autocorrect = forms.BooleanField(initial=False, required=False, help_text="Check this box to attempt automatically adding lunch to a student's schedule so that they are less likely to violate the schedule constraint.")
    include_conditions = forms.BooleanField(initial=False, required=False, help_text="Check this box to allow students to schedule classes through lunch if they do not have morning or afternoon classes.")

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
        return super(ProgramSettingsForm, self).save()

    class Meta:
        fieldsets = [
                     ('Program Title', {'fields': ['term', 'term_friendly'] }),
                     ('Program Constraints', {'fields':['grade_min', 'grade_max', 'program_size_max', 'program_allow_waitlist']}),
                     ('About Program Creator', {'fields':['director_email', 'director_cc_email', 'director_confidential_email']}),
                     ('Financial Details', {'fields':['base_cost', 'sibling_discount']}),
                     ('Program Internal Details', {'fields':['program_type', 'program_modules', 'program_module_questions', 'class_categories', 'flag_types']}),
                    ]# Here you can also add description for each fieldset.
        widgets = {
            'program_modules': forms.SelectMultiple(attrs={'class': 'hidden-field'}),
        }
        model = Program
ProgramSettingsForm.base_fields['director_email'].widget = forms.EmailInput(attrs={'pattern': r'(^.+@{0}$)|(^.+@(\w+\.)?learningu\.org$)'.format(settings.SITE_INFO[1].replace('.', '\.'))})

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
                     ('Priority Registration Settings', {'fields': ['priority_limit']}), # use_priority is not included here to prevent confusion; to my knowledge, only HSSP uses this setting - WG
                     ('Enrollment Settings', {'fields': ['register_from_catalog', 'visible_enrollments', 'visible_meeting_times', 'show_emailcodes']}), # use_grade_range_exceptions is excluded until there is an interface for it - WG 5/25/23
                     ('Button Settings', {'fields': ['confirm_button_text', 'view_button_text', 'cancel_button_text', 'temporarily_full_text', 'cancel_button_dereg', 'send_confirmation']}),
                     ('Visual Options', {'fields': ['progress_mode', 'force_show_required_modules']}),
                    ]# Here you can also add description for each fieldset.
        model = StudentClassRegModuleInfo

def get_template_source(template_list):
    template = select_template(template_list)
    if template.origin.name == "(template override)": # source is from a template override
        return TemplateOverride.objects.get(name=template.template.name).content.replace('\r\n', '\n').strip() # Use unix line endings and strip whitespace just in case
    else: # source is from a file
        return open(template.origin.name, 'r').read().strip()

class ReceiptsForm(BetterForm):
    confirm = forms.CharField(widget=forms.Textarea(attrs={'class': 'fullwidth'}),
                              help_text = mark_safe("This text is <b>shown on the website</b> when a student clicks the 'confirm registration' button (HTML is supported).\
                                                    If no text is supplied, the default text will be used. The text is then followed by the student's information,\
                                                    the program information, the student's purchased items, and the student's schedule."),
                              required = False)
    confirmemail = forms.CharField(widget=forms.Textarea(attrs={'class': 'fullwidth'}),
                                   help_text = mark_safe("This text is <b>sent via email</b> when a student clicks the 'confirm registration' button.\
                                                     If no text is supplied, the default text will be used. The text is then followed by the student's information,\
                                                     the program information, the student's purchased items, and the student's schedule. This email can be disabled\
                                                     by deactivating the 'Send confirmation' option in the 'Student Registration Settings' above."),
                                   required = False)
    cancel = forms.CharField(widget=forms.Textarea(attrs={'class': 'fullwidth'}),
                              help_text = "This receipt is shown on the website when a student clicks the 'cancel registration' button.\
                                           If no text is supplied, the student will be redirected to the main student registration page instead.",
                              required = False)

    def __init__(self, *args, **kwargs):
        self.program = kwargs.pop('program')
        super(ReceiptsForm, self).__init__(*args, **kwargs)
        for action in ['confirm', 'confirmemail', 'cancel']:
            receipts = DBReceipt.objects.filter(program=self.program, action=action)
            if receipts.count() > 0:
                receipt_text = receipts.latest('id').receipt
            elif action == "confirm":
                receipt_text = get_template_source(['program/receipts/%s_custom_pretext.html' %(self.program.id), 'program/receipts/default_pretext.html'])
            elif action == "confirmemail":
                receipt_text = get_template_source(['program/confemails/%s_confemail_pretext.html' %(self.program.id), 'program/confemails/default_pretext.html'])
            else:
                receipt_text = ""
            self.fields[action].initial = receipt_text.encode('UTF-8')

    def save(self):
        for action in ['confirm', 'confirmemail', 'cancel']:
            receipts = DBReceipt.objects.filter(program=self.program, action=action)
            cleaned_text = self.cleaned_data[action].replace('\r\n', '\n').strip() # Use unix line endings and strip whitespace just in case
            if cleaned_text == "":
                receipts.delete()
            else:
                if action == "confirm":
                    default_text = get_template_source(['program/receipts/%s_custom_pretext.html' %(self.program.id), 'program/receipts/default_pretext.html'])
                elif action == "confirmemail":
                    default_text = get_template_source(['program/confemails/%s_confemail_pretext.html' %(self.program.id), 'program/confemails/default_pretext.html'])
                elif action == "cancel":
                    default_text = ""
                if cleaned_text == default_text:
                    receipts.delete()
                else:
                    receipt, created = DBReceipt.objects.get_or_create(program=self.program, action=action)
                    receipt.receipt = cleaned_text
                    receipt.save()

    class Meta:
        fieldsets = [('Student Registration Receipts', {'fields': ['confirm', 'confirmemail', 'cancel']})]

class ProgramTagSettingsForm(BetterForm):
    """ Form for changing tags associated with a program. """
    def __init__(self, *args, **kwargs):
        self.program = kwargs.pop('program')
        self.categories = set()
        super(ProgramTagSettingsForm, self).__init__(*args, **kwargs)
        from esp.program.modules.forms.teacherreg import TeacherClassRegForm
        classreg_fields = [field.name for field in TeacherClassRegForm(self.program.classregmoduleinfo).visible_fields()]
        for key in all_program_tags:
            # generate field for each tag
            tag_info = all_program_tags[key]
            if tag_info.get('is_setting', False):
                self.categories.add(tag_info.get('category'))
                field = tag_info.get('field')
                if key == 'teacherreg_hide_fields':
                    self.fields[key] = forms.MultipleChoiceField(choices=[(field[0], field[1].label if field[1].label else field[0]) for field in TeacherClassRegForm.declared_fields.items() if not field[1].required])
                elif key in ['student_reg_records', 'teacher_reg_records']:
                    from esp.users.models import RecordType
                    self.fields[key] = forms.MultipleChoiceField(choices=list(RecordType.desc()))
                elif field is not None:
                    self.fields[key] = field
                elif tag_info.get('is_boolean', False):
                    self.fields[key] = forms.BooleanField()
                else:
                    self.fields[key] = forms.CharField()
                # some help texts need to be rendered
                if key in ['student_self_checkin']:
                    template = Template(tag_info.get('help_text', ''))
                    self.fields[key].help_text = template.render(Context({'program': self.program}))
                else:
                    self.fields[key].help_text = tag_info.get('help_text', '')
                self.fields[key].initial = self.fields[key].default = tag_info.get('default')
                self.fields[key].required = False
                set_val = Tag.getBooleanTag(key, program = self.program) if tag_info.get('is_boolean', False) else Tag.getProgramTag(key, program = self.program)
                if set_val != None and set_val != self.fields[key].initial:
                    if isinstance(self.fields[key], forms.MultipleChoiceField):
                        set_val = set_val.split(",")
                    self.fields[key].initial = set_val
                # For class reg tags, hide them if the fields are not in the form
                if key.startswith("teacherreg_label") and key.partition("teacherreg_label_")[2] not in classreg_fields:
                    self.fields[key].widget = forms.HiddenInput()
                elif key.startswith("teacherreg_help_text") and key.partition("teacherreg_help_text_")[2] not in classreg_fields:
                    self.fields[key].widget = forms.HiddenInput()

    def save(self):
        prog = self.program
        for key in all_program_tags:
            # Update tags if necessary
            tag_info = all_program_tags[key]
            if tag_info.get('is_setting', False):
                set_val = self.cleaned_data[key]
                if isinstance(set_val, list):
                    set_val = ",".join(set_val)
                global_val = Tag.getBooleanTag(key, default = tag_info.get('default')) if tag_info.get('is_boolean', False) else Tag.getProgramTag(key, default = tag_info.get('default'))
                if not set_val in ("", "None", None, global_val):
                    # Set a [new] tag if a value was provided and the value is not the default (or if it is but there is also a global tag set)
                    Tag.setTag(key, prog, set_val)
                else:
                    # Otherwise, delete the old tag, if there is one
                    Tag.unSetTag(key, prog)

    class Meta:
        fieldsets = [(cat, {'fields': [key for key in sorted(all_program_tags.keys()) if all_program_tags[key].get('category') == cat], 'legend': tag_categories[cat]}) for cat in tag_categories.keys()]
