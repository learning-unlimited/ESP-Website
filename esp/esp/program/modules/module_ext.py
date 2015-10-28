
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
  Email: web-team@learningu.org
"""

import time
from datetime import timedelta
from django.db import models
from esp.program.modules.base import ProgramModuleObj
from esp.db.fields import AjaxForeignKey
from django.conf import settings
from esp.users.models import ESPUser
from esp.program.models import Program, RegistrationType, ClassSection

class DBReceipt(models.Model):
    """ Per-program Receipt templates """
    #   Allow multiple receipts per program.  Which one is used depends on the action.
    action  = models.CharField(max_length=80, default='confirm')
    program = models.ForeignKey(Program)
    receipt = models.TextField()
    
    def __unicode__(self):
        return 'Registration (%s) receipt for %s' % (self.action, self.program)


class StudentClassRegModuleInfo(models.Model):
    """ Define what happens when students add classes to their schedule at registration. """

    module               = models.ForeignKey(ProgramModuleObj, editable=False)
    
    #   Set to true to prevent students from registering from full classes.
    enforce_max          = models.BooleanField(default=True, help_text='Check this box to prevent students from signing up for full classes.')
    
    #   Filter class caps on the fly... y = ax + b
    #     a = class_cap_multiplier
    #     b = class_cap_offset
    class_cap_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default='1.00', help_text='A multiplier for class capacities (set to 0.5 to cap all classes at half their stored capacity).')
    class_cap_offset    = models.IntegerField(default=0, help_text='Offset for class capacities (this number is added to the original capacity of every class).')
    apply_multiplier_to_room_cap = models.BooleanField(default=False, help_text='Apply class cap multipler and offset to room capacity instead of class capacity.')
    
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
    #   Whether to use grade range exceptions
    use_grade_range_exceptions = models.BooleanField(default=False, help_text='Check this box to enable grade range exceptions.')
    
    #   Set to true to allow classes to be added (via Ajax) using buttons on the catalog
    register_from_catalog = models.BooleanField(default=False, help_text='Check this box to allow students to add classes from the catalog page if they are logged in.')
    
    #   Enrollment visibility
    visible_enrollments = models.BooleanField(default=True, help_text='Uncheck this box to prevent students from seeing enrollments on the catalog.')
    #   Meeting times visibility
    visible_meeting_times = models.BooleanField(default=True, help_text='Uncheck this box to prevent students from seeing classes\' meeting times on the catalog.')
    
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
    
    #   The maximum length of a class, in minutes.
    class_max_duration   = models.IntegerField(blank=True, null=True, help_text='The maximum length of a class, in minutes.')
    
    #   Class size options: teachers will see [min:step:max] plus other_sizes
    class_min_cap       = models.IntegerField(blank=True, null=True, help_text='The minimum number of students a teacher can choose as their class capacity.')
    class_max_size       = models.IntegerField(blank=True, null=True, help_text='The maximum number of students a teacher can choose as their class capacity.')
    class_size_step      = models.IntegerField(blank=True, null=True, help_text='The interval for class capacity choices.')
    class_other_sizes    = models.CommaSeparatedIntegerField(blank=True, null=True, max_length=100, help_text='Force the addition of these options to teachers\' choices of class size.  (Enter a comma-separated list of integers.)')
    
    #   Allowed numbers of sections and meeting days
    allowed_sections     = models.CommaSeparatedIntegerField(max_length=100, blank=True,
        help_text='Allow this many independent sections of a class (comma separated list of integers). Leave blank to allow arbitrarily many.')
    session_counts       = models.CommaSeparatedIntegerField(max_length=100, blank=True,
        help_text='Possibilities for the number of days that a class could meet (comma separated list of integers). Leave blank if this is not a relevant choice for the teachers.')
    
    num_teacher_questions = models.PositiveIntegerField(default=1, blank=True, null=True, help_text='The maximum number of application questions that can be specified for each class.')
    
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
        min_size = 5
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
    
    def __unicode__(self):
        return 'Class Reg Ext. for %s' % str(self.module)

class AJAXChangeLogEntry(models.Model):

    # unique index in change_log of this entry
    index = models.IntegerField()

    # whether this is a scheduling entry (or comment entry)
    isScheduling = models.BooleanField(default=True)

    # scheduling entry: comma-separated list of integer timeslots
    timeslots = models.CharField(max_length=256)

    # scheduling entry: name of the room involved in scheduling update
    room_name = models.CharField(max_length=256)

    # comment entry: comment text
    comment = models.CharField(max_length=256, null=True)

    # comment entry: is locked
    locked = models.BooleanField(default=False)

    # ClassSection ID to update
    cls_id = models.IntegerField()

    # user responsible for this entry
    user = AjaxForeignKey(ESPUser, blank=True, null=True)

    # time we entered this
    time = models.FloatField()

    def setScheduling(self, timeslots, room_name, cls_id):
        self.isScheduling = True
        self.timeslots = ','.join([str(x) for x in timeslots])
        self.room_name = room_name
        self.cls_id = cls_id

    def setComment(self, comment, lock, cls_id):
        self.isScheduling = False
        self.comment = comment
        self.locked = lock
        self.cls_id = cls_id

    def save(self, *args, **kwargs):
        self.time = time.time()
        super(AJAXChangeLogEntry, self).save(*args, **kwargs)

    def getTimeslots(self):
        if self.timeslots == "":
            return []
        return [int(timeslot_id) for timeslot_id in self.timeslots.split(',')]

    def getUserName(self):
        if self.user:
            return self.user.username
        else:
            return "unknown"

    def toDict(self):
        d = {}
        d['index'] = self.index
        d['id'] = self.cls_id
        d['user'] = self.getUserName()
        d['isScheduling'] = self.isScheduling
        if self.isScheduling:
            d['room_name'] = self.room_name
            d['timeslots'] = self.getTimeslots()
        else:
            d['comment'] = self.comment
            d['locked'] = self.locked
        return d

class AJAXChangeLog(models.Model):
    # program this change log stores changes for
    program = AjaxForeignKey(Program)

    # many to many for entries in this change log
    entries = models.ManyToManyField(AJAXChangeLogEntry)

    # log entries older than this are deleted
    max_log_age = timedelta(hours=12).total_seconds()

    def update(self, program):
        self.program = program
        self.age = time.time()

    def prune(self):
        max_time = time.time() - self.max_log_age
        self.entries.filter(time__lte=max_time).delete()
        self.save()

    def append(self, entry, user=None):
        entry.index = self.get_latest_index() + 1
        if user:
            entry.user = user

        entry.save()
        self.save()
        self.entries.add(entry)
        self.save()

    def appendScheduling(self, timeslots, room_name, cls_id, user=None):
        entry = AJAXChangeLogEntry()
        entry.setScheduling(timeslots, room_name, cls_id)
        self.append(entry, user)

    def appendComment(self, comment, lock, cls_id, user=None):
        entry = AJAXChangeLogEntry()
        entry.setComment(comment, lock, cls_id)
        self.append(entry, user)

    def get_latest_index(self):
        index = self.entries.all().aggregate(models.Max('index'))['index__max']

        if index is None:
            index = 0

        return index

    def get_earliest_index(self):
        return self.entries.all().aggregate(models.Min('index'))['index__min']

        if index is None:
            index = 0

        return index

    def get_log(self, last_index):
        new_entries = self.entries.filter(index__gt=last_index).order_by('index')
        entry_list = list()

        for entry in new_entries:
            entry_list.append(entry.toDict())

        return entry_list

# stores scheduling details about an section for the AJAX scheduler
#  (e.g., scheduling comments, locked from AJAX scheduling, etc.)
class AJAXSectionDetail(models.Model):
    program = AjaxForeignKey(Program)
    cls_id = models.IntegerField()
    comment = models.CharField(max_length=256)
    locked = models.BooleanField(default=False)

    def initialize(self, program, cls_id, comment, locked):
        self.program = program
        self.cls_id = cls_id
        self.comment = comment
        self.locked = locked
        self.save()

    def update(self, comment, locked):
        self.comment = comment
        self.locked = locked
        self.save()

from esp.application.models import FormstackAppSettings
