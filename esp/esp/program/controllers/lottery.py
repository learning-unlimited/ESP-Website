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
import numpy.random

from datetime import date, datetime

from esp.cal.models import Event
from esp.users.models import ESPUser, StudentInfo
from esp.program.models import StudentRegistration, RegistrationType, RegistrationProfile, ClassSection
from esp.mailman import add_list_member, remove_list_member, list_contents

from django.conf import settings

class LotteryAssignmentController(object):

    default_options = {
        'Kp': 1.2,
        'Ki': 1.1,
        'check_grade': True,
        'stats_display': False,
    }
    
    def __init__(self, program, **kwargs):
        """ Set constant parameters for a lottery assignment. """
        
        self.program = program
        self.num_timeslots = len(self.program.getTimeSlots())
        self.num_students = self.program.students()['lotteried_students'].count()
        self.num_sections = len(self.program.sections().filter(status__gt=0, registration_status=0))
        
        self.options = LotteryAssignmentController.default_options.copy()
        self.options.update(kwargs)
        
        numpy.random.seed(datetime.now().microsecond)
        
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
        
        a1 = numpy.array(qs.order_by('id').values_list('id', flat=True))
        a2 = self.get_index_array(a1)
        return (a1, a2)
        
    def clear_assignments(self):
        """ Reset the state of the controller so that new assignments may be computed,
            but without fetching any information from the database. """
            
        self.student_schedules = numpy.zeros((self.num_students, self.num_timeslots), dtype=numpy.bool)
        self.student_sections = numpy.zeros((self.num_students, self.num_sections), dtype=numpy.bool)
        self.student_weights = numpy.ones((self.num_students,))
        
    def initialize(self):
        """ Gather all of the information needed to run the lottery assignment.
            This includes:
            -   Students' interest (priority and interested bits)
            -   Class schedules and capacities
            -   Timeslots (incl. lunch periods for each day)
        """
        
        self.interest = numpy.zeros((self.num_students, self.num_sections), dtype=numpy.bool)
        self.priority = numpy.zeros((self.num_students, self.num_sections), dtype=numpy.bool)
        self.section_schedules = numpy.zeros((self.num_sections, self.num_timeslots), dtype=numpy.bool)
        self.section_capacities = numpy.zeros((self.num_sections,), dtype=numpy.uint32)
        self.section_overlap = numpy.zeros((self.num_sections, self.num_sections), dtype=numpy.bool)
        
        #   Get student, section, timeslot IDs and prepare lookup table
        (self.student_ids, self.student_indices) = self.get_ids_and_indices(self.program.students()['lotteried_students'])
        (self.section_ids, self.section_indices) = self.get_ids_and_indices(self.program.sections().filter(status__gt=0, registration_status=0))
        (self.timeslot_ids, self.timeslot_indices) = self.get_ids_and_indices(self.program.getTimeSlots())
        
        #   Get IDs of timeslots allocated to lunch by day
        #   (note: requires that this is constant across days)
        self.lunch_schedule = numpy.zeros((self.num_timeslots,))
        lunch_timeslots = Event.objects.filter(meeting_times__parent_class__parent_program=self.program, meeting_times__parent_class__category__category='Lunch').order_by('start').distinct()
        #   Note: this code should not be necessary once lunch-constraints branch is merged (provides Program.dates())
        dates = []
        for ts in self.program.getTimeSlots():
            ts_day = date(ts.start.year, ts.start.month, ts.start.day)
            if ts_day not in dates:
                dates.append(ts_day)
        lunch_by_day = [[] for x in dates]
        ts_count = 0
        for ts in lunch_timeslots:
            d = date(ts.start.year, ts.start.month, ts.start.day)
            lunch_by_day[dates.index(d)].append(ts.id)
            self.lunch_schedule[self.timeslot_indices[ts.id]] = True
        for i in range(len(lunch_by_day)):
            if len(lunch_by_day[i]) > ts_count:
                ts_count = len(lunch_by_day[i])
        self.lunch_timeslots = numpy.zeros((len(lunch_by_day), ts_count), dtype=numpy.int32)
        for i in range(len(lunch_by_day)):
            self.lunch_timeslots[i, :len(lunch_by_day[i])] = numpy.array(lunch_by_day[i])

        now = datetime.now()
        
        #   Populate interest matrix
        interest_regs = StudentRegistration.objects.filter(section__parent_class__parent_program=self.program, relationship__name='Interested', end_date__gte=now).values_list('user__id', 'section__id').distinct()
        ira = numpy.array(interest_regs, dtype=numpy.uint32)
        self.interest[self.student_indices[ira[:, 0]], self.section_indices[ira[:, 1]]] = True
        
        #   Populate priority matrix
        priority_regs = StudentRegistration.objects.filter(section__parent_class__parent_program=self.program, relationship__name='Priority/1', end_date__gte=now).values_list('user__id', 'section__id').distinct()
        pra = numpy.array(priority_regs, dtype=numpy.uint32)
        self.priority[self.student_indices[pra[:, 0]], self.section_indices[pra[:, 1]]] = True
        
        #   Populate section schedule
        section_times = numpy.array(self.program.sections().filter(status__gt=0, registration_status=0).filter(meeting_times__id__isnull=False).distinct().values_list('id', 'meeting_times__id'))
        self.section_schedules[self.section_indices[section_times[:, 0]], self.timeslot_indices[section_times[:, 1]]] = True
        
        #   Populate section overlap matrix
        parent_classes = numpy.array(self.program.sections().filter(status__gt=0, registration_status=0).order_by('id').values_list('parent_class__id', flat=True))
        for i in range(self.num_sections):
            group_ids = numpy.nonzero(parent_classes == parent_classes[i])[0]
            self.section_overlap[numpy.meshgrid(group_ids, group_ids)] = True

        #   Populate section grade limits
        self.section_grade_min = numpy.array(self.program.sections().filter(status__gt=0, registration_status=0).order_by('id').values_list('parent_class__grade_min', flat=True), dtype=numpy.uint32)
        self.section_grade_max = numpy.array(self.program.sections().filter(status__gt=0, registration_status=0).order_by('id').values_list('parent_class__grade_max', flat=True), dtype=numpy.uint32)
        
        #   Populate student grades; grade will be assumed to be 0 if not entered on profile
        self.student_grades = numpy.zeros((self.num_students,))
        gradyear_pairs = numpy.array(RegistrationProfile.objects.filter(user__id__in=list(self.student_ids), most_recent_profile=True, student_info__graduation_year__isnull=False).values_list('user__id', 'student_info__graduation_year'), dtype=numpy.uint32)
        self.student_grades[self.student_indices[gradyear_pairs[:, 0]]] = 12 + ESPUser.current_schoolyear() - gradyear_pairs[:, 1]
        
        #   Find section capacities (TODO: convert to single query)
        for sec in self.program.sections().filter(status__gt=0, registration_status=0):
            self.section_capacities[self.section_indices[sec.id]] = sec.capacity

        # Populate section lengths (hours)
        self.section_lengths = numpy.array([x.nonzero()[0].size for x in self.section_schedules])

    
    def fill_section(self, si, priority=False):
        """ Assigns students to the section with index si.
            Performs some checks along the way to make sure this didn't break anything. """
        
        timeslots = numpy.nonzero(self.section_schedules[si, :])[0]
        
        if self.options['stats_display']: print '-- Filling section %d (index %d, capacity %d, timeslots %s), priority=%s' % (self.section_ids[si], si, self.section_capacities[si], self.timeslot_ids[timeslots], priority)
        
        #   Compute number of spaces - exit if section or program is already full
        num_spaces = self.section_capacities[si] - numpy.sum(self.student_sections[:, si])
        if self.program.program_size_max:
            program_spaces_remaining = self.program.program_size_max - numpy.sum((numpy.sum(self.student_schedules, 1) > 0))
            num_spaces = min(num_spaces, program_spaces_remaining)
            if num_spaces == 0:
                if self.options['stats_display']: print '   Program was already full with %d students' % numpy.sum((numpy.sum(self.student_schedules, 1) > 0))
                return True
        else:
            if num_spaces == 0:
                if self.options['stats_display']: print '   Section was already full with %d students' % self.section_capacities[si]
                return True
        assert(num_spaces > 0)
        
        #   Assign the matrix of sign-up preferences depending on whether we are considering priority bits or not
        if priority:
            signup = self.priority
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
        if self.options['check_grade']:
            possible_students *= (self.student_grades >= self.section_grade_min[si])
            possible_students *= (self.student_grades <= self.section_grade_max[si])
            
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
        
        #   Update student weights
        self.student_weights[selected_students] /= weight_factor
        
        if self.options['stats_display']: print '   Added %d/%d students (section filled: %s)' % (selected_students.shape[0], candidate_students.shape[0], section_filled)
        
        return section_filled

    def compute_assignments(self, check_result=True):
        """ Figure out what students should be assigned to what sections.
            Doesn't actually store results in the database.
            Can be run any number of times. """
            
        self.clear_assignments()
        
        #   Assign priority students to all sections in random order, grouped by duration
        #   so that longer sections aren't disadvantaged by scheduling conflicts
        random_section_indices = numpy.random.choice(self.num_sections, self.num_sections, replace=False)
        random_section_indices = sorted(random_section_indices, key=lambda i : -self.section_lengths[i])
        if self.options['stats_display']: print '\n== Assigning priority students'
        for section_index in random_section_indices:
            self.fill_section(section_index, priority=True)
        
        #   Sort sections in increasing order of number of interesting students
        #   TODO: Check with Alex that this is the desired algorithm
        interested_counts = numpy.sum(self.interest, 0)
        sorted_section_indices = numpy.argsort(interested_counts.astype(numpy.float) / self.section_capacities)
        if self.options['stats_display']: print '\n== Assigning interested students'
        for section_index in sorted_section_indices:
            self.fill_section(section_index, priority=False)
        
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

        priority_matches = self.student_sections * self.priority
        priority_assigned = numpy.sum(priority_matches, 1)
        priority_requested = numpy.sum(self.priority, 1)
        priority_fractions = numpy.nan_to_num(priority_assigned.astype(numpy.float) / priority_requested)

        interest_matches = self.student_sections * self.interest
        interest_assigned = numpy.sum(interest_matches, 1)
        interest_requested = numpy.sum(self.interest, 1)
        interest_fractions = numpy.nan_to_num(interest_assigned.astype(numpy.float) / interest_requested)

        stats['priority_requested'] = priority_requested
        stats['priority_assigned'] = priority_assigned
        stats['interest_requested'] = interest_requested
        stats['interest_assigned'] = interest_assigned
        stats['student_ids'] = self.student_ids
        stats['student_grades'] = self.student_grades
        stats['num_sections'] = self.num_sections
        stats['num_enrolled_students'] = numpy.sum((numpy.sum(self.student_schedules, 1) > 0))
        stats['num_lottery_students'] = self.num_students
        stats['overall_priority_ratio'] = float(numpy.sum(priority_assigned)) / numpy.sum(priority_requested)
        stats['overall_interest_ratio'] = float(numpy.sum(interest_assigned)) / numpy.sum(interest_requested)
        stats['num_registrations'] = numpy.sum(self.student_sections)
        stats['num_full_classes'] = numpy.sum(self.section_capacities == numpy.sum(self.student_sections, 0))
        stats['total_spaces'] = numpy.sum(self.section_capacities)

        #   Compute histograms of assigned vs. requested classes
        hist_priority = {}
        for i in range(self.num_students):
            key = (priority_assigned[i], priority_requested[i])
            if key not in hist_priority:
                hist_priority[key] = 0
            hist_priority[key] += 1
        stats['hist_priority'] = hist_priority

        hist_interest = {}
        for i in range(self.num_students):
            key = (interest_assigned[i], interest_requested[i])
            if key not in hist_interest:
                hist_interest[key] = 0
            hist_interest[key] += 1
        stats['hist_interest'] = hist_interest

        if self.options['stats_display'] or display:
            self.display_stats(stats)
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
            assignments = numpy.nonzero(self.priority[self.student_indices[student_id], :])[0]
        result = []
        for i in range(assignments.shape[0]):
            result.append(ClassSection.objects.get(id=self.section_ids[assignments[i]]))
        return result
    
    def save_assignments(self, debug_display=False, try_mailman=False):
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

        #   As mailman doesn't work, disable for now.
        if try_mailman:
            self.update_mailman_lists()

    def clear_saved_assignments(self, delete=False):
        """ Expire/delete all previous StudentRegistration enrollments associated with the program. """
        
        old_registrations = StudentRegistration.objects.filter(section__parent_class__parent_program=self.program, relationship__name='Enrolled')
        if delete:
            old_registrations.delete()
        else:
            old_registrations.filter(end_date__gte=datetime.now()).update(end_date=datetime.now())
        
    def clear_mailman_list(self, list_name):
        contents = list_contents(list_name)
        for address in contents:
            remove_list_member(list_name, address)
        
    def update_mailman_lists(self, delete=True):
        if hasattr(settings, 'USE_MAILMAN') and settings.USE_MAILMAN:
            self.clear_mailman_list("%s_%s-students" % (self.program.anchor.parent.name, self.program.anchor.name))
            for i in range(self.num_sections):
                section = ClassSection.objects.get(id=self.section_ids[i])
                list_names = ["%s-%s" % (section.emailcode(), "students"), "%s-%s" % (section.parent_class.emailcode(), "students")]
                for list_name in list_names:
                    self.clear_mailman_list(list_name)
                for j in range(self.num_students):
                    student = ESPUser.objects.get(id=self.student_ids[i])
                    for list_name in list_names:
                        add_list_member(list_name, student.email)
                    add_list_member("%s_%s-students" % (self.program.anchor.parent.name, self.program.anchor.name), student.email)
        
