
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

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
from django.db import models
from esp.datatree.models import DataTree
from esp.program.modules.base import ProgramModuleObj
from esp.db.fields import AjaxForeignKey

class SATPrepAdminModuleInfo(models.Model):
    module        = models.ForeignKey(ProgramModuleObj)
    num_divisions = models.IntegerField(blank=True, null=True)
    
    class Admin:
        pass

class StudentClassRegModuleInfo(models.Model):
    module               = models.ForeignKey(ProgramModuleObj)
    enforce_max          = models.BooleanField(default=True)
    def __str__(self):
        return 'Student Class Reg Ext. for %s' % str(self.module)
    
    class Admin:
        pass

class ClassRegModuleInfo(models.Model):
    module               = models.ForeignKey(ProgramModuleObj)
    allow_coteach        = models.BooleanField(blank=True, null=True)
    set_prereqs          = models.BooleanField(blank=True, null=True)
    display_times        = models.BooleanField(blank=True, null=True)
    times_selectmultiple = models.BooleanField(blank=True, null=True)
    
    #   The maximum length of a class, in minutes.
    class_max_duration   = models.IntegerField(blank=True, null=True)
    
    class_max_size       = models.IntegerField(blank=True, null=True)
    
    class_size_step      = models.IntegerField(blank=True, null=True)
    director_email       = models.CharField(maxlength=64, blank=True, null=True)
    class_durations      = models.CharField(maxlength=128, blank=True, null=True)
    teacher_class_noedit = models.DateTimeField(blank=True, null=True)
    
    session_counts       = models.CommaSeparatedIntegerField(maxlength=100, blank=True)
    
    num_teacher_questions = models.PositiveIntegerField(default=1, blank=True, null=True)
    num_class_choices    = models.PositiveIntegerField(default=1, blank=True, null=True)
    
    #   An HTML color code for the program.  All classes will appear in some variant
    #   of this color in the catalog and registration pages.  If null, the default
    #   ESP colors will be used.
    color_code           = models.CharField(maxlength=6, blank=True, null=True)

    #   If this is true, teachers will be allowed to specify that students may
    #   come to their class late.
    allow_lateness       = models.BooleanField(blank=True, null=True)

    def session_counts_ints_get(self):
        return [ int(s) for s in self.session_counts.split(',') ]

    def session_counts_ints_set(self, value):
        self.session_counts = ",".join([ str(n) for n in value ])
    
    session_counts_ints = property( session_counts_ints_get, session_counts_ints_set )
    
    class_durations_any = models.BooleanField(blank=True, null=True)
    def __str__(self):
        return 'Class Reg Ext. for %s' % str(self.module)
    
    class Admin:
        pass
    

class CreditCardModuleInfo(models.Model):
    module = models.ForeignKey(ProgramModuleObj)
    base_cost        = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return 'Credit Card Ext. for %s' % str(self.module)

    class Admin:
        pass

class RemoteProfile(models.Model):
    from esp.users.models import User
    from esp.program.models import Program
    from esp.cal.models import Event

    user      = AjaxForeignKey(User,blank=True, null=True)
    program   = models.ForeignKey(Program,blank=True, null=True)
    volunteer = models.BooleanField(default = False)
    need_bus  = models.BooleanField(default = False)
    bus_runs  = models.ManyToManyField(DataTree,
                                       related_name="bus_teachers",
                                       blank=True)
    volunteer_times = models.ManyToManyField(Event,
                                             related_name='teacher_volunteer_set',
                                             blank=True)

    
    def __str__(self):
        return 'Remote participation info for teacher %s in %s' % \
                 (str(self.user), str(self.program))      

    class Admin:
        pass

class SATPrepTeacherModuleInfo(models.Model):
    from esp.users.models import User
    from esp.program.models import Program

    """ Module that links a user with a program and has SATPrep teacher info"""
    SAT_SUBJECTS = (
        ('M', 'Math'),
        ('V', 'Verbal'),
        ('W', 'Writing')
        )
        
    SUBJECT_DICT = {'M': 'Math', 'V': 'Verbal', 'W': 'Writing'}
    #   This is the unanimous decision of the ESP office, as of 11:30pm Friday Feb 22, 2008.
    #   Old category labels are kept commented below.   -Michael P
    SECTION_DICT = {'A': 'Helium', 'B': 'Neon', 'C': 'Argon', 'D': 'Krypton', 'E': 'Xenon', 'F': 'Radon'}
    #   SECTION_DICT = {'A': 'Mercury', 'B': 'Venus', 'C': 'Mars', 'D': 'Jupiter', 'E': 'Saturn', 'F': 'Neptune'}
    #   SECTION_DICT = {'A': 'Red', 'B': 'Orange', 'C': 'Yellow', 'D': 'Green', 'E': 'Blue', 'F': 'Violet'}

    sat_math = models.PositiveIntegerField(blank=True, null=True)
    sat_writ = models.PositiveIntegerField(blank=True, null=True)
    sat_verb = models.PositiveIntegerField(blank=True, null=True)

    mitid    = models.PositiveIntegerField(blank=True, null=True)

    subject  = models.CharField(maxlength=32, choices = SAT_SUBJECTS)

    user     = AjaxForeignKey(User,blank=True, null=True)
    program  = models.ForeignKey(Program,blank=True, null=True)
    section  = models.CharField(maxlength=5)
   
    def __str__(self):
        return 'SATPrep Information for teacher %s in %s' % \
                 (str(self.user), str(self.program))

    class Admin:
        pass
    
    def get_subject_display(self):
        if self.subject in SATPrepTeacherModuleInfo.SUBJECT_DICT:
            return SATPrepTeacherModuleInfo.SUBJECT_DICT[self.subject]
        else:
            return 'Unknown'
        
    def get_section_display(self):
        if self.section in SATPrepTeacherModuleInfo.SECTION_DICT:
            return SATPrepTeacherModuleInfo.SECTION_DICT[self.section]
        else:
            return 'Unknown'
        
    @staticmethod
    def subjects():
        return SATPrepTeacherModuleInfo.SAT_SUBJECTS



