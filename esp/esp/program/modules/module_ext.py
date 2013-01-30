
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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
  Email: web-team@lists.learningu.org
"""
from django.db import models
from esp.datatree.models import *
from esp.program.modules.base import ProgramModuleObj
from esp.db.fields import AjaxForeignKey
from esp import settings
from esp.users.models import ESPUser
from esp.program.models import Program, RegistrationType

class DBReceipt(models.Model):
    """ Per-program Receipt templates """
    #   Allow multiple receipts per program.  Which one is used depends on the action.
    action  = models.CharField(max_length=80, default='confirm')
    program = models.ForeignKey(Program)
    receipt = models.TextField()
    
    def __unicode__(self):
        return 'Registration (%s) receipt for %s' % (self.action, self.program)


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
    signup_verb          = models.ForeignKey(RegistrationType, default=lambda: RegistrationType.get_map(include=['Enrolled'], category='student')['Enrolled'], help_text='Which verb to grant a student when they sign up for a class.', null=True)
    
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

    #   Choose whether users have to fill out "required" modules before they can see the main StudentReg page
    #   (They still have to fill them out before confirming their registration, regardless of this setting)
    force_show_required_modules = models.BooleanField(default=True, help_text = "Check this box to require that users see and fill out \"required\" modules before they can see the main StudentReg page")
    
    def reg_verbs(self):
        verb_list = [self.signup_verb]

        if self.use_priority:
            for i in range(0, self.priority_limit):
                name = 'Priority/%d' % (i + 1)
                verb_list.append(RegistrationType.get_map(include=[name], category='student')[name])
        
        #   Require that the /Applied bit is in the list, since students cannot enroll
        #   directly in classes with application questions.
        applied_verb = RegistrationType.get_map(include=['Applied'], category='student')['Applied']
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
    
    #   Class size options: teachers will see [min:step:max] plus other_sizes
    class_min_cap       = models.IntegerField(blank=True, null=True, help_text='The minimum number of students a teacher can choose as their class capacity.')
    class_max_size       = models.IntegerField(blank=True, null=True, help_text='The maximum number of students a teacher can choose as their class capacity.')
    class_size_step      = models.IntegerField(blank=True, null=True, help_text='The interval for class capacity choices.')
    class_other_sizes    = models.CommaSeparatedIntegerField(blank=True, null=True, max_length=100, help_text='Force the addition of these options to teachers\' choices of class size.  (Enter a comma-separated list of integers.)')
    
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

    # Use the maximum class size field.
    use_class_size_max   = models.BooleanField(blank=True, default=True)
    # Use the optimal class size field.
    use_class_size_optimal = models.BooleanField(blank=True, default=False)
    # Provide an option to pick an optimal class size range.
    use_optimal_class_size_range = models.BooleanField(blank=True, default=False)
    # Enable teachers to specify all allowable class size ranges.
    use_allowable_class_size_ranges = models.BooleanField(blank=True, default=False)

    # Have an additional registration option to register for an "open class".
    open_class_registration = models.BooleanField(blank=True, default=False,
         help_text = 'If true, teachers will be presented with an option to register for an "open class".')
    
    #   Choose which appears on teacher reg for the modules: checkbox list, progress bar, or nothing
    #   ((0, 'None'),(1, 'Checkboxes'), (2, 'Progress Bar'))
    progress_mode = models.IntegerField(default=1, help_text='Select which to use on teacher reg: 1=checkboxes, 2=progress bar, 0=neither.')
    
    def allowed_sections_ints_get(self):
        return [ int(s.strip()) for s in self.allowed_sections.split(',') if s.strip() != '' ]

    def allowed_sections_ints_set(self, value):
        self.allowed_sections = ",".join([ str(n) for n in value ])

    def get_program(self):
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
        return program
    
    def allowed_sections_actual_get(self):
        if self.allowed_sections:
            return self.allowed_sections_ints_get()
        else:
            return range( 1, self.get_program().getTimeSlots().count()+1 )

    # TODO: rename allowed_sections to... something and this to allowed_sections
    allowed_sections_actual = property( allowed_sections_actual_get, allowed_sections_ints_set )

    def session_counts_ints_get(self):
        return [ int(s) for s in self.session_counts.split(',') ]

    def session_counts_ints_set(self, value):
        self.session_counts = ",".join([ str(n) for n in value ])
    
    session_counts_ints = property( session_counts_ints_get, session_counts_ints_set )

    def getClassSizes(self):
        #   Default values
        min_size = 0
        max_size = 30
        size_step = 1
        other_sizes = range(40, 210, 10)

        if self.class_max_size:
            max_size = self.class_max_size
            other_sizes = []
        if self.class_size_step:
            size_step = self.class_size_step
            other_sizes = []
        if self.class_min_cap:
            min_size = self.class_min_cap
            other_sizes = []
        if self.class_other_sizes and len(self.class_other_sizes) > 0:
            other_sizes = [int(x) for x in self.class_other_sizes.split(',')]

        ret_range = sorted(range(min_size, max_size + 1, size_step) + other_sizes)

        return ret_range

    def getClassGrades(self):
        min_grade, max_grade = (6, 12)
        if self.get_program().grade_min:
            min_grade = self.get_program().grade_min
        if self.get_program().grade_max:
            max_grade = self.get_program().grade_max

        return range(min_grade, max_grade+1)

    def getTimes(self):
        times = self.get_program().getTimeSlots()
        return [(str(x.id),x.short_description) for x in times]

    def getDurations(self):
        return self.get_program().getDurations()

    def getResources(self):
        resources = self.get_program().getResources()
        return [(str(x.id), x.name) for x in resources]
   
    def getResourceTypes(self, is_global=None):
        #   Get a list of all resource types, excluding the fundamental ones.
        base_types = self.get_program().getResourceTypes().filter(priority_default__gt=0)
        
        if is_global is True:
            res_types = base_types.filter(program__isnull=True)
        elif is_global is False:
            res_types = base_types.filter(program__isnull=False)
        else:
            res_types = base_types
            
        return [(str(x.id), x.name) for x in res_types]

    
    def __unicode__(self):
        return 'Class Reg Ext. for %s' % str(self.module)

class RemoteProfile(models.Model):
    from esp.users.models import User
    from esp.program.models import Program
    from esp.cal.models import Event

    user      = AjaxForeignKey(ESPUser,blank=True, null=True)
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
    SECTION_DICT = {'A': 'Java', 'B': 'Python', 'C': 'QB', 'D': 'C++', 'E': 'MATLAB', 'F': 'Scheme', 'G': 'SQL'}
    #   SECTION_DICT = {'A': 'Java', 'B': 'Python', 'C': 'QB', 'D': 'C++', 'E': 'MATLAB', 'F': 'Scheme'}
    #    SECTION_DICT = {'A': 'Libra', 'B': 'Scorpio', 'C': 'Sagittarius', 'D': 'Capricorn', 'E': 'Aquarius', 'F': 'Pisces'}
    #   SECTION_DICT = {'A': 'Helium', 'B': 'Neon', 'C': 'Argon', 'D': 'Krypton', 'E': 'Xenon', 'F': 'Radon'}
    #   SECTION_DICT = {'A': 'Mercury', 'B': 'Venus', 'C': 'Mars', 'D': 'Jupiter', 'E': 'Saturn', 'F': 'Neptune'}
    #   SECTION_DICT = {'A': 'Red', 'B': 'Orange', 'C': 'Yellow', 'D': 'Green', 'E': 'Blue', 'F': 'Violet'}

    sat_math = models.PositiveIntegerField(blank=True, null=True)
    sat_writ = models.PositiveIntegerField(blank=True, null=True)
    sat_verb = models.PositiveIntegerField(blank=True, null=True)

    mitid    = models.PositiveIntegerField(blank=True, null=True)

    subject  = models.CharField(max_length=32, choices = SAT_SUBJECTS)

    user     = AjaxForeignKey(ESPUser,blank=True, null=True)
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

""" Model for settings that control the First Data credit card module. """
class CreditCardSettings(models.Model):
    module = models.ForeignKey(ProgramModuleObj)
    store_id = models.CharField(max_length=80, default='')
    host_payment_form = models.BooleanField(default=False)
    post_url = models.CharField(max_length=255, default='')
    offer_donation = models.BooleanField(default=False)
    invoice_prefix = models.CharField(max_length=80, default=settings.INSTITUTION_NAME.lower())
