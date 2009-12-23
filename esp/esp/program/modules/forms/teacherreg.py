
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 MIT ESP

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

from django import forms
from esp.utils.forms import SizedCharField, FormWithRequiredCss, FormUnrestrictedOtherUser
from esp.utils.widgets import BlankSelectWidget, SplitDateWidget
import re
from esp.datatree.models import DataTree, GetNode
from esp.users.models import UserBit
from esp.program.models import ClassCategories, ClassSubject, ClassSection
from esp.cal.models import Event
from datetime import datetime, timedelta

class TeacherClassRegForm(FormWithRequiredCss):
    location_choices = [    (True, "I will use my own space for this class (e.g. space in my laboratory).  I have explained this in 'Message for Directors' below."),
                            (False, "I would like a classroom to be provided for my class.")]
    lateness_choices = [    (True, "Students may join this class up to 20 minutes after the official start time."),
                            (False, "My class is not suited to late additions.")]                                
    
    # Grr, TypedChoiceField doesn't seem to exist yet
    title          = SizedCharField(    label='Course Title', length=50, max_length=200 )
    category       = forms.ChoiceField( label='Course Category', choices=[], widget=BlankSelectWidget() )
    class_info     = forms.CharField(   label='Course Description', widget=forms.Textarea(),
                                        help_text='Want to enter math? Use <tt>$$ Your-LaTeX-code-here $$</tt>. (e.g. use $$\pi$$ to mention &pi;)' )
    prereqs        = forms.CharField(   label='Course Prerequisites', widget=forms.Textarea(), required=False )
    
    # At the moment we don't use viable_times at all.
    viable_times   = forms.ChoiceField( label='Starting Time', choices=[] )
    duration       = forms.ChoiceField( label='Duration of a Class Meeting', help_text='(hours:minutes)', choices=[('0.0', 'Program default')], widget=BlankSelectWidget() )
    num_sections   = forms.ChoiceField( label='Number of Sections', choices=[(1,1)], widget=BlankSelectWidget(),
                                        help_text='(How many independent sections (copies) of your class would you like to teach?)' )
    session_count  = forms.ChoiceField( label='Number of Days of Class', choices=[(1,1)], widget=BlankSelectWidget(),
                                        help_text='(How many days will your class take to complete?)' )
    
    grade_min      = forms.ChoiceField( label='Minimum Grade Level', choices=[(7, 12)], widget=BlankSelectWidget() )
    grade_max      = forms.ChoiceField( label='Maximum Grade Level', choices=[(7, 12)], widget=BlankSelectWidget() )
    class_size_max = forms.ChoiceField( label='Maximum Number of Students', choices=[(0, 0)], widget=BlankSelectWidget(),
                                        help_text='The above class-size and grade-range values are absolute, not the "optimum" nor "recommended" amounts. We will not allow any more students than you specify, nor allow any students in grades outside the range that you specify. Please contact us later if you would like to make an exception for a specific student.' )
    class_size_optimal = forms.ChoiceField( label='Optimal Number of Students', choices=[(0, 0)], required=False, widget=BlankSelectWidget(), help_text="This is the number of students you would have in your class in the most ideal situation.  This number is not a hard limit, but we'll do what we can to try to honor this." )
    allow_lateness = forms.ChoiceField( label='Punctuality', choices=lateness_choices, widget=forms.RadioSelect() )
    
    has_own_space  = forms.ChoiceField( label='Location', choices=location_choices, widget=forms.RadioSelect(), required=False )
    requested_room = forms.CharField(   label='Room Request', required=False,
                                        help_text='If you have a specific room or type of room in mind, name a room at MIT that would be ideal for you.' )
    
    global_resources = forms.MultipleChoiceField( label='Equipment and Classroom Options',
                                                  choices=[], widget=forms.CheckboxSelectMultiple(), required=False,
                                                  help_text="Check all that apply. We can usually supply these common resources at your request. But if your class is truly uncommon, ESP may also have access to unusual rooms and supplies. These can be entered in the next section, 'Special Requests.'" )
    resources        = forms.MultipleChoiceField( label='Other Resources',
                                                  choices=[], widget=forms.CheckboxSelectMultiple(), required=False )
    requested_special_resources = forms.CharField( label='Special Requests', widget=forms.Textarea(), required=False,
                                                   help_text="Write in any specific resources you need, like a piano, empty room, or kitchen. We cannot guarantee you any of the special resources you request, but we will contact you if we are unable to get you the resources you need. Please include any necessary explanations in the 'Message for Directors' box! " )

    purchase_requests = forms.CharField( label='Planned Purchases', widget=forms.Textarea(), required=False,
                                         help_text='We give all teachers a $30 budget per class section for their classes; we can reimburse you if you turn in an itemized receipt with attached reimbursement form before the end of the program.  If you would like to exceed this budget, please type a budget proposal here stating what you would like to buy, what it will cost, and why you would like to purchase it.' )
    
    message_for_directors       = forms.CharField( label='Message for Directors', widget=forms.Textarea(), required=False,
                                                   help_text='Please explain any special circumstances and equipment requests. Remember that you can be reimbursed for up to $30 (or more with the directors\' approval) for class expenses if you submit itemized receipts.' )
    
    
    def __init__(self, module, *args, **kwargs):
        def hide_field(field, default=None):
            field.widget = forms.HiddenInput()
            if default is not None:
                field.initial = default
        def hide_choice_if_useless(field):
            """ Hide a choice field if there's only one choice """
            if len(field.choices) == 1:
                hide_field(field, default=field.choices[0][0])
        
        super(TeacherClassRegForm, self).__init__(*args, **kwargs)
        
        prog = module.program
        
        section_numbers = module.allowed_sections_actual
        section_numbers = zip(section_numbers, section_numbers)
        
        class_sizes = module.getClassSizes()
        class_sizes = zip(class_sizes, class_sizes)
        
        class_grades = module.getClassGrades()
        class_grades = zip(class_grades, class_grades)
        
        # num_sections: section_list; hide if useless
        self.fields['num_sections'].choices = section_numbers
        hide_choice_if_useless( self.fields['num_sections'] )
        # category: program.class_categories.all()
        self.fields['category'].choices = [ (x.id, x.category) for x in prog.class_categories.all() ]
        # grade_min, grade_max: module.getClassGrades
        self.fields['grade_min'].choices = class_grades
        self.fields['grade_max'].choices = class_grades
        # class_size_max: module.getClassSizes
        self.fields['class_size_max'].choices = class_sizes
        self.fields['class_size_optimal'].choices = class_sizes
        # global_resources: module.getResourceTypes(is_global=True)
        self.fields['global_resources'].choices = module.getResourceTypes(is_global=True)
        # resources: module.getResourceTypes(is_global=False)
        resource_choices = module.getResourceTypes(is_global=False)
        
        # decide whether to display certain fields
        # resources
        if len(resource_choices) > 0:
            self.fields['resources'].choices = resource_choices
        else:
            self.fields['resources'].widget = forms.HiddenInput()
        
        # prereqs
        if not module.set_prereqs:
            self.fields['prereqs'].widget = forms.HiddenInput()
        
        # allow_lateness
        if not module.allow_lateness:
            self.fields['allow_lateness'].widget = forms.HiddenInput()
            self.fields['allow_lateness'].initial = 'False'
        
        #  viable_times vs. duration
        if module.display_times:
            if module.times_selectmultiple:
                self.fields['viable_times'] = forms.MultipleChoiceField( label='Viable Times', choices=module.getTimes(), widget=forms.CheckboxSelectMultiple() )
            else:
                self.fields['viable_times'].choices = module.getTimes()
        else:
            del self.fields['viable_times']
        if module.times_selectmultiple or not module.display_times:
            self.fields['duration'].choices = sorted(module.getDurations())
        hide_choice_if_useless( self.fields['duration'] )
        
        # session_count
        if module.session_counts:
            session_count_choices = module.session_counts_ints
            session_count_choices = zip(session_count_choices, session_count_choices)
            self.fields['session_count'].choices = session_count_choices
        hide_choice_if_useless( self.fields['session_count'] )
        
        # requested_room
        if not module.ask_for_room:
            hide_field( self.fields['requested_room'] )
            
        #   Hide resource fields since separate forms are now being used. - Michael P
        resource_fields = ['has_own_space', 'global_resources', 'resources', 'requested_special_resources']
        for field in resource_fields:
            self.fields[field].widget = forms.HiddenInput()
        
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
                self._errors['grade_min'] = forms.util.ErrorList([msg])
                self._errors['grade_max'] = forms.util.ErrorList([msg])
                del cleaned_data['grade_min']
                del cleaned_data['grade_max']

        # Make sure the optimal class size <= maximum class size.
        class_size_optimal = cleaned_data.get('class_size_optimal')
        class_size_max = cleaned_data.get('class_size_max')
        if class_size_optimal and class_size_max:
            class_size_optimal = int(class_size_optimal)
            class_size_max = int(class_size_max)
            if class_size_optimal > class_size_max:
                msg = u'Optimal class size must be less than or equal to the maximum class size.'
                self._errors['class_size_optimal'] = forms.util.ErrorList([msg])
                self._errors['class_size_max'] = forms.util.ErrorList([msg])
                del cleaned_data['class_size_optimal']
                del cleaned_data['class_size_max']

        if class_size_optimal == '':
            cleaned_data['class_size_optimal'] = None
        
        # Return cleaned data
        return cleaned_data


class TeacherEventSignupForm(FormWithRequiredCss):
    """ Form for teachers to pick interview and teacher training times. """
    interview = forms.ChoiceField( label='Interview', choices=[], required=False, widget=BlankSelectWidget(blank_choice=('', 'Pick an interview timeslot...')) )
    training  = forms.ChoiceField( label='Teacher Training', choices=[], required=False, widget=BlankSelectWidget(blank_choice=('', 'Pick a teacher training session...')) )
    
    def _slot_is_taken(self, anchor):
        """ Determine whether an interview slot is taken. """
        return self.module.bitsBySlot(anchor).count() > 0

    def _slot_is_mine(self, anchor):
        """ Determine whether an interview slot is taken by you. """
        return self.module.bitsBySlot(anchor).filter(user=self.user).count() > 0

    def _slot_too_late(self, anchor):
        """ Determine whether it is too late to register for a time slot. """
        # Don't allow signing up for a spot less than 3 days in advance
        return Event.objects.get(anchor=anchor).start - datetime.now() < timedelta(days=3)

    def _slot_is_available(self, anchor):
        """ Determine whether a time slot is available. """
        return self._slot_is_mine(anchor) or (not self._slot_is_taken(anchor) and not self._slot_too_late(anchor))
    
    def _get_datatree(self, id):
        """ Given an ID, get the datatree node with that ID. """
        try:
            return DataTree.objects.get(id=id)
        except (DoesNotExist, ValueError):
            raise forms.ValidationError('The time you selected seems not to exist. Please try a different one.')
    
    def __init__(self, module, *args, **kwargs):
        super(TeacherEventSignupForm, self).__init__(*args, **kwargs)
        self.module = module
        self.user = module.user
        
        interview_times = module.getTimes('interview')
        if interview_times.count() > 0:
            self.fields['interview'].choices = [ (x.anchor.id, x.description) for x in interview_times if self._slot_is_available(x.anchor) ]
        else:
            self.fields['interview'].widget = forms.HiddenInput()
        
        training_times = module.getTimes('training')
        if training_times.count() > 0:
            self.fields['training'].choices = [ (x.anchor.id, x.description) for x in training_times ]
        else:
            self.fields['training'].widget = forms.HiddenInput()
    
    def clean_interview(self):
        data = self.cleaned_data['interview']
        if not data:
            return data
        data = self._get_datatree( data )
        if not self._slot_is_available(data):
            raise forms.ValidationError('That time is taken; please select a different one.')
        return data
    
    def clean_training(self):
        data = self.cleaned_data['training']
        if not data:
            return data
        return self._get_datatree( data )



