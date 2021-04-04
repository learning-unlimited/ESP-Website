
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 by the individual contributors
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

from django import forms
from django.core import validators
from django.core.exceptions import ObjectDoesNotExist
from django.utils.safestring import mark_safe
from esp.utils.forms import StrippedCharField, FormWithRequiredCss, FormUnrestrictedOtherUser
from esp.utils.widgets import BlankSelectWidget, SplitDateWidget
import re
from esp.program.models import ClassCategories, ClassSubject, ClassSection, ClassSizeRange
from esp.program.modules.module_ext import ClassRegModuleInfo
from esp.cal.models import Event
from esp.tagdict.models import Tag
from django.conf import settings
from esp.middleware.threadlocalrequest import get_current_request
from datetime import datetime, timedelta
import json

class TeacherClassRegForm(FormWithRequiredCss):
    location_choices = [    (True, "I will use my own space for this class (e.g. space in my laboratory).  I have explained this in 'Message for Directors' below."),
                            (False, "I would like a classroom to be provided for my class.")]
    lateness_choices = [    (True, "Students may join this class up to 20 minutes after the official start time."),
                            (False, "My class is not suited to late additions.")]
    hardness_choices = [
        ("*",    "*    - Should be understandable to everyone in the class.",),
        ("**",   "**   - Should not be too difficult for most students.",),
        ("***",  "***  - Will move quickly and will have many difficult parts.",),
        ("****", "**** - You should not expect to be able to understand most of this class.",),
    ]

    # The following is a dummy list (because using None causes an error). To enable class styles, admins should set the
    # Tag class_style_choices with value in the following JSON format, where the first element of each list
    # is the value stored in the database, and the second value is the option shown on the form.
    #     [["Lecture", "Lecture Style Class"], ["Seminar", "Seminar Style Class"]]
    style_choices = []

    # Grr, TypedChoiceField doesn't seem to exist yet
    title          = StrippedCharField(    label='Course Title', length=50, max_length=200 )
    category       = forms.ChoiceField( label='Course Category', choices=[], widget=BlankSelectWidget() )
    class_info     = StrippedCharField(   label='Course Description', widget=forms.Textarea(),
                                        help_text=mark_safe('<span class="tex2jax_ignore">Want to enter math? Use <tt>$$ Your-LaTeX-code-here $$</tt>. (e.g. use $$\pi$$ to mention &pi;)</span>'))
    prereqs        = forms.CharField(   label='Course Prerequisites', widget=forms.Textarea(attrs={'rows': 4}), required=False,
                                        help_text='If your course does not have prerequisites, leave this box blank.')

    duration       = forms.ChoiceField( label='Duration of a Class Meeting', help_text='(hours:minutes)', choices=[('0.0', 'Program default')], widget=BlankSelectWidget() )
    num_sections   = forms.ChoiceField( label='Number of Sections', choices=[(1,1)], widget=BlankSelectWidget(),
                                        help_text='(How many independent sections (copies) of your class would you like to teach?)' )
    session_count  = forms.ChoiceField( label='Number of Days of Class', choices=[(1,1)], widget=BlankSelectWidget(),
                                        help_text='(How many days will your class take to complete?)' )

    # To enable grade ranges, admins should set the Tag grade_ranges.
    # e.g. [[7,9],[9,10],[9,12],[10,12],[11,12]] gives five grade ranges: 7-9, 9-10, 9-12, 10-12, and 11-12
    grade_range    = forms.ChoiceField( label='Grade Range', choices=[], widget=BlankSelectWidget() )
    grade_min      = forms.ChoiceField( label='Minimum Grade Level', choices=[(7, 7)], widget=BlankSelectWidget() )
    grade_max      = forms.ChoiceField( label='Maximum Grade Level', choices=[(12, 12)], widget=BlankSelectWidget() )
    class_size_max = forms.ChoiceField( label='Maximum Number of Students',
                                        choices=[(0, 0)],
                                        widget=BlankSelectWidget(),
                                        validators=[validators.MinValueValidator(1)],
                                        help_text='The above class-size and grade-range values are absolute, not the "optimum" nor "recommended" amounts. We will not allow any more students than you specify, nor allow any students in grades outside the range that you specify. Please contact us later if you would like to make an exception for a specific student.' )
    class_size_optimal = forms.IntegerField( label='Optimal Number of Students', help_text="This is the number of students you would have in your class in the most ideal situation.  This number is not a hard limit, but we'll do what we can to try to honor this." )
    optimal_class_size_range = forms.ChoiceField( label='Optimal Class Size Range', choices=[(0, 0)], widget=BlankSelectWidget() )
    allowable_class_size_ranges = forms.MultipleChoiceField( label='Allowable Class Size Ranges', choices=[(0, 0)], widget=forms.CheckboxSelectMultiple(),
                                                             help_text="Please select all class size ranges you are comfortable teaching." )
    class_style = forms.ChoiceField( label='Class Style', choices=style_choices, required=False, widget=BlankSelectWidget())
    hardness_rating = forms.ChoiceField( label='Difficulty',choices=hardness_choices, initial="**",
        help_text="Which best describes how hard your class will be for your students?")
    allow_lateness = forms.ChoiceField( label='Punctuality', choices=lateness_choices, widget=forms.RadioSelect() )

    requested_room = forms.CharField(   label='Room Request', required=False,
                                        help_text='If you have a specific room or type of room in mind, name a room at %s that would be ideal for you.' % settings.INSTITUTION_NAME )

    requested_special_resources = forms.CharField( label='Special Requests', widget=forms.Textarea(), required=False,
                                                   help_text="Write in any specific resources you need, like a piano, empty room, or kitchen. We cannot guarantee you any of the special resources you request, but we will contact you if we are unable to get you the resources you need. Please include any necessary explanations in the 'Message for Directors' box! " )

    purchase_requests = forms.CharField( label='Planned Purchases', widget=forms.Textarea(), required=False,
                                         help_text='We give all teachers a $30 budget per class section for their classes; we can reimburse you if you turn in an itemized receipt with attached reimbursement form before the end of the program.  If you would like to exceed this budget, please type a budget proposal here stating what you would like to buy, what it will cost, and why you would like to purchase it.' )

    message_for_directors       = forms.CharField( label='Message for Directors', widget=forms.Textarea(), required=False,
                                                   help_text='Please explain any special circumstances and equipment requests. Remember that you can be reimbursed for up to $30 (or more with the directors\' approval) for class expenses if you submit itemized receipts.' )


    def __init__(self, crmi, *args, **kwargs):
        from esp.program.controllers.classreg import get_custom_fields

        def hide_field(field, default=None):
            field.widget = forms.HiddenInput()
            if default is not None:
                field.initial = default
        def hide_choice_if_useless(field):
            """ Hide a choice field if there's only one choice """
            if len(field.choices) == 1:
                hide_field(field, default=field.choices[0][0])

        super(TeacherClassRegForm, self).__init__(*args, **kwargs)

        prog = crmi.program

        section_numbers = crmi.allowed_sections_actual
        section_numbers = zip(section_numbers, section_numbers)

        class_sizes = crmi.getClassSizes()
        class_sizes = zip(class_sizes, class_sizes)

        class_grades = crmi.getClassGrades()
        class_grades = zip(class_grades, class_grades)

        class_ranges = ClassSizeRange.get_ranges_for_program(prog)
        class_ranges = [(range.id, range.range_str()) for range in class_ranges]

        # num_sections: section_list; hide if useless
        self.fields['num_sections'].choices = section_numbers
        hide_choice_if_useless( self.fields['num_sections'] )
        # category: program.class_categories.all()
        self.fields['category'].choices = [ (x.id, x.category) for x in prog.class_categories.all() ]
        # grade_min, grade_max: crmi.getClassGrades
        self.fields['grade_min'].choices = class_grades
        self.fields['grade_max'].choices = class_grades
        if Tag.getProgramTag('grade_ranges', prog):
            grade_ranges = json.loads(Tag.getProgramTag('grade_ranges', prog))
            self.fields['grade_range'].choices = [(range,str(range[0]) + " - " + str(range[1])) for range in grade_ranges]
            del self.fields['grade_min']
            del self.fields['grade_max']
        else:
            del self.fields['grade_range']
        if crmi.use_class_size_max:
            # class_size_max: crmi.getClassSizes
            self.fields['class_size_max'].choices = class_sizes
        else:
            del self.fields['class_size_max']

        if Tag.getBooleanTag('use_class_size_optimal'):
            if not crmi.use_class_size_optimal:
                del self.fields['class_size_optimal']

            if crmi.use_optimal_class_size_range:
                self.fields['optimal_class_size_range'].choices = class_ranges
            else:
                del self.fields['optimal_class_size_range']

            if crmi.use_allowable_class_size_ranges:
                self.fields['allowable_class_size_ranges'].choices = class_ranges
            else:
                del self.fields['allowable_class_size_ranges']
        else:
            del self.fields['class_size_optimal']
            del self.fields['optimal_class_size_range']
            del self.fields['allowable_class_size_ranges']

        # decide whether to display certain fields

        # prereqs
        if not crmi.set_prereqs:
            self.fields['prereqs'].widget = forms.HiddenInput()

        # allow_lateness
        if not crmi.allow_lateness:
            self.fields['allow_lateness'].widget = forms.HiddenInput()
            self.fields['allow_lateness'].initial = 'False'

        self.fields['duration'].choices = sorted(crmi.getDurations())
        hide_choice_if_useless( self.fields['duration'] )

        # session_count
        if crmi.session_counts:
            session_count_choices = crmi.session_counts_ints
            session_count_choices = zip(session_count_choices, session_count_choices)
            self.fields['session_count'].choices = session_count_choices
        hide_choice_if_useless( self.fields['session_count'] )

        # requested_room
        if not crmi.ask_for_room:
            hide_field( self.fields['requested_room'] )

        #   Hide resource fields since separate forms are now being used. - Michael P
        #   Most have now been removed, but this one gets un-hidden by open classes.
        self.fields['requested_special_resources'].widget = forms.HiddenInput()

        #   Add program-custom form components (for inlining additional questions without
        #   introducing a separate program module)
        custom_fields = get_custom_fields()
        for field_name in custom_fields:
            self.fields[field_name] = custom_fields[field_name]

        #   Modify help text on these fields if necessary.
        #   TODO(benkraft): Is there a reason not to allow this on all fields?
        custom_helptext_fields = [
            'duration', 'class_size_max', 'class_size_optimal', 'num_sections',
            'requested_room', 'message_for_directors', 'purchase_requests',
            'class_info', 'grade_max', 'grade_min'] + custom_fields.keys()
        for field in custom_helptext_fields:
            tag_data = Tag.getProgramTag('teacherreg_label_%s' % field, prog)
            if tag_data:
                self.fields[field].label = tag_data
            tag_data = Tag.getProgramTag('teacherreg_help_text_%s' % field, prog)
            if tag_data:
                self.fields[field].help_text = tag_data

        #   Hide fields as desired.
        tag_data = Tag.getProgramTag('teacherreg_hide_fields', prog)
        if tag_data:
            for field_name in tag_data.split(','):
                hide_field(self.fields[field_name])

        tag_data = Tag.getProgramTag('teacherreg_default_min_grade', prog)
        if tag_data:
            self.fields['grade_min'].initial = tag_data

        tag_data = Tag.getProgramTag('teacherreg_default_max_grade', prog)
        if tag_data:
            self.fields['grade_max'].initial = tag_data

        tag_data = Tag.getProgramTag('teacherreg_default_class_size_max', prog)
        if tag_data:
            self.fields['class_size_max'].initial = tag_data

        #   Rewrite difficulty label/choices if desired:
        if Tag.getTag('teacherreg_difficulty_choices'):
            self.fields['hardness_rating'].choices = json.loads(Tag.getTag('teacherreg_difficulty_choices'))

        # Get class_style_choices from tag, otherwise hide the field
        if Tag.getTag('class_style_choices'):
            self.fields['class_style'].choices = json.loads(Tag.getTag('class_style_choices'))
            self.fields['class_style'].required = True
        else:
            hide_field(self.fields['class_style'])
        # plus subprogram section wizard

    def clean(self):
        cleaned_data = self.cleaned_data

        # Make sure grade_min <= grade_max
        # We need to cast here until we can make the ChoiceFields into TypedChoiceFields.
        grade_min = cleaned_data.get('grade_min')
        grade_max = cleaned_data.get('grade_max')
        if grade_min and grade_max:
            grade_min = int(grade_min)
            grade_max = int(grade_max)
            if grade_min > grade_max:
                msg = u'Minimum grade must be less than the maximum grade.'
                self.add_error('grade_min', msg)
                self.add_error('grade_max', msg)

        # Make sure the optimal class size <= maximum class size.
        class_size_optimal = cleaned_data.get('class_size_optimal')
        class_size_max = cleaned_data.get('class_size_max')
        if class_size_optimal and class_size_max:
            class_size_optimal = int(class_size_optimal)
            class_size_max = int(class_size_max)
            if class_size_optimal > class_size_max:
                msg = u'Optimal class size must be less than or equal to the maximum class size.'
                self.add_error('class_size_optimal', msg)
                self.add_error('class_size_max', msg)

        if class_size_optimal == '':
            cleaned_data['class_size_optimal'] = None

        # If using grade ranges instead of min and max, extract min and max from grade range.
        if cleaned_data.get('grade_range'):
            cleaned_data['grade_min'], cleaned_data['grade_max'] = json.loads(cleaned_data.get('grade_range'))

        # Return cleaned data
        return cleaned_data

    def _get_total_time_requested(self):
        """ Get total time requested. Do not call before validation. """
        return float(self.cleaned_data['duration']) * int(self.cleaned_data['num_sections'])


class TeacherOpenClassRegForm(TeacherClassRegForm):

    def __init__(self, crmi, *args, **kwargs):
        """ Initialize the teacher class reg form, and then remove irrelevant fields. """
        def hide_field(field, default=None):
            field.widget = forms.HiddenInput()
            if default is not None:
                field.initial = default

        super(TeacherOpenClassRegForm, self).__init__(crmi, *args, **kwargs)
        program = crmi.program
        open_class_category = program.open_class_category
        self.fields['category'].choices += [(open_class_category.id, open_class_category.category)]

        # Re-enable the requested special resources field as a space needs .
        self.fields['requested_special_resources'].widget = forms.Textarea()
        self.fields['requested_special_resources'].label = "Space Needs"
        self.fields['requested_special_resources'].help_text = "Please describe what kind of space needs you will have for this open class (such as walls, chairs, open floor space, etc)."

        # Modify some help texts to be form-specific.
        self.fields['duration'].help_text = "For how long are you willing to teach this class?"

        if self.fields.get('grade_min') and self.fields.get('grade_max'):
            del self.fields['grade_min']
            del self.fields['grade_max']
        else:
            del self.fields['grade_range']

        fields = [('category', open_class_category.id),
                  ('prereqs', ''), ('session_count', 1),
                  ('class_size_max', 200), ('class_size_optimal', ''), ('optimal_class_size_range', ''),
                  ('allowable_class_size_ranges', ''), ('hardness_rating', '**'), ('allow_lateness', True),
                  ('requested_room', '')]
        for field, default in fields:
            if field in self.fields:
                self.fields[field].required = False
                hide_field(self.fields[field], default)


class TeacherEventSignupForm(FormWithRequiredCss):
    """ Form for teachers to pick interview and teacher training times. """
    interview = forms.ChoiceField( label='Interview', choices=[], required=False, widget=BlankSelectWidget(blank_choice=('', 'Pick an interview timeslot...')) )
    training  = forms.ChoiceField( label='Teacher Training', choices=[], required=False, widget=BlankSelectWidget(blank_choice=('', 'Pick a teacher training session...')) )

    def _slot_is_taken(self, event):
        """ Determine whether an interview slot is taken. """
        return self.module.entriesBySlot(event).count() > 0

    def _slot_is_mine(self, event):
        """ Determine whether an interview slot is taken by you. """
        return self.module.entriesBySlot(event).filter(user=self.user).count() > 0

    def _slot_too_late(self, event):
        """ Determine whether it is too late to register for a time slot. """
        # Don't allow signing up for a spot insuficiently far in advance
        return event.start - datetime.now() < timedelta(days=0)

    def _slot_is_available(self, event):
        """ Determine whether a time slot is available. """
        return self._slot_is_mine(event) or (not self._slot_is_taken(event) and not self._slot_too_late(event))

    def __init__(self, module, *args, **kwargs):
        super(TeacherEventSignupForm, self).__init__(*args, **kwargs)
        self.module = module
        self.user = get_current_request().user

        interview_times = module.getTimes('interview')
        if interview_times.count() > 0:
            self.fields['interview'].choices = [ (x.id, x.description) for x in interview_times if self._slot_is_available(x) ]
        else:
            self.fields['interview'].widget = forms.HiddenInput()

        training_times = module.getTimes('training')
        if training_times.count() > 0:
            self.fields['training'].choices = [ (x.id, x.description) for x in training_times if not self._slot_too_late(x) ]
        else:
            self.fields['training'].widget = forms.HiddenInput()

    def clean_interview(self):
        event_id = self.cleaned_data['interview']
        try:
            data = Event.objects.get(id=event_id)
        except ValueError:
            return None
        if not self._slot_is_available(data):
            raise forms.ValidationError('That time is taken; please select a different one.')
        return data

    def clean_training(self):
        event_id = self.cleaned_data['training']
        try:
            return Event.objects.get(id=event_id)
        except ValueError:
            return None
