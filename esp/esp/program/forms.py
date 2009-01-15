
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 MIT ESP

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

from esp.users.models import ESPUser, UserBit
from esp.datatree.models import *
from esp.program.models import Program, ProgramModule
from esp.utils.forms import new_callback, grouped_as_table, add_fields_to_class
from django.db.models import Q
from django import forms

def make_id_tuple(object_list):
    
    return tuple([(o.id, str(o)) for o in object_list])

class ProgramCreationForm(forms.ModelForm):
    """ Massive form for creating a new instance of a program. """
    anchor_choices = DataTree.objects.filter(Q(child_set__program__isnull=False) | Q(parent=GetNode("Q/Programs"))).exclude(parent__name="Subprograms").distinct()
    
    term = forms.CharField(label='Term or year, in URL form (i.e. "2007_Fall")', widget=forms.TextInput(attrs={'size': '40'}))
    term_friendly = forms.CharField(label='Term, in English (i.e. "Fall 07")', widget=forms.TextInput(attrs={'size': '40'}))
    
    admins            = forms.MultipleChoiceField(choices = [], label = 'Administrators')
    teacher_reg_start = forms.DateTimeField()
    teacher_reg_end   = forms.DateTimeField()
    student_reg_start = forms.DateTimeField()
    student_reg_end   = forms.DateTimeField()
    publish_start     = forms.DateTimeField(label = 'Program-Visible-on-Website Date')
    publish_end       = forms.DateTimeField(label = 'Program-Completely-Over Archive Date')
    base_cost         = forms.IntegerField( label = 'Cost of Program Admission $')
    finaid_cost       = forms.IntegerField( label = 'Cost to Students who receive Financial Aid $')
    anchor            = forms.ModelChoiceField(anchor_choices, label = "Program Type")
    program_modules   = forms.MultipleChoiceField(choices = [], label = 'Program Modules')

    def __init__(self, *args, **kwargs):
        """ Used to update ChoiceFields with the current admins and modules. """
        super(ProgramCreationForm, self).__init__(*args, **kwargs)
        ub_list = UserBit.objects.bits_get_users(GetNode('Q'), GetNode('V/Flags/UserRole/Administrator'))
        self.fields['admins'].choices = make_id_tuple([ub.user for ub in ub_list])
        self.fields['program_modules'].choices = make_id_tuple(ProgramModule.objects.all())

    def load_program(self, program):
        #   Copy the data in the program into the form so that we don't have to re-select modules and stuff.
        pass

    # use field grouping
    as_table = grouped_as_table

    class Meta:
        model = Program
        
ProgramCreationForm.base_fields['term'].line_group = -4
ProgramCreationForm.base_fields['term_friendly'].line_group = -4

ProgramCreationForm.base_fields['grade_min'].line_group = -3
ProgramCreationForm.base_fields['grade_max'].line_group = -3

ProgramCreationForm.base_fields['class_size_min'].line_group = -2
ProgramCreationForm.base_fields['class_size_max'].line_group = -2

ProgramCreationForm.base_fields['director_email'].widget = forms.TextInput(attrs={'size': 40})
ProgramCreationForm.base_fields['director_email'].line_group = -1

ProgramCreationForm.base_fields['teacher_reg_start'].line_group = 2
ProgramCreationForm.base_fields['teacher_reg_end'].line_group = 2
ProgramCreationForm.base_fields['student_reg_start'].line_group = 3
ProgramCreationForm.base_fields['student_reg_end'].line_group = 3        
ProgramCreationForm.base_fields['publish_start'].line_group = 1
ProgramCreationForm.base_fields['publish_end'].line_group = 1

ProgramCreationForm.base_fields['base_cost'].line_group = 4
ProgramCreationForm.base_fields['finaid_cost'].line_group = 4

