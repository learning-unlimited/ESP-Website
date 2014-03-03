__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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

import numpy
assert numpy.version.short_version >= "1.7.0"
import numpy.random

from datetime import date, datetime

from esp.cal.models import Event
from esp.users.models import ESPUser, StudentInfo
from esp.program.models import StudentRegistration, StudentSubjectInterest, RegistrationType, RegistrationProfile, ClassSection
from esp.program.models.class_ import ClassCategories
from esp.mailman import add_list_member, remove_list_member, list_contents

from django.conf import settings
from django.db.models import Min
import os
import operator

class LotteryAssignmentController(object):

    default_options = {
        'Kp': 1.2,
        'Ki': 1.1,
        'check_grade': True,
        'stats_display': False,
        'directory': os.getenv("HOME"),
        'use_student_apps': False,
        'fill_low_priorities': False,
    }
    
    def __init__(self, program, **kwargs):
        """ Set constant parameters for a lottery assignment. """
        

        self.program = program
        students = self.program.students()
        if 'twophase_star_students' in students:
            # We can't do the join in SQL, because the query generated takes at least half an hour.  So do it in python.
            stars = set(students['twophase_star_students'].values_list('id',flat=True))
            prioritys = set(students['twophase_priority_students'].values_list('id',flat=True))
            self.lotteried_students = list(stars|prioritys)

        elif 'lotteried_students' in students:
            self.lotteried_students = students['lotteried_students']
        else:
            raise Exception('Cannot retrieve lottery preferences for program, please ensure that it has the lottery module.')
        self.sections = self.program.sections().filter(status__gt=0, parent_class__status__gt=0, registration_status=0, meeting_times__isnull=False).order_by('id').select_related('parent_class','parent_class__parent_program','meeting_times').distinct()
        self.timeslots = self.program.getTimeSlots()
        self.num_timeslots = len(self.timeslots)
        self.num_students = len(self.lotteried_students)
        self.num_sections = len(self.sections)
        self.real_priority_limit = self.program.priorityLimit() # For most purposes, you probably want to use self.effective_priority_limit instead.
        self.grade_range_exceptions = self.program.useGradeRangeExceptions()
        self.effective_priority_limit = self.real_priority_limit + 1 if self.grade_range_exceptions else self.real_priority_limit
        
        self.options = LotteryAssignmentController.default_options.copy()
        self.options.update(kwargs)
        
        self.now = datetime.now()
        numpy.random.seed(self.now.microsecond)
        
        self.initialize()
        
        if self.options['stats_display']: 
            print 'Initialized lottery assignment for %d students, %d sections, %d timeslots' % (self.num_students, self.num_sections, self.num_timeslots)
        
    def get_index_array(self, arr):
        """ Given an array of arbitrary integers, create a new array that maps 
            the values back to their indices.  Invalid entries are stored as -1.
            For example:            arr = [1, 6, 5, 3]
                -> get_index_array(arr) = [-1, 0, -1, 3, -1, 2, 1]
        """
        
        max_index = numpy.max(arr)
        index_arr = -numpy.ones((max_index + 1,), dtype=numpy.int32)
        for i in range(arr.shape[0]):
            index_arr[arr[i]] = i
        return index_arr
        
    def get_ids(self, qs):
        """ Get an array of the IDs of the objects stored in the QuerySet qs. """
        
        return numpy.array(qs.order_by('id').values_list('id', flat=True))
        
    def get_ids_and_indices(self, qs):
        """ Get a tuple of the IDs and lookup indices of the objects stored in the QuerySet qs. """
        
        if 'order_by' in dir(qs):
            # We have a QuerySet.
            a1 = numpy.array(qs.order_by('id').values_list('id', flat=True))
        else:
            a1 = numpy.array(qs)
        a2 = self.get_index_array(a1)
        return (a1, a2)
        
    def clear_assignments(self):
        """ Reset the state of the controller so that new assignments may be computed,
            but without fetching any information from the database. """
            
        self.student_schedules = numpy.zeros((self.num_students, self.num_timeslots), dtype=numpy.bool)
        self.student_enrollments = numpy.zeros((self.num_students, self.num_timeslots), dtype=numpy.int32)
        self.student_sections = numpy.zeros((self.num_students, self.num_sections), dtype=numpy.bool)
        self.student_weights = numpy.ones((self.num_students,))
        self.student_utilities = numpy.zeros((self.num_students, ), dtype=numpy.float)

    def put_prefs_in_array(self, prefs, array):
        """ Helper function for self.initialize().

        Given ValuesListQuerySet of preferences (student, section) and a students-by-sections array (likely self.interest or self.priority[i]), set the entries of the array corresponding to the preferences True.  Check that all values in question are valid.

        prefs should be a ValuesListQuerySet of tuples (user, section), such as that generated by StudentRegistration.objects.filter(...).values_list('user__id', 'section__id').distinct().
        array should be a boolean array of dimension self.num_students by self.num_sections, such as self.interest or self.priority[i]."""
        if prefs.exists():
            pref_array = numpy.array(prefs, dtype=numpy.uint32)
            student_ixs = self.student_indices[pref_array[:, 0]]
            section_ixs = self.section_indices[pref_array[:, 1]]
            #   Check that we didn't look up invalid indices (which are set to -1).
            assert numpy.min(student_ixs)>=0, "Got a preference for a student who doesn't exist!"
            assert numpy.min(section_ixs)>=0, "Got a preference for a section which doesn't exist!"
            array[student_ixs, section_ixs] = True

    def initialize(self):
        """ Gather all of the information needed to run the lottery assignment.
            This includes:
            -   Students' interest (priority and interested bits)
            -   Class schedules and capacities
            -   Timeslots (incl. lunch periods for each day)
        """
        
        self.interest = numpy.zeros((self.num_students, self.num_sections), dtype=numpy.bool)
        self.priority = [numpy.zeros((self.num_students, self.num_sections), dtype=numpy.bool) for i in range(self.effective_priority_limit+1)]
        self.ranks = 10*numpy.ones((self.num_students, self.num_sections), dtype=numpy.int32)
        self.section_schedules = numpy.zeros((self.num_sections, self.num_timeslots), dtype=numpy.bool)
        self.section_start_schedules = numpy.zeros((self.num_sections, self.num_timeslots), dtype=numpy.bool)
        self.section_capacities = numpy.zeros((self.num_sections,), dtype=numpy.uint32)
        self.section_overlap = numpy.zeros((self.num_sections, self.num_sections), dtype=numpy.bool)
        
        # One array to keep track of the utility of each student
        # (defined as hours of interested class + 1.5*hours of priority classes)
        # and the other arrary to keep track of student weigths (defined as # of classes signed up for)
        self.student_utility_weights = numpy.zeros((self.num_students, ), dtype=numpy.float)
        self.student_utilities = numpy.zeros((self.num_students, ), dtype=numpy.float)

        #   Get student, section, timeslot IDs and prepare lookup table
        (self.student_ids, self.student_indices) = self.get_ids_and_indices(self.lotteried_students)
        (self.section_ids, self.section_indices) = self.get_ids_and_indices(self.sections)
        (self.timeslot_ids, self.timeslot_indices) = self.get_ids_and_indices(self.timeslots)
        self.parent_classes = numpy.array(self.sections.values_list('parent_class__id', flat=True))
        
        #   Get IDs of timeslots allocated to lunch by day
        #   (note: requires that this is constant across days)
        self.lunch_schedule = numpy.zeros((self.num_timeslots,))
        lunch_timeslots = Event.objects.filter(meeting_times__parent_class__parent_program=self.program, meeting_times__parent_class__category__category='Lunch').order_by('start').distinct()
        #   Note: this code should not be necessary once lunch-constraints branch is merged (provides Program.dates())
        dates = []
        for ts in self.timeslots:
            ts_day = date(ts.start.year, ts.start.month, ts.start.day)
            if ts_day not in dates:
                dates.append(ts_day)
        lunch_by_day = [[] for x in dates]
        ts_count = 0
        for ts in lunch_timeslots:
            d = date(ts.start.year, ts.start.month, ts.start.day)
            lunch_by_day[dates.index(d)].append(ts.id)
            self.lunch_schedule[self.timeslot_indices[ts.id]] = True
        self.lunch_timeslots = numpy.array(lunch_by_day)
        
        #   Populate interest matrix; this uses both the StudentRegistrations (which apply to a particular section) and StudentSubjectIntegests (which apply to all sections of the class).  If one does not exist, ignore it.  Be careful to only return SRs and SSIs for accepted sections of accepted classes; this might matter for SSIs where only some sections of the class are accepted.
        interest_regs_sr = StudentRegistration.valid_objects().filter(section__parent_class__parent_program=self.program, section__status__gt=0, section__parent_class__status__gt=0, section__registration_status=0, section__meeting_times__isnull=False, relationship__name='Interested').values_list('user__id', 'section__id').distinct()
        interest_regs_ssi = StudentSubjectInterest.valid_objects().filter(subject__parent_program=self.program, subject__status__gt=0, subject__sections__status__gt=0, subject__sections__registration_status=0, subject__sections__meeting_times__isnull=False).values_list('user__id', 'subject__sections__id').distinct()
        self.put_prefs_in_array(interest_regs_sr, self.interest)
        self.put_prefs_in_array(interest_regs_ssi, self.interest)
        
        #   Populate priority matrix
        priority_regs = [StudentRegistration.valid_objects().filter(section__parent_class__parent_program=self.program, relationship__name='Priority/%s'%i).values_list('user__id', 'section__id').distinct() for i in range(self.real_priority_limit+1)]
        if self.grade_range_exceptions:
            priority_regs.append(StudentRegistration.valid_objects().filter(section__parent_class__parent_program=self.program, relationship__name='GradeRangeException').values_list('user__id', 'section__id').distinct())
        for i in range(1,self.effective_priority_limit+1):
            self.put_prefs_in_array(priority_regs[i], self.priority[i])
        if self.options['use_student_apps']:
            for i in range(1,self.effective_priority_limit+1):
                for (student_id,section_id) in priority_regs[i]:
                    self.ranks[self.student_indices[student_id],self.section_indices[section_id]] = ESPUser.getRankInClass(student_id,self.parent_classes[self.section_indices[section_id]])
            for (student_id,section_id) in interest_regs:
                self.ranks[self.student_indices[student_id],self.section_indices[section_id]] = ESPUser.getRankInClass(student_id,self.parent_classes[self.section_indices[section_id]])

        
        #   Set student utility weights. Counts number of classes that students selected. Used only for computing the overall_utility stat
        self.student_utility_weights = numpy.sum(self.interest.astype(float), 1) + sum([numpy.sum(self.priority[i].astype(float), 1) for i in range(1,self.effective_priority_limit+1)])

        #   Populate section schedule
        section_times = numpy.array(self.sections.values_list('id', 'meeting_times__id'))
        start_times = numpy.array(self.sections.annotate(start_time=Min('meeting_times')).values_list('id','start_time'))
        self.section_schedules[self.section_indices[section_times[:, 0]], self.timeslot_indices[section_times[:, 1]]] = True
        self.section_start_schedules[self.section_indices[start_times[:, 0]], self.timeslot_indices[start_times[:, 1]]] = True
        
        #   Populate section overlap matrix
        for i in range(self.num_sections):
            group_ids = numpy.nonzero(self.parent_classes == self.parent_classes[i])[0]
            self.section_overlap[numpy.meshgrid(group_ids, group_ids)] = True

        #   Populate section grade limits
        self.section_grade_min = numpy.array(self.sections.values_list('parent_class__grade_min', flat=True), dtype=numpy.uint32)
        self.section_grade_max = numpy.array(self.sections.values_list('parent_class__grade_max', flat=True), dtype=numpy.uint32)
        
        #   Populate student grades; grade will be assumed to be 0 if not entered on profile
        self.student_grades = numpy.zeros((self.num_students,))
        gradyear_pairs = numpy.array(RegistrationProfile.objects.filter(user__id__in=list(self.student_ids), most_recent_profile=True, student_info__graduation_year__isnull=False).values_list('user__id', 'student_info__graduation_year'), dtype=numpy.uint32)
        self.student_grades[self.student_indices[gradyear_pairs[:, 0]]] = 12 + ESPUser.current_schoolyear() - gradyear_pairs[:, 1] + self.program.incrementGrade()
        
        #   Find section capacities (TODO: convert to single query)
        for sec in self.sections:
            self.section_capacities[self.section_indices[sec.id]] = sec.capacity

        # Populate section lengths (hours)
        self.section_lengths = numpy.array([x.nonzero()[0].size for x in self.section_schedules])

        if self.options['fill_low_priorities']:
            #   Compute who has a priority when.  Includes lower priorities, since this is used for places where we check not clobbering priorities.
            self.has_priority = [numpy.zeros((self.num_students, self.num_timeslots), dtype=numpy.bool) for i in range(self.effective_priority_limit)]
            for i in range(1,self.effective_priority_limit+1):
                priority_at_least_i = reduce(operator.or_,[self.priority[j] for j in range(i,self.effective_priority_limit+1)])
                numpy.dot(priority_at_least_i,self.section_schedules,out=self.has_priority[i])
            
            self.sections_at_same_time = numpy.dot(self.section_schedules, numpy.transpose(self.section_schedules))

            #   And the same, overlappingly.
            self.has_overlapping_priority = [numpy.zeros((self.num_students, self.num_timeslots), dtype=numpy.bool) for i in range(self.effective_priority_limit)]
            for i in range(1,self.effective_priority_limit+1):
                priority_at_least_i = reduce(operator.or_,[self.priority[j] for j in range(i,self.effective_priority_limit+1)])
                numpy.dot(numpy.dot(priority_at_least_i,self.sections_at_same_time),self.section_schedules,out=self.has_overlapping_priority[i])

            #   Fill in preferences for students who haven't ranked them.  In particular, if a student has ranked some level of class in a timeblock (i.e. they plan to be at Splash that timeblock), but has not ranked any priority/n or lower-priority classes overlapping it, add a random class from their interesteds.

            for i in range(1,self.real_priority_limit+1): #Use self.real_priority_limit since we don't want to give people free grade range exceptions!
                should_fill = numpy.transpose(numpy.nonzero(self.has_priority[1]&~self.has_overlapping_priority[i]))
                if len(should_fill):
                    for student, timeslot in should_fill:
                        # student is interested, and class starts in this timeslot, and class does not overlap any lower or equal priorities
                        possible_classes = numpy.nonzero(self.interest[student] & self.section_start_schedules[:,timeslot] & ~numpy.dot(self.section_schedules, numpy.transpose(self.has_priority[i][student])))[0]
                        if len(possible_classes):
                            choice = numpy.random.choice(possible_classes)
                            self.priority[i][student,choice]=True

                        

    
    def fill_section(self, si, priority=False, rank=10):
        """ Assigns students to the section with index si.
            Performs some checks along the way to make sure this didn't break anything. """
        
        timeslots = numpy.nonzero(self.section_schedules[si, :])[0]
        
        if self.options['stats_display']: print '-- Filling section %d (index %d, capacity %d, timeslots %s), priority=%s' % (self.section_ids[si], si, self.section_capacities[si], self.timeslot_ids[timeslots], priority)
        
        #   Compute number of spaces - exit if section or program is already full.  Otherwise, set num_spaces to the number of students we can add without overfilling the section or program.
        num_spaces = self.section_capacities[si] - numpy.sum(self.student_sections[:, si])
        if self.program.program_size_max:
            program_spaces_remaining = self.program.program_size_max - numpy.sum((numpy.sum(self.student_schedules, 1) > 0))
            if program_spaces_remaining == 0:
                if self.options['stats_display']: print '   Program was already full with %d students' % numpy.sum((numpy.sum(self.student_schedules, 1) > 0))
                return True
            else:
                num_spaces = min(num_spaces, program_spaces_remaining)
        if num_spaces == 0:
            if self.options['stats_display']: print '   Section was already full with %d students' % self.section_capacities[si]
            return True
        assert(num_spaces > 0)
        
        #   Assign the matrix of sign-up preferences depending on whether we are considering priority bits or not
        if priority:
            signup = self.priority[priority]
            weight_factor = self.options['Kp']
        else:
            signup = self.interest
            weight_factor = self.options['Ki']
            
        #   Check that there is at least one timeslot associated with this section
        if timeslots.shape[0] == 0:
            if self.options['stats_display']: print '   Section was not assigned to any timeslots, aborting'
            return False
            
        #   Check that this section does not cover all lunch timeslots on any given day
        lunch_overlap = self.lunch_schedule * self.section_schedules[si, :]
        for i in range(self.lunch_timeslots.shape[0]):
            if len(self.lunch_timeslots[i]) != 0 and numpy.sum(lunch_overlap[self.timeslot_indices[self.lunch_timeslots[i]]]) >= (self.lunch_timeslots.shape[1]):
                if self.options['stats_display']: print '   Section covered all lunch timeslots %s on day %d, aborting' % (self.lunch_timeslots[i, :], i)
                return False
        
        #   Get students who have indicated interest in the section
        possible_students = numpy.copy(signup[:, si])
        
        #   Filter students by the section's grade limits
        if self.options['check_grade'] and not (priority == self.effective_priority_limit and self.grade_range_exceptions):
            possible_students *= (self.student_grades >= self.section_grade_min[si])
            possible_students *= (self.student_grades <= self.section_grade_max[si])

        if self.options['use_student_apps']:
            possible_students *= (self.ranks[:, si] == rank)
            
        #   Filter students by who has all of the section's timeslots available
        for i in range(timeslots.shape[0]):
            possible_students *= (True - self.student_schedules[:, timeslots[i]])
            
        #   Filter students by who is not already registered for a different section of the class
        for sec_index in numpy.nonzero(self.section_overlap[:, si])[0]:
            possible_students *= (True - self.student_sections[:, sec_index])
            
        #   Filter students by lunch constraint - if class overlaps with lunch period, student must have 1 additional free spot
        #   NOTE: Currently only works with 2 lunch periods per day
        for i in range(timeslots.shape[0]):
            if numpy.sum(self.lunch_timeslots == self.timeslot_ids[timeslots[i]]) > 0:
                lunch_day = numpy.nonzero(self.lunch_timeslots == self.timeslot_ids[timeslots[i]])[0][0]
                for j in range(self.lunch_timeslots.shape[1]):
                    timeslot_index = self.timeslot_indices[self.lunch_timeslots[lunch_day, j]]
                    if timeslot_index != timeslots[i]:
                        possible_students *= (True - self.student_schedules[:, timeslot_index])
                        
        candidate_students = numpy.nonzero(possible_students)[0]
        if candidate_students.shape[0] <= num_spaces:
            #   If the section has enough space for all students that applied, let them all in.
            selected_students = candidate_students
            section_filled = False
        else:
            #   If the section does not have enough space, select the students up to the maximum
            #   capacity of the section, with the students' weight values serving as the probability
            #   distribution to draw from.
            weights = self.student_weights[candidate_students]
            weights /= numpy.sum(weights)
            selected_students = numpy.random.choice(candidate_students, num_spaces, replace=False, p=weights)
            section_filled = True

        #   Update student section assignments
        #   Check that none of these students are already assigned to this section
        assert(numpy.sum(self.student_sections[selected_students, si]) == 0)
        self.student_sections[selected_students, si] = True
        
        #   Update student schedules
        #   Check that none of the students are already occupied in those timeblocks
        for i in range(timeslots.shape[0]):
            assert(numpy.sum(self.student_schedules[selected_students, timeslots[i]]) == 0)
            self.student_schedules[selected_students, timeslots[i]] = True
            self.student_enrollments[selected_students, timeslots[i]] = self.section_ids[si]

            #   Update student utilies
            if priority:
                self.student_utilities[selected_students] += 1.5
            else:
                self.student_utilities[selected_students] += 1
        
        #   Update student weights
        self.student_weights[selected_students] /= weight_factor
        
        if self.options['stats_display']: print '   Added %d/%d students (section filled: %s)' % (selected_students.shape[0], candidate_students.shape[0], section_filled)
        
        return section_filled

    def compute_assignments(self, check_result=True):
        """ Figure out what students should be assigned to what sections.
            Doesn't actually store results in the database.
            Can be run any number of times. """
            
        self.clear_assignments()
        
        ranks = (10,)
        if self.options['use_student_apps']:
            ranks = (10,5)
        for rank in ranks:
            for i in range(1,self.effective_priority_limit+1):
                if self.options['stats_display']:
                    print '\n== Assigning priority%s students%s' % ((str(i) if self.effective_priority_limit > 1 else ''), (' with rank %s'%rank if self.options['use_student_apps'] else ''))
                #   Assign priority students to all sections in random order, grouped by duration
                #   so that longer sections aren't disadvantaged by scheduling conflicts
                #   Re-randomize for each priority level so that some sections don't keep getting screwed
                sections_by_length = [numpy.nonzero(numpy.sum(self.section_schedules, axis=1) == i)[0] for i in range(self.num_timeslots, 0, -1)]
                for a in sections_by_length:
                    numpy.random.shuffle(a)
                    for section_index in a:
                        self.fill_section(section_index, priority=i, rank=rank)
            #   Sort sections in increasing order of number of interesting students
            #   TODO: Check with Alex that this is the desired algorithm
            interested_counts = numpy.sum(self.interest, 0)
            sorted_section_indices = numpy.argsort(interested_counts.astype(numpy.float) / self.section_capacities)
            if self.options['stats_display']:
                print '\n== Assigning interested students%s' % (' with rank %s'%rank if self.options['use_student_apps'] else '')
            for section_index in sorted_section_indices:
                self.fill_section(section_index, priority=False, rank=rank)
        
        if check_result:
            self.check_assignments()
    
    def check_assignments(self):
        """ Check the result for desired properties, before it is saved. """
        
        #   Check that no sections are overfilled
        assert(numpy.sum(numpy.sum(self.student_sections, 0) > self.section_capacities) == 0)
        
        #   Check that no student's schedule violates the lunch constraints: 1 or more open lunch periods per day
        for i in range(self.lunch_timeslots.shape[0]):
            timeslots = numpy.array([]) if (self.lunch_timeslots[i].shape[0] == 0) else self.timeslot_indices[self.lunch_timeslots[i, :]]
            if (timeslots.shape[0] == 0): continue
            assert(numpy.sum(numpy.sum(self.student_schedules[:, timeslots] > self.lunch_timeslots.shape[1] - 1)) == 0)
        
        #   Check that each student's schedule is consistent with their assigned sections
        for i in range(self.num_students):
            assert(numpy.sum(self.student_schedules[i, :] != numpy.sum(self.section_schedules[numpy.nonzero(self.student_sections[i, :])[0], :], 0)) == 0)
    
    def compute_stats(self, display=True):
        """ Compute statistics to provide feedback to the user about how well the
            lottery assignment worked.  """

        stats = {}
        
        priority_matches = [self.student_sections * self.priority[i] for i in range(self.effective_priority_limit+1)]
        priority_assigned = [numpy.sum(priority_matches[i], 1) for i in range(self.effective_priority_limit+1)]
        priority_requested = [numpy.sum(self.priority[i], 1) for i in range(self.effective_priority_limit+1)]
        priority_fractions = [0 for i in range(self.effective_priority_limit+1)]
        for i in range(1,self.effective_priority_limit+1):
            priority_fractions[i] = numpy.nan_to_num(priority_assigned[i].astype(numpy.float) / priority_requested[i])
        
        interest_matches = self.student_sections * self.interest
        interest_assigned = numpy.sum(interest_matches, 1)
        interest_requested = numpy.sum(self.interest, 1)
        interest_fractions = numpy.nan_to_num(interest_assigned.astype(numpy.float) / interest_requested)
        
        if self.effective_priority_limit > 1:
            for i in range(1,self.effective_priority_limit+1):
                stats['priority_%s_requested'%i] = priority_requested[i]
                stats['priority_%s_assigned'%i] = priority_assigned[i]
                stats['overall_priority_%s_ratio'%i] = float(numpy.sum(priority_assigned[i])) / numpy.sum(priority_requested[i])
        else:
            stats['priority_requested'] = priority_requested[1]
            stats['priority_assigned'] = priority_assigned[1]
            stats['overall_priority_ratio'] = float(numpy.sum(priority_assigned[1])) / numpy.sum(priority_requested[1])

        if self.options['use_student_apps']:
            stats['ranks'] = self.ranks
            for rank in (10,5,1):
                stats['rank_%s_assigned'%rank] = numpy.logical_and(self.ranks == rank, self.student_sections == True)
        stats['interest_requested'] = interest_requested
        stats['interest_assigned'] = interest_assigned
        stats['enrollments'] = self.student_sections
        stats['assignments'] = self.student_enrollments
        stats['student_ids'] = self.student_ids
        stats['student_grades'] = self.student_grades
        stats['num_sections'] = self.num_sections
        stats['num_enrolled_students'] = numpy.sum((numpy.sum(self.student_schedules, 1) > 0))
        stats['num_lottery_students'] = self.num_students
        stats['overall_interest_ratio'] = float(numpy.sum(interest_assigned)) / numpy.sum(interest_requested)
        stats['num_registrations'] = numpy.sum(self.student_sections)
        stats['num_full_classes'] = numpy.sum(self.section_capacities == numpy.sum(self.student_sections, 0))
        stats['total_spaces'] = numpy.sum(self.section_capacities)

        #   Compute histograms of assigned vs. requested classes
        hist_priority = [{} for i in range(self.effective_priority_limit+1)]
        for j in range(1,self.effective_priority_limit+1):
            for i in range(self.num_students):
                key = (priority_assigned[j][i], priority_requested[j][i])
                if key not in hist_priority[j]:
                    hist_priority[j][key] = 0
                hist_priority[j][key] += 1
            if self.options['use_student_apps']:
                stats['hist_priority_%s'%j] = hist_priority[j]
        if not self.options['use_student_apps']:
            stats['hist_priority'] = hist_priority[1]
        
        hist_interest = {}
        for i in range(self.num_students):
            key = (interest_assigned[i], interest_requested[i])
            if key not in hist_interest:
                hist_interest[key] = 0
            hist_interest[key] += 1
        stats['hist_interest'] = hist_interest

        # Compute the overall utility of the current run.
        # 1. Each student has a utility of sqrt(#hours of interested + 1.5 #hours of priority).
        # This measures how happy the student will be with their classes
        # 2. Each student gets a weight of sqrt(# classes regged for)
        # This measures how much responsibility we take if the student gets a
        # bad schedule (we care less if students regged for less classes).
        # 3. We then sum weight*utility over all students and divide that
        # by the sum of weights to get a weighted average utility.
        #
        # Also use the utility to get a list of screwed students,
        # where the level of screwedness is defined by (1+utility)/(1+weight)
        # So, people with low untilities and high weights (low screwedness scores)
        # are considered screwed. This is pretty sketchy, so take it with a grain of salt.
        weighted_overall_utility = 0.0
        sum_of_weights=0.0
        screwed_students=[]
        for i in range(self.num_students):
            utility = numpy.sqrt(self.student_utilities[i])
            weight = numpy.sqrt((self.student_utility_weights[i]))
            weighted_overall_utility += utility * weight
            sum_of_weights += weight
            screwed_students.append(((1+utility)/(1+weight), self.student_ids[i]))

        overall_utility = weighted_overall_utility/sum_of_weights
        screwed_students.sort()

        stats['overall_utility'] = overall_utility
        stats['students_by_screwedness'] = screwed_students

        if self.options['stats_display'] or display:
            self.display_stats(stats)

        self.stats = stats
        return stats

    def display_stats(self, stats):
        print 'Lottery results for %s' % self.program.niceName()
        print '--------------------------------------'

        print 'Counts:'
        print '%6d students applied to the lottery' % stats['num_lottery_students']
        print '%6d students were enrolled in at least 1 class' % stats['num_enrolled_students']
        print '%6d total enrollments' % stats['num_registrations']
        print '%6d available sections' % stats['num_sections']
        print '%6d sections were filled to capacity' % stats['num_full_classes']

        print 'Ratios:'
        if self.effective_priority_limit>1:
            for i in range(1,self.effective_priority_limit+1):
                print '%2.2f%% of priority %s classes were enrolled' % (stats['overall_priority_%s_ratio' % i] * 100.0, i)
        else:
            print '%2.2f%% of priority classes were enrolled' % (stats['overall_priority_ratio'] * 100.0)
        print '%2.2f%% of interested classes were enrolled' % (stats['overall_interest_ratio'] * 100.0)
        """
        print 'Example results:'
        no_pri_indices = numpy.nonzero(stats['priority_assigned'] == 0)[0]
        print '1) First %d students who got none of their priority classes:' % min(5, no_pri_indices.shape[0])
        for i in range(min(5, no_pri_indices.shape[0])):
            sid = stats['student_ids'][no_pri_indices[i]]
            student = ESPUser.objects.get(id=sid)
            print '   Student: %s (grade %s)' % (student.name(), student.getGrade())
            cs_ids = self.section_ids[numpy.nonzero(self.priority[no_pri_indices[i], :])[0]]
            print '   - Priority classes: %s' % ClassSection.objects.filter(id__in=list(cs_ids))
            cs_ids = self.section_ids[numpy.nonzero(self.interest[no_pri_indices[i], :])[0]]
            print '   - Interested classes: %s' % ClassSection.objects.filter(id__in=list(cs_ids))
            """

    def get_computed_schedule(self, student_id, mode='assigned'):
        #   mode can be 'assigned', 'interested', or 'priority'
        if mode == 'assigned':
            assignments = numpy.nonzero(self.student_sections[self.student_indices[student_id], :])[0]
        elif mode == 'interested':
            assignments = numpy.nonzero(self.interest[self.student_indices[student_id], :])[0]
        elif mode == 'priority':
            assignments = numpy.nonzero(self.priority[1][self.student_indices[student_id], :])[0]
        else:
            import re
            p = re.search('(?<=priority_)\d*', mode).group(0)
            if p:
                assignments = numpy.nonzero(self.priority[p][self.student_indices[student_id], :])[0]
        result = []
        for i in range(assignments.shape[0]):
            result.append(ClassSection.objects.get(id=self.section_ids[assignments[i]]))
        return result

    def generate_screwed_csv(self, directory=None, n=None, stats=None):
        """Generate a CSV file of the n most screwed students. Default: All of them.
        Directory: string of what directory you like the information stored in.
        This is also known as the script shulinye threw together while trying to run the Spark 2013 lottery.
        You might want to crosscheck this file before accepting it."""
        import csv

        if directory == None:
            directory = self.options['directory']

        if stats == None:
            stats = self.compute_stats(display=False) #Calculate stats if I didn't get any

        studentlist = stats['students_by_screwedness']
        if n != None: studentlist = studentlist[:n]
        tday = datetime.today().strftime('%Y-%m-%d')
        
        fullfilename = directory + '/screwed_csv_' + tday + '.csv'
        
        csvfile = open(fullfilename, 'wb')
        csvwriter = csv.writer(csvfile)
        
        csvwriter.writerow(["Student", "Student ID", "StudentScrewedScore", "#Classes"])

        for s in studentlist:
            csvwriter.writerow([ESPUser.objects.get(id=s[1]).name().encode('ascii', 'ignore'), s[1], s[0], len(self.get_computed_schedule(s[1]))])

        csvfile.close()
        print 'File can be found at: ' + fullfilename
    
    def save_assignments(self, debug_display=False, try_mailman=True):
        """ Store lottery assignments in the database once they have been computed.
            This is a fairly time consuming step compared to computing the assignments. """
            
        self.clear_saved_assignments()
        
        assignments = numpy.nonzero(self.student_sections)
        student_ids = self.student_ids[assignments[0]]
        section_ids = self.section_ids[assignments[1]]
        
        assert(student_ids.shape == section_ids.shape)
        
        relationship, created = RegistrationType.objects.get_or_create(name='Enrolled')
        self.now = datetime.now()   # The time that all the registrations start at, in case all lottery registrations need to be manually reverted later
        StudentRegistration.objects.bulk_create([StudentRegistration(user_id=student_ids[i], section_id=section_ids[i], relationship=relationship, start_date=self.now) for i in range(student_ids.shape[0])])
        print "StudentRegistration enrollments all created to start at %s" % self.now
        if debug_display:
            print 'Created %d registrations' % student_ids.shape[0]
        
        #As mailman has sometimes not worked in the past,
        #leave the option to disable.
        if try_mailman:
            self.update_mailman_lists()
    
    def clear_saved_assignments(self, delete=False):
        """ Expire/delete all previous StudentRegistration enrollments associated with the program. """
        
        old_registrations = StudentRegistration.objects.filter(section__parent_class__parent_program=self.program, relationship__name='Enrolled')
        if delete:
            old_registrations.delete()
        else:
            old_registrations.filter(StudentRegistration.is_valid_qobject()).update(end_date=datetime.now())
        
    def clear_mailman_list(self, list_name):
        contents = list_contents(list_name)
        for address in contents:
            remove_list_member(list_name, address)
        
    def update_mailman_lists(self, delete=True):
        if hasattr(settings, 'USE_MAILMAN') and settings.USE_MAILMAN:
            self.clear_mailman_list("%s_%s-students" % (self.program.program_type, self.program.program_instance))
            for i in range(self.num_sections):
                section = ClassSection.objects.get(id=self.section_ids[i])
                list_names = ["%s-%s" % (section.emailcode(), "students"), "%s-%s" % (section.parent_class.emailcode(), "students")]
                for list_name in list_names:
                    self.clear_mailman_list(list_name)
                for j in range(self.num_students):
                    student = ESPUser.objects.get(id=self.student_ids[i])
                    for list_name in list_names:
                        add_list_member(list_name, student.email)
                    add_list_member("%s_%s-students" % (self.program.program_type, self.program.program_instance), student.email)
        
