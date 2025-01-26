
from __future__ import absolute_import
from six.moves import map
import six
from six.moves import zip
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

from django.conf import settings
from esp.middleware import ESPError
from esp.users.models import StudentInfo, K12School, RecordType
from esp.program.models import Program, ProgramModule, ClassFlag, ClassFlagType, ClassCategories
from esp.dbmail.models import PlainRedirect
from esp.utils.widgets import DateTimeWidget
from django import forms
from django.core import validators
from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from form_utils.forms import BetterModelForm, BetterForm
from django.utils.safestring import mark_safe
from esp.tagdict import all_global_tags, tag_categories
from esp.tagdict.models import Tag
from collections import OrderedDict

def make_id_tuple(object_list):
    return tuple([(o.id, str(o)) for o in object_list])

class ProgramCreationForm(BetterModelForm):
    """ Massive form for creating a new instance of a program. """

    term = forms.SlugField(label=mark_safe('Term or year, in URL form (e.g. <tt>2007_Fall</tt>)'), widget=forms.TextInput(attrs={'size': '40'}))
    term_friendly = forms.CharField(label=mark_safe('Term, in English (e.g. <tt>Fall 2007</tt>)'), widget=forms.TextInput(attrs={'size': '40'}))

    teacher_reg_start = forms.DateTimeField(widget = DateTimeWidget())
    teacher_reg_end   = forms.DateTimeField(widget = DateTimeWidget())
    student_reg_start = forms.DateTimeField(widget = DateTimeWidget())
    student_reg_end   = forms.DateTimeField(widget = DateTimeWidget())
    base_cost         = forms.IntegerField(label = 'Cost of Program Admission $', min_value = 0 )
    sibling_discount  = forms.DecimalField(max_digits=9, decimal_places=2, required=False, initial=None,
                                           help_text="The amount of the sibling discount. Leave blank if you don't use sibling discounts.")
    program_type      = forms.CharField(label = "Program Type", help_text='e.g. Splash or Cascade')
    program_module_questions   = forms.MultipleChoiceField(choices=[],
                                                           label='Program Modules',
                                                           widget=forms.CheckboxSelectMultiple(),
                                                           help_text=Program.program_modules.field.help_text,
                                                           required=False)

    def __init__(self, *args, **kwargs):
        """ Used to update ChoiceFields with the current modules. """
        # These modules are the "choosable" ones that admins will usually want to choose to select or exclude (i.e. not automatically include or exclude)
        self.program_module_question_ids = OrderedDict([('Will you charge for items such as shirts or lunch?', [x.id for x in ProgramModule.objects.filter(admin_title__in=['Student Optional Fees', 'Accounting', 'Financial Aid Application', 'Easily Approve Financial Aid Requests', 'Line Items Module'])]),
                                                        ('If you will charge for admission or other costs, will you accept payment by credit card?', [x.id for x in ProgramModule.objects.filter(admin_title__in=['Credit Card Payment Module (Stripe)', 'Credit Card View Module'])]),
                                                        ('Do you want a pre-program quiz for teachers?', [x.id for x in ProgramModule.objects.filter(admin_title='Teacher Logistics Quiz')]),
                                                        ('Will you have any additional non-survey forms that teachers should fill out?', [x.id for x in ProgramModule.objects.filter(admin_title='Teacher Custom Form')]),
                                                        ('Will you have any (non-survey) forms that students should fill out?', [x.id for x in ProgramModule.objects.filter(admin_title='Student Custom Form')]),
                                                        ('Will you have more than one lunch period (per day)?', [x.id for x in ProgramModule.objects.filter(admin_title='Student Lunch Period Selection')]),
                                                        ('Would you be willing to solicit donations for LU?', [x.id for x in ProgramModule.objects.filter(admin_title='Donation Module')]),
                                                        ('Do you plan to have teacher training or interviews?', [x.id for x in ProgramModule.objects.filter(admin_title__in=['Teacher Training and Interview Signups', 'Manage Teacher Training and Interviews'])]),
                                                        (mark_safe('Will you use lottery admission (as opposed to first come, first served) for <b>classes</b>?'), [x.id for x in ProgramModule.objects.filter(admin_title__in=['Two-Phase Student Registration', 'Lottery Frontend'])]),
                                                        (mark_safe('Will you use lottery registration (as opposed to first come, first served) to the <b>program</b>?'), [x.id for x in ProgramModule.objects.filter(admin_title__in=['Student Registration Phase Zero', 'Manage Student Registration Phase Zero'])]),
                                                        ('Will you let students enter a lottery to switch classes after the program has started?', [x.id for x in ProgramModule.objects.filter(admin_title='Class Change Request')]),
                                                        ('Will you have students accept some sort of agreement?', [x.id for x in ProgramModule.objects.filter(admin_title='Student Acknowledgement')]),
                                                        ('Do students have to apply to individual classes?', [x.id for x in ProgramModule.objects.filter(admin_title__in=['Application Review for Admin', 'Admin Admissions Dashboard'])]),
                                                        ('If yes, can teachers admit them (as opposed to just admins)?', [x.id for x in ProgramModule.objects.filter(admin_title__in=['Teacher Admissions Dashboard', 'Application Reviews for Teachers', 'Application Review for Admin', 'Admin Admissions Dashboard'])]),
                                                        ('Will you have moderators or assistants for individual class sections?', [x.id for x in ProgramModule.objects.filter(admin_title='Moderator Signup')]),
                                                        ('Do you want students to be able to download a completion certificate after the program ends?', [x.id for x in ProgramModule.objects.filter(admin_title='Student Certificate Module')]),
                                                       ])
        # Include additional or new modules that haven't been added to the list
        for x in ProgramModule.objects.filter(choosable=0):
            if x.id not in sum(list(self.program_module_question_ids.values()), []): # flatten list of modules
                self.program_module_question_ids['Would you like to include the {} module?'.format(x.admin_title)] = [x.id]
        # Now initialize the form
        super(ProgramCreationForm, self).__init__(*args, **kwargs)
        self.fields['program_module_questions'].choices = [(','.join(map(str, ids)), q) for q, ids in self.program_module_question_ids.items()]
        #self.fields['program_modules'].choices = make_id_tuple(ProgramModule.objects.all())
        self.fields['program_modules'].required = False
        #   Enable validation on other fields
        self.fields['program_size_max'].required = True
        self.fields['program_size_max'].validators.append(validators.MaxValueValidator((1 << 31) - 1))


    def save(self, commit=True):
        self.instance.url = self.cleaned_data['new_url']
        self.instance.name = self.cleaned_data['new_name']
        return super(ProgramCreationForm, self).save(commit=commit)


    def load_program(self, program):
        #   Copy the data in the program into the form so that we don't have to re-select modules and stuff.
        pass

    def clean_program_modules(self):
        mods = list(self.cleaned_data['program_modules'])[:] # take a copy of the list to be safe
        # Add "include by default" modules (choosable property = 1)
        mods.extend(ProgramModule.objects.filter(choosable=1))
        return list(set(mods)) # Database wants a unique collection, so take set

    def clean(self):
        '''
        Takes the program creation form's program_type, term, and term_friendly
        fields, and constructs the url and name fields on the Program instance.
        '''
        super(ProgramCreationForm, self).clean()
        if 'term' in self.cleaned_data and 'term_friendly' in self.cleaned_data:
            #   Filter out unwanted characters from program type to form URL
            ptype_slug = re.sub('[-\s]+', '_', re.sub('[^\w\s-]', '', unicodedata.normalize('NFKD', self.cleaned_data['program_type'])).strip())
            new_url = six.u('%(type)s/%(term)s') \
                % {'type': ptype_slug
                  ,'term': self.cleaned_data['term']
                  }
            new_name = six.u('%(type)s %(term)s') \
                % {'type': self.cleaned_data['program_type']
                  ,'term': self.cleaned_data['term_friendly']
                  }
            self.cleaned_data['new_url'] = new_url
            self.cleaned_data['new_name'] = new_name
            # Check that there isn't another program with this URL or name
            if Program.objects.filter(url=new_url).exclude(id=self.instance.id).exists():
                self.add_error('term', "A %s program already exists with this URL. Please choose a new URL or change the URL of the old program." % self.cleaned_data['program_type'])
            if Program.objects.filter(name=new_name).exclude(id=self.instance.id).exists():
                self.add_error('term_friendly', "A %s program already exists with this name. Please choose a new name or change the name of the old program." % self.cleaned_data['program_type'])

    class Meta:
        fieldsets = [
                     ('Program Title', {'fields': ['term', 'term_friendly'] }),
                     ('Program Constraints', {'fields':['grade_min', 'grade_max', 'program_size_max', 'program_allow_waitlist']}),
                     ('About Program Creator', {'fields':['director_email', 'director_cc_email', 'director_confidential_email']}),
                     ('Financial Details', {'fields':['base_cost', 'sibling_discount']}),
                     ('Program Internal Details', {'fields':['program_type', 'program_modules', 'program_module_questions', 'class_categories', 'flag_types']}),
                     ('Registration Dates', {'fields': ['teacher_reg_start', 'teacher_reg_end', 'student_reg_start', 'student_reg_end'],}),
        ]                      # Here You can also add description for each fieldset.
        widgets = {
            'program_modules': forms.SelectMultiple(attrs={'class': 'hidden-field'}),
        }
        model = Program
ProgramCreationForm.base_fields['director_email'].widget = forms.EmailInput(attrs={'size': 40,
                                                                                   'pattern': r'(^.+@%s$)|(^.+@(\w+\.)?learningu\.org$)' % settings.SITE_INFO[1].replace('.', '\.')})
ProgramCreationForm.base_fields['director_cc_email'].widget = forms.EmailInput(attrs={'size': 40})
ProgramCreationForm.base_fields['director_confidential_email'].widget = forms.EmailInput(attrs={'size': 40})
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
        ('student_reg', 'How many students registered?'),
        ('teacher_reg', 'How many teachers registered?'),
        ('class_reg', 'How many classes were registered by teachers?'),
        #   (other queries here)
    )

    #   Keys into the program.students() dictionary (and descriptions)
    student_reg_categories = (
        ('student_profile', 'Created a profile'),
        ('confirmed', 'Confirmed registration'),
        ('attended', 'Marked as attended on the Web site'),
        ('classreg', 'Registered for at least one class'),
        ('student_survey', 'Completed the online survey'),
    )

    #   Keys into the program.students() dictionary (and descriptions)
    teacher_reg_categories = (
        ('teacher_profile', 'Created a profile'),
        ('class_proposed', 'Proposed a class'),
        ('class_approved', 'Had a class approved'),
        ('class_rejected', 'Had a class rejected'),
        ('teacher_survey', 'Completed the online survey'),
    )

    @staticmethod
    def get_program_type_choices():
        programs = Program.objects.all()
        names_url = sorted({x.program_type for x in programs})
        result = list(zip(names_url, names_url))
        return result

    @staticmethod
    def get_program_instance_choices(program_name):
        programs = Program.objects.all()
        names_url = [x.url for x in programs]
        names_friendly = [x.name for x in programs]
        result = sorted(zip(names_url, names_friendly), key=lambda pair: pair[0])
        result = [x for x in result if len(x[1]) > 0]
        return result

    @staticmethod
    def get_school_choices():
        k12schools = K12School.objects.all().order_by('name')
        schools = list(set(StudentInfo.objects.all().exclude(school__isnull=True).exclude(school='').values_list('school', flat=True)))
        result = []
        for school in k12schools:
            result.append(('K12:%d' % school.id, school.name))
        for school in schools:
            result.append(('Sch:%s' % school, school))
        result.sort(key=lambda x: x[1])
        return result

    query = forms.ChoiceField(choices=stats_questions, widget=forms.Select(), help_text='What question would you like to ask?')
    limit = forms.IntegerField(required=False, min_value=0, widget=forms.TextInput(), help_text='Limit number of aggregate results to display (leave blank or enter 0 to display all results)')

    program_type_all = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput(), label='Search All Programs?', help_text='Uncheck to select program type(s)')
    program_type = forms.ChoiceField(required=False, choices=((None, ''),), widget=forms.Select())
    program_instance_all = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(), label='Search All Instances?', help_text='Uncheck to select specific instance(s)')
    program_instances = forms.MultipleChoiceField(required=False, choices=((None, ''),), widget=forms.SelectMultiple(), label='Instance(s) of Program')  #   Choices will be replaced by Ajax request if necessary

    student_reg_type_all = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(), label='Search All Students?', help_text='Uncheck to select student registration type(s)')
    student_reg_types = forms.MultipleChoiceField(required=False, choices=student_reg_categories, widget=forms.SelectMultiple(), label='Registration Categories')
    teacher_reg_type_all = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(), label='Search All Teachers?', help_text='Uncheck to select teacher registration type(s)')
    teacher_reg_types = forms.MultipleChoiceField(required=False, choices=teacher_reg_categories, widget=forms.SelectMultiple(), label='Registration Categories')

    school_query_type = forms.ChoiceField(choices=(('all', 'Match any school'), ('name', 'Enter partial school name')), initial='all', widget=forms.RadioSelect(), label='School Query Type')
    school_name = forms.CharField(required=False, widget=forms.TextInput(), label='[Partial] School Name')
    school_multisel = forms.MultipleChoiceField(required=False, choices=(), widget=forms.SelectMultiple(), label='School(s)', help_text='Hold down Ctrl to select more than one')

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

        school_choices = StatisticsQueryForm.get_school_choices()
        if len(school_choices) > 0:
            self.fields['school_query_type'].choices = (('all', 'Match any school'), ('name', 'Enter partial school name'), ('list', 'Select school(s) from list'))
            self.fields['school_multisel'].choices = school_choices

    def clean(self):
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

        if 'query' in data and data['query'] in ['teacher_reg', 'class_reg']:
            #   Hide fields that don't apply to teachers
            self.hide_field('student_reg_types')
            self.hide_field('school_query_type')
            self.hide_field('student_reg_type_all')
            if 'teacher_reg_type_all' in data and data['teacher_reg_type_all']:
                self.hide_field('teacher_reg_types')
        else:
            #   Hide fields that don't apply to students
            self.hide_field('teacher_reg_types')
            self.hide_field('teacher_reg_type_all')
            if 'student_reg_type_all' in data and data['student_reg_type_all']:
                self.hide_field('student_reg_types')

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
        fields = ['subject', 'flag_type', 'comment']

class FlagTypeForm(forms.ModelForm):
    class Meta:
        model = ClassFlagType
        fields = ['name', 'color', 'seq', 'show_in_scheduler', 'show_in_dashboard']

class RecordTypeForm(forms.ModelForm):
    def clean_name(self):
        name = self.cleaned_data.get('name').strip()
        if name in RecordType.BUILTIN_TYPES:
            raise forms.ValidationError('You can not add/edit a built-in record type.')
        else:
            return name
    class Meta:
        model = RecordType
        fields = ['name', 'description']

class CategoryForm(forms.ModelForm):
    class Meta:
        model = ClassCategories
        fields = ['category', 'symbol', 'seq']
        widgets = {
            'symbol': forms.TextInput(attrs={'pattern': '[A-Za-z]{1}', 'title': 'Single letter'})
        }

class RedirectForm(forms.ModelForm):
    class Meta:
        model = Redirect
        fields = ['old_path', 'new_path']

class PlainRedirectForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PlainRedirectForm, self).__init__(*args, **kwargs)
        self.fields['original'].help_text = 'A real or custom email address name (e.g., "directors" or "splash"). Any emails to &lt;original&gt;@%s will be redirected to the destination email address(es).' % Site.objects.get_current().domain
    class Meta:
        model = PlainRedirect
        fields = ['original', 'destination']

class TagSettingsForm(BetterForm):
    """ Form for changing global tags. """
    def __init__(self, *args, **kwargs):
        self.categories = set()
        super(TagSettingsForm, self).__init__(*args, **kwargs)
        for key in all_global_tags:
            # generate field for each tag
            tag_info = all_global_tags[key]
            if tag_info.get('is_setting', False):
                self.categories.add(tag_info.get('category'))
                field = tag_info.get('field')
                # Some field widgets need to be setup manually because we can't do it during compilation
                if key == 'teacher_profile_hide_fields':
                    from esp.users.forms.user_profile import TeacherProfileForm
                    self.fields[key] = forms.MultipleChoiceField(choices=[(field[0], field[0]) for field in TeacherProfileForm.declared_fields.items() if not field[1].required])
                elif key == 'student_profile_hide_fields':
                    from esp.users.forms.user_profile import StudentProfileForm
                    self.fields[key] = forms.MultipleChoiceField(choices=[(field[0], field[0]) for field in StudentProfileForm.declared_fields.items() if not field[1].required])
                elif key == 'volunteer_profile_hide_fields':
                    from esp.users.forms.user_profile import VolunteerProfileForm
                    self.fields[key] = forms.MultipleChoiceField(choices=[(field[0], field[0]) for field in VolunteerProfileForm.declared_fields.items() if not field[1].required])
                elif key == 'educator_profile_hide_fields':
                    from esp.users.forms.user_profile import EducatorProfileForm
                    self.fields[key] = forms.MultipleChoiceField(choices=[(field[0], field[0]) for field in EducatorProfileForm.declared_fields.items() if not field[1].required])
                elif key == 'guardian_profile_hide_fields':
                    from esp.users.forms.user_profile import GuardianProfileForm
                    self.fields[key] = forms.MultipleChoiceField(choices=[(field[0], field[0]) for field in GuardianProfileForm.declared_fields.items() if not field[1].required])
                elif field is not None:
                    self.fields[key] = field
                elif tag_info.get('is_boolean', False):
                    self.fields[key] = forms.BooleanField()
                else:
                    self.fields[key] = forms.CharField()
                self.fields[key].help_text = tag_info.get('help_text', '')
                self.fields[key].initial = self.fields[key].default = tag_info.get('default')
                self.fields[key].required = False
                set_val = Tag.getBooleanTag(key) if tag_info.get('is_boolean', False) else Tag.getTag(key)
                if set_val is not None and set_val != self.fields[key].initial:
                    if isinstance(self.fields[key], forms.MultipleChoiceField):
                        set_val = set_val.split(",")
                    self.fields[key].initial = set_val

    def save(self):
        for key in all_global_tags:
            # Update tags if necessary
            tag_info = all_global_tags[key]
            if tag_info.get('is_setting', False):
                set_val = self.cleaned_data[key]
                if isinstance(set_val, list):
                    set_val = ",".join(set_val)
                if not set_val in ("", "None", None, tag_info.get('default')):
                    # Set a [new] tag if a value was provided and the value is not the default
                    Tag.setTag(key, value=set_val)
                else:
                    # Otherwise, delete the old tag, if there is one
                    Tag.unSetTag(key)

    class Meta:
        fieldsets = [(cat, {'fields': [key for key in sorted(all_global_tags.keys()) if all_global_tags[key].get('category') == cat], 'legend': tag_categories[cat]}) for cat in tag_categories.keys()]
