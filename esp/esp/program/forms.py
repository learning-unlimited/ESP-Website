
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
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

import re
import unicodedata

from esp.users.models import StudentInfo, K12School
from esp.datatree.models import *
from esp.program.models import Program, ProgramModule, ClassFlag
from esp.utils.widgets import DateTimeWidget
from django import forms
from django.core import validators
from form_utils.forms import BetterModelForm


def make_id_tuple(object_list):
    return tuple([(o.id, str(o)) for o in object_list])

class ProgramCreationForm(BetterModelForm):
    """ Massive form for creating a new instance of a program. """
    
    term = forms.SlugField(label='Term or year, in URL form (i.e. "2007_Fall")', widget=forms.TextInput(attrs={'size': '40'}))
    term_friendly = forms.CharField(label='Term, in English (i.e. "Fall 07")', widget=forms.TextInput(attrs={'size': '40'}))
    
    teacher_reg_start = forms.DateTimeField(widget = DateTimeWidget())
    teacher_reg_end   = forms.DateTimeField(widget = DateTimeWidget())
    student_reg_start = forms.DateTimeField(widget = DateTimeWidget())
    student_reg_end   = forms.DateTimeField(widget = DateTimeWidget())
    base_cost         = forms.IntegerField( label = 'Cost of Program Admission $', min_value = 0 )
    sibling_discount  = forms.DecimalField(max_digits=9, decimal_places=2, required=False, initial=None, help_text='The amount of the sibling discount. Leave blank to disable sibling discounts.')
    program_type      = forms.CharField(label = "Program Type")
    program_modules   = forms.MultipleChoiceField(
                          choices=[],
                          label='Program Modules',
                          widget=forms.SelectMultiple(attrs={'class': 'input-xxlarge'}),
                          help_text=Program.program_modules.field.help_text)

    def __init__(self, *args, **kwargs):
        """ Used to update ChoiceFields with the current modules. """
        super(ProgramCreationForm, self).__init__(*args, **kwargs)
        self.fields['program_modules'].choices = make_id_tuple(ProgramModule.objects.all())

        #   Enable validation on other fields
        self.fields['program_size_max'].required = True
        self.fields['program_size_max'].validators.append(validators.MaxValueValidator((1 << 31) - 1))

    def save(self, commit=True):
        '''
        Takes the program creation form's program_type, term, and term_friendly
        fields, and constructs the url and name fields on the Program instance;
        then calls the superclass's save() method.
        '''
        #   Filter out unwanted characters from program type to form URL
        ptype_slug = re.sub('[-\s]+', '_', re.sub('[^\w\s-]', '', unicodedata.normalize('NFKD', self.cleaned_data['program_type']).encode('ascii', 'ignore')).strip())
        self.instance.url = u'%(type)s/%(instance)s' \
            % {'type': ptype_slug
              ,'instance': self.cleaned_data['term']
              }
        self.instance.name = u'%(type)s %(instance)s' \
            % {'type': self.cleaned_data['program_type']
              ,'instance': self.cleaned_data['term_friendly']
              }
        return super(ProgramCreationForm, self).save(commit=commit)

    def load_program(self, program):
        #   Copy the data in the program into the form so that we don't have to re-select modules and stuff.
        pass

    def clean_program_modules(self):
        value = self.cleaned_data['program_modules']
        value = map(int, value)
        json_module = ProgramModule.objects.get(handler=u'JSONDataModule')
        # If the JSON Data Module isn't already in the list of selected
        # program modules, add it. The JSON Data Module is a dependency for
        # many commonly-used modules, so it is important that it be enbabled
        # by default for all new programs.
        if json_module.id not in value:
            value.append(json_module.id)
        return value


    class Meta:
        fieldsets = [
('Program Title', {'fields': ['term', 'term_friendly'] }),
                     ('Program Constraints', {'fields':['grade_min','grade_max','program_size_max','program_allow_waitlist']}),
                     ('About Program Creator',{'fields':['director_email', 'director_cc_email', 'director_confidential_email']}),
                     ('Financial Details' ,{'fields':['base_cost','sibling_discount']}),
                     ('Program Internal details' ,{'fields':['program_type','program_modules','class_categories','flag_types']}),
                     ('Registrations Date',{'fields':['teacher_reg_start','teacher_reg_end','student_reg_start','student_reg_end'],}),


]                      # Here You can also add description for each fieldset.

        model = Program
ProgramCreationForm.base_fields['director_email'].widget = forms.TextInput(attrs={'size': 40})
ProgramCreationForm.base_fields['director_cc_email'].widget = forms.TextInput(attrs={'size': 40})
ProgramCreationForm.base_fields['director_confidential_email'].widget = forms.TextInput(attrs={'size': 40})
'''        
ProgramCreationForm.base_fields['term'].line_group = -4
ProgramCreationForm.base_fields['term_friendly'].line_group = -4

ProgramCreationForm.base_fields['grade_min'].line_group = -3
ProgramCreationForm.base_fields['grade_max'].line_group = -3

ProgramCreationForm.base_fields['director_email'].widget = forms.TextInput(attrs={'size': 40})
ProgramCreationForm.base_fields['director_email'].line_group = -1

ProgramCreationForm.base_fields['teacher_reg_start'].line_group = 2
ProgramCreationForm.base_fields['teacher_reg_end'].line_group = 2
ProgramCreationForm.base_fields['student_reg_start'].line_group = 3
ProgramCreationForm.base_fields['student_reg_end'].line_group = 3        
ProgramCreationForm.base_fields['publish_start'].line_group = 1
ProgramCreationForm.base_fields['publish_end'].line_group = 1

ProgramCreationForm.base_fields['base_cost'].line_group = 4
ProgramCreationForm.base_fields['sibling_discount'].line_group = 4
'''

class StatisticsQueryForm(forms.Form):

    #   Types of queries (each is handled in the statistics view in esp/program/views.py)
    stats_questions = (
        ('demographics', 'What were the aggregate demographics (grade, age, etc.)?'),
        ('zipcodes', 'What were the most common zip codes for students to come from?'),
        ('schools', 'What were the most common schools for students to come from?'),
        ('startreg', 'When did the students begin registering?'),
        ('repeats', 'What other programs have the students attended?'),
        ('heardabout', 'How did the students hear about the program?'),
        ('hours', 'How many hours of class did the students take and when?'),
        #   Not yet implemented
        #   ('classes', 'What were the most and least popular classes?'),
        #   (other queries here)
    )

    #   Keys into the program.students() dictionary (and descriptions)
    reg_categories = (
        ('confirmed', 'Confirmed registration'),
        ('attended', 'Marked as attended on the Web site'),
        ('classreg', 'Registered for at least one class'),
        ('student_survey', 'Completed the online survey'),
    )

    @staticmethod
    def get_program_type_choices():
        programs = Program.objects.all()
        names_url = list(set([x.program_type for x in programs]))
        names_url.sort()
        result = zip(names_url, names_url)
        return result
        
    @staticmethod
    def get_program_instance_choices(program_name):
        programs = Program.objects.all()
        names_url = [x.url for x in programs]
        names_friendly = [x.name for x in programs]
        result = sorted(zip(names_url, names_friendly), key=lambda pair: pair[0])
        result = filter(lambda x: len(x[1]) > 0, result)
        return result

    @staticmethod
    def get_school_choices():
        k12schools = K12School.objects.all().order_by('name')
        schools = list(set(StudentInfo.objects.all().values_list('school', flat=True)))
        result = []
        for school in k12schools:
            result.append(('K12:%d' % school.id, school.name))
        for school in schools:
            result.append(('Sch:%s' % school, school))
        result.sort(key=lambda x: x[1])
        return result

    query = forms.ChoiceField(choices=stats_questions, widget=forms.Select(), help_text='What question would you like to ask?')
    limit = forms.IntegerField(required=False, min_value=0, widget=forms.TextInput(), help_text='Limit number of aggregate results to display (leave blank or enter 0 to display all results)')

    program_type_all = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput(), label='Search All Programs?', help_text='Uncheck to select a program type')
    program_type = forms.ChoiceField(required=False, choices=((None, ''),), widget=forms.Select(), help_text='Type of Program')
    program_instance_all = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(), label='Search All Instances?', help_text='Uncheck to select specific instances')
    program_instances = forms.MultipleChoiceField(required=False, choices=((None, ''),), widget=forms.SelectMultiple(), label='Instance[s] of Program')  #   Choices will be replaced by Ajax request if necessary
    
    reg_types = forms.MultipleChoiceField(choices=reg_categories, widget=forms.SelectMultiple(), initial=['classreg'], label='Registration Categories')
    
    school_query_type = forms.ChoiceField(choices=(('all', 'Match any school'), ('name', 'Enter partial school name'), ('list', 'Select school[s] from list')), initial='all', widget=forms.RadioSelect(), label='School Query Type')
    school_name = forms.CharField(required=False, widget=forms.TextInput(), label='[Partial] School Name')
    school_multisel = forms.MultipleChoiceField(required=False, choices=(), widget=forms.SelectMultiple(), label='School[s]', help_text='Hold down Ctrl to select more than one')
    
    zip_query_type = forms.ChoiceField(choices=(('all', 'Any Zip code'), ('exact', 'Exact match'), ('partial', 'Partial match'), ('distance', 'Distance from Zip code')), initial='all', widget=forms.RadioSelect(), label='Zip Code Query Type')
    zip_code = forms.CharField(required=False, widget=forms.TextInput())
    zip_code_partial = forms.CharField(required=False, widget=forms.TextInput(), label='Beginning digits of Zip code')
    zip_code_distance = forms.IntegerField(required=False, widget=forms.TextInput(), label='Maximum distance from Zip code', help_text='Enter an integer distance in miles')
    
    def __init__(self, *args, **kwargs):
        if 'program' in kwargs:
            #   placeholder for later:
            del kwargs['program']
            
        super(StatisticsQueryForm, self).__init__(*args, **kwargs)
        
        self.fields['program_type'].choices = StatisticsQueryForm.get_program_type_choices()
        self.fields['program_instances'].choices = StatisticsQueryForm.get_program_instance_choices(self.fields['program_type'].choices[0][0])
        
        #   This will be done later if they ask
        #   self.fields['school_multisel'].choices = StatisticsQueryForm.get_school_choices()

    def clean(self):
        #   print self.cleaned_data
        
        """ Check that either 'All Programs' is selected or a program is selected   """
        if not self.cleaned_data['program_type_all']:
            if not self.cleaned_data['program_type']:
                if len(self.fields['program_type'].choices) > 1:
                    raise forms.ValidationError('Please select at least one program type if you have not checked "All Programs."')
                else:
                    self.cleaned_data['program_type'] = self.fields['program_type'].choices[0][0]
                
        """ Check that either 'All Instances' is selected or an instance is selected """
        if not self.cleaned_data['program_type_all'] and not self.cleaned_data['program_instance_all']:
            if 'program_instances' not in self.cleaned_data or not self.cleaned_data['program_instances']:
                raise forms.ValidationError('Please select at least one instance if you have not checked "All Programs" or "All Instances."')

        """ Check that school_name or school_multisel is filled out """
        if self.cleaned_data['school_query_type'] == 'name':
            if 'school_name' not in self.cleaned_data or len(self.cleaned_data['school_name'].strip()) == 0:
                raise forms.ValidationError('Please enter a school name or name fragment.')
        elif self.cleaned_data['school_query_type'] == 'list':
            if 'school_multisel' not in self.cleaned_data or len(self.cleaned_data['school_multisel']) == 0:
                raise forms.ValidationError('Please select at least one school from the list.')
        
        """ Check that the appropriate zip code fields are filled out """
        if self.cleaned_data['zip_query_type'] in ['exact', 'distance']:
            if not self.cleaned_data['zip_code'] or len(self.cleaned_data['zip_code']) != 5 or not self.cleaned_data['zip_code'].isnumeric():
                raise forms.ValidationError('Please enter a 5-digit zip code to match.')
        elif self.cleaned_data['zip_query_type'] == 'partial':
            if not self.cleaned_data['zip_code_partial'] or len(self.cleaned_data['zip_code_partial']) > 5 or not self.cleaned_data['zip_code_partial'].isnumeric():
                raise forms.ValidationError('Please enter a partial zip code (1-4 digits) to match.')
        if self.cleaned_data['zip_query_type'] == 'distance':
            if not self.cleaned_data['zip_code_distance']:
                raise forms.ValidationError('Please enter a zip code and a radius to search within.')
        
        return self.cleaned_data

    def hide_field(self, field_name, default=None):
        self.fields[field_name]._old_widget = self.fields[field_name].widget
        self.fields[field_name].widget = forms.HiddenInput()
        if default:
            self.fields[field_name].initial = default

    def disable_field(self, field_name):
        self.fields[field_name].widget.attrs['disabled'] = 'disabled'

    def disable_if_useless(self, field_name, linked_fields=[]):
        if hasattr(self.fields[field_name], 'choices') and len(self.fields[field_name].choices) == 1:
            self.fields[field_name].initial = self.fields[field_name].choices[0][0]
            self.disable_field(field_name)
            for field in linked_fields:
                self.disable_field(field)

    def hide_unwanted_fields(self):
        """ Function that should be called every time the form is rendered. """

        #   Unhide all fields (in case this function is run multiple times)
        for field_name in self.fields:
            if hasattr(self.fields[field_name], '_old_widget'):
                self.fields[field_name].widget = self.fields[field_name]._old_widget
            
        #   Populate data.  Start with default initial values and then add bound data if it's there.
        data = {}

        if self.is_bound:
            for key in self.data:
                data[key] = self.data.get(key)
            #   Force clean to get helpful cleaned_data dictionary
            if self.is_valid():
                data.update(self.cleaned_data)
        else:
            for field_name in self.fields:
                if hasattr(self.fields[field_name], 'initial') and self.fields[field_name].initial:
                    data[field_name] = self.fields[field_name].initial
            if hasattr(self, 'initial'):
                data.update(self.initial)

            
        #   Program selection
        if 'program_type_all' in data and data['program_type_all']:
            self.hide_field('program_type')
            self.hide_field('program_instance_all')
            self.hide_field('program_instances')
        elif 'program_instance_all' in data and data['program_instance_all']:
            self.hide_field('program_instances')
        self.disable_if_useless('program_type', ['program_type_all'])

        #   School selection
        if 'school_query_type' in data:
            if data['school_query_type'] == 'all':
                self.hide_field('school_name')
                self.hide_field('school_multisel')
            elif data['school_query_type'] == 'name':
                self.hide_field('school_multisel')
            elif data['school_query_type'] == 'list':
                self.hide_field('school_name')        

        #   Zip code selection
        if 'zip_query_type' in data:
            if data['zip_query_type'] == 'all':
                self.hide_field('zip_code')
                self.hide_field('zip_code_partial')
                self.hide_field('zip_code_distance')
            elif data['zip_query_type'] == 'exact':
                self.hide_field('zip_code_partial')
                self.hide_field('zip_code_distance')
            elif data['zip_query_type'] == 'partial':
                self.hide_field('zip_code')
                self.hide_field('zip_code_distance')
            elif data['zip_query_type'] == 'distance':
                self.hide_field('zip_code_partial')
                
        #   Limit queries
        if 'query' not in data or data['query'] not in ['zipcodes', 'heardabout', 'schools']:
            self.hide_field('limit')
            
    @staticmethod
    def get_multiselect_fields():
        result = []
        for field_name in StatisticsQueryForm.base_fields:
            if isinstance(StatisticsQueryForm.base_fields[field_name], forms.MultipleChoiceField):
                result.append(field_name)
        return result


class ClassFlagForm(forms.ModelForm):
    class Meta:
        model = ClassFlag
        fields = ['subject','flag_type','comment']
