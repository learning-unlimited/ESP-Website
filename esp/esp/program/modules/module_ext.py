
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
from esp.datatree.models import *
from esp.program.modules.base import ProgramModuleObj
from esp.db.fields import AjaxForeignKey

from esp.program.models import Program

class DBReceipt(models.Model):
    """ Per-program Receipt templates """
    #   Allow multiple receipts per program.  Which one is used depends on the action.
    action  = models.CharField(max_length=80, default='confirm')
    program = models.ForeignKey(Program)
    receipt = models.TextField()
    
    def __unicode__(self):
        return 'Registration (%s) receipt for %s' % (self.action, self.program)


class SATPrepAdminModuleInfo(models.Model):
    module        = models.ForeignKey(ProgramModuleObj)
    num_divisions = models.IntegerField(blank=True, null=True)
    
    def __unicode__(self):
        return 'SATPrep admin settings for %s' % self.module.program
    
    class Admin:
        pass

REG_VERB_BASE = 'V/Flags/Registration'
class StudentClassRegModuleInfo(models.Model):
    """ Define what happens when students add classes to their schedule at registration. """

    module               = models.ForeignKey(ProgramModuleObj)
    
    #   Set to true to prevent students from registering from full classes.
    enforce_max          = models.BooleanField(default=True, help_text='Check this box to prevent students from signing up for full classes.')
    
    #   Filter class caps on the fly... y = ax + b
    #     a = class_cap_multiplier
    #     b = class_cap_offset
    class_cap_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default='1.00', help_text='A multiplier for class capacities (set to 0.5 to cap all classes at half their stored capacity).')
    class_cap_offset    = models.IntegerField(default=0, help_text='Offset for class capacities (this number is added to the original capacity of every class).')
    
    #   This points to the tree node that is used for the verb when a student is added to a class.
    #   Only 'Enrolled' actually puts them on the class roster.  Other verbs may be used to
    #   represent other statuses ('Applied', 'Rejected', etc.)
    #   Note: When use_priority is True, sub-verbs with integer indices are used 
    #         (e.g. 'Priority/1', 'Priority/2', ...)
    signup_verb          = AjaxForeignKey(DataTree, default=lambda:GetNode(REG_VERB_BASE + '/Enrolled'), help_text='Which verb to grant a student when they sign up for a class.')
    
    #   Whether to use priority
    use_priority         = models.BooleanField(default=False, help_text='Check this box to enable priority registration.')
    #   Number of choices a student can make for each time block (1st choice, 2nd choice, ...Nth choice.)
    priority_limit       = models.IntegerField(default=3, help_text='The maximum number of choices a student can make per timeslot when priority registration is enabled.')
    
    #   Set to true to allow classes to be added (via Ajax) using buttons on the catalog
    register_from_catalog = models.BooleanField(default=False, help_text='Check this box to allow students to add classes from the catalog page if they are logged in.')
    
    #   Enrollment visibility
    visible_enrollments = models.BooleanField(default=True, help_text='Uncheck this box to prevent students from seeing enrollments on the catalog.')
    #   Meeting times visibility
    visible_meeting_times = models.BooleanField(default=True, help_text='Uncheck this box to prevent students from seeing classes\' meeting times on the catalog.')
    
    #   Show classes that have not yet been scheduled?
    show_unscheduled_classes = models.BooleanField(default=True, help_text='Uncheck this box to prevent people from seeing classes in the catalog before they have been scheduled.')
    
    #   Customize buttons
    #   - Labels
    confirm_button_text = models.CharField(max_length=80, default='Confirm', help_text='Label for the "confirm" button at the bottom of student reg.')
    view_button_text    = models.CharField(max_length=80, default='View Receipt', help_text='Label for the "get receipt" button (for already confirmed students) at the bottom of student reg.')
    cancel_button_text  = models.CharField(max_length=80, default='Cancel Registration', help_text='Label for the "cancel" button at the bottom of student reg.')
    temporarily_full_text = models.CharField(max_length=255, default='Class temporarily full; please check back later', help_text='The text that replaces the "Add class" button when the class has reached its adjusted capacity')
    
    #   - Set to true to make the cancel button remove the student from classes they have registered for
    cancel_button_dereg = models.BooleanField(default=False, help_text='Check this box to remove a student from all of their classes when they cancel their registration.')
    
    #   Choose which appears on student reg for the modules: checkbox list, progress bar, or nothing
    #   ((0, 'None'),(1, 'Checkboxes'), (2, 'Progress Bar'))
    progress_mode = models.IntegerField(default=1, help_text='Select which to use on student reg: 1=checkboxes, 2=progress bar, 0=neither.')
    
    #   Choose whether an e-mail is sent the first time a student confirms registration.
    send_confirmation = models.BooleanField(default=False, help_text='Check this box to send each student an e-mail the first time they confirm their registration.  You must define an associated DBReceipt of type "confirmemail".')
    
    #   Choose whether class IDs are shown on catalog.
    show_emailcodes = models.BooleanField(default=True, help_text='Uncheck this box to prevent e-mail codes (i.e. E534, H243) from showing up on catalog and fillslot pages.')
    
    def __init__(self, *args, **kwargs):
        #   Trying to fetch self.signup_verb directly throws a DoesNotExist for some reason.
        super(StudentClassRegModuleInfo, self).__init__(*args, **kwargs)
        if (not self.signup_verb_id) and ('signup_verb' not in kwargs.keys()):
            self.signup_verb = GetNode(REG_VERB_BASE + '/Enrolled')
    
    def reg_verbs(self, uris=False):
        if not self.signup_verb:
            return []

        if self.use_priority:
            verb_list = []
            for i in range(0, self.priority_limit):
                if uris:
                    verb_list.append(self.signup_verb.get_uri()[len(REG_VERB_BASE):] + '/%d' % (i + 1))
                else:
                    verb_list.append(DataTree.get_by_uri(self.signup_verb.get_uri() + '/%d' % (i + 1)))
        else:
            if uris:
                verb_list = [self.signup_verb.get_uri()[len(REG_VERB_BASE):]]
            else:
                verb_list = [self.signup_verb]
        
        #   Require that the /Applied bit is in the list, since students cannot enroll
        #   directly in classes with application questions.
        if uris:
            if '/Applied' not in verb_list: 
                verb_list.append('/Applied')
        else:
            applied_verb = GetNode(REG_VERB_BASE + '/Applied')
            if applied_verb not in verb_list:
                verb_list.append(applied_verb)
        
        return verb_list
    
    def __unicode__(self):
        return 'Student Class Reg Ext. for %s' % str(self.module)
    
class ClassRegModuleInfo(models.Model):
    module               = models.ForeignKey(ProgramModuleObj)
    allow_coteach        = models.BooleanField(blank=True, default=True, help_text='Check this box to allow teachers to specify co-teachers.')
    set_prereqs          = models.BooleanField(blank=True, default=True, help_text='Check this box to allow teachers to enter prerequisites for each class that are displayed separately on the catalog.')
    display_times        = models.BooleanField(blank=True, default=False)
    times_selectmultiple = models.BooleanField(blank=True, default=False)
    
    #   The maximum length of a class, in minutes.
    class_max_duration   = models.IntegerField(blank=True, null=True, help_text='The maximum length of a class, in minutes.')
    
    class_max_size       = models.IntegerField(blank=True, null=True)
    
    class_size_step      = models.IntegerField(blank=True, null=True)
    director_email       = models.EmailField(blank=True, null=True)
    class_durations      = models.CharField(max_length=128, blank=True, null=True)
    teacher_class_noedit = models.DateTimeField(blank=True, null=True, help_text='Teachers will not be able to edit their classes after this time.')
    
    #   Allowed numbers of sections and meeting days
    allowed_sections     = models.CommaSeparatedIntegerField(max_length=100, blank=True,
        help_text='Allow this many independent sections of a class (comma separated list of integers). Leave blank to allow arbitrarily many.')
    session_counts       = models.CommaSeparatedIntegerField(max_length=100, blank=True,
        help_text='Possibilities for the number of days that a class could meet (comma separated list of integers). Leave blank if this is not a relevant choice for the teachers.')
    
    num_teacher_questions = models.PositiveIntegerField(default=1, blank=True, null=True, help_text='The maximum number of application questions that can be specified for each class.')
    num_class_choices    = models.PositiveIntegerField(default=1, blank=True, null=True)
    
    #   An HTML color code for the program.  All classes will appear in some variant
    #   of this color in the catalog and registration pages.  If null, the default
    #   ESP colors will be used.
    color_code           = models.CharField(max_length=6, blank=True, null=True)

    #   If this is true, teachers will be allowed to specify that students may
    #   come to their class late.
    allow_lateness       = models.BooleanField(blank=True, default=False)
    #   Room requests
    ask_for_room         = models.BooleanField(blank=True, default=True,
        help_text = 'If true, teachers will be asked if they have a particular classroom in mind.')
    
    #   Choose which appears on teacher reg for the modules: checkbox list, progress bar, or nothing
    #   ((0, 'None'),(1, 'Checkboxes'), (2, 'Progress Bar'))
    progress_mode = models.IntegerField(default=1, help_text='Select which to use on teacher reg: 1=checkboxes, 2=progress bar, 0=neither.')
    
    def allowed_sections_ints_get(self):
        return [ int(s.strip()) for s in self.allowed_sections.split(',') if s.strip() != '' ]

    def allowed_sections_ints_set(self, value):
        self.allowed_sections = ",".join([ str(n) for n in value ])
    
    def allowed_sections_actual_get(self):
        if self.allowed_sections:
            return self.allowed_sections_ints_get()
        else:
            # Unfortunately, it turns out the ProgramModule system does obscene
            # things with __dict__, so the class specification up there is a
            # blatant lie. Why the designer didn't think of giving two
            # different fields different names is a mystery sane people have no
            # hope of fathoming. (Seriously, these models are INTENDED to be
            # subclassed together with ProgramModuleObj! What were you
            # thinking!?)
            #
            # see ProgramModuleObj.module, ClassRegModuleInfo.module, and
            # ProgramModuleObj.fixExtensions
            #
            # TODO: Look into renaming the silly field and make sure no black
            # magic depends on it
            if hasattr(self, 'program'):
                program = self.program
            elif isinstance(self.module, ProgramModuleObj):
                # Sadly, this probably never happens, but this function is
                # going to work when called by a sane person, dammit!
                program = self.module.program
            else:
                raise ESPError("Can't find program from ClassRegModuleInfo")
            return range( 1, program.getTimeSlots().count()+1 )

    # TODO: rename allowed_sections to... something and this to allowed_sections
    allowed_sections_actual = property( allowed_sections_actual_get, allowed_sections_ints_set )

    def session_counts_ints_get(self):
        return [ int(s) for s in self.session_counts.split(',') ]

    def session_counts_ints_set(self, value):
        self.session_counts = ",".join([ str(n) for n in value ])
    
    session_counts_ints = property( session_counts_ints_get, session_counts_ints_set )
    def __unicode__(self):
        return 'Class Reg Ext. for %s' % str(self.module)
    

class CreditCardModuleInfo(models.Model):
    module = models.ForeignKey(ProgramModuleObj)
    base_cost        = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
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

    
    def __unicode__(self):
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
    #   This is the unanimous decision of the ESP office, as of 9:30pm Thursday Feb 20, 2009.
    #   Old category labels are kept commented below.   -Michael P
    SECTION_DICT = {'A': 'Java', 'B': 'Python', 'C': 'QB', 'D': 'C++', 'E': 'MATLAB', 'F': 'Scheme'}
    #    SECTION_DICT = {'A': 'Libra', 'B': 'Scorpio', 'C': 'Sagittarius', 'D': 'Capricorn', 'E': 'Aquarius', 'F': 'Pisces'}
    #   SECTION_DICT = {'A': 'Helium', 'B': 'Neon', 'C': 'Argon', 'D': 'Krypton', 'E': 'Xenon', 'F': 'Radon'}
    #   SECTION_DICT = {'A': 'Mercury', 'B': 'Venus', 'C': 'Mars', 'D': 'Jupiter', 'E': 'Saturn', 'F': 'Neptune'}
    #   SECTION_DICT = {'A': 'Red', 'B': 'Orange', 'C': 'Yellow', 'D': 'Green', 'E': 'Blue', 'F': 'Violet'}

    sat_math = models.PositiveIntegerField(blank=True, null=True)
    sat_writ = models.PositiveIntegerField(blank=True, null=True)
    sat_verb = models.PositiveIntegerField(blank=True, null=True)

    mitid    = models.PositiveIntegerField(blank=True, null=True)

    subject  = models.CharField(max_length=32, choices = SAT_SUBJECTS)

    user     = AjaxForeignKey(User,blank=True, null=True)
    program  = models.ForeignKey(Program,blank=True, null=True)
    section  = models.CharField(max_length=5)
   
    def __unicode__(self):
        return 'SATPrep Information for teacher %s in %s' % \
                 (str(self.user), str(self.program))

    class Meta:
        unique_together = ('user', 'program')
    
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



