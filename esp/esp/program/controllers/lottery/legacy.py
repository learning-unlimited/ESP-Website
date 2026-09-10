from __future__ import absolute_import
from __future__ import division

import logging
import operator
from functools import reduce

import numpy
import numpy.random
from django.db.models import Min

from esp.users.models import ESPUser

from .base import BaseLotteryAssignmentController

logger = logging.getLogger(__name__)


class LegacyLotteryAssignmentController(BaseLotteryAssignmentController):
    """The original randomized greedy fill algorithm: fills sections one at a
    time (grouped by priority level, then by interest), in random order,
    selecting students to admit by weighted random draw when oversubscribed.
    Satisfies the hard constraints but does not directly optimize preference
    satisfaction."""

    default_options = dict(
        BaseLotteryAssignmentController.default_options,
        Kp=(1.2, 'Assignment weight factor for priority students'),
        Ki=(1.1, 'Assignment weight factor for interested students'),
    )

    def clear_assignments(self):
        super(LegacyLotteryAssignmentController, self).clear_assignments()

        #   Weight used to probabilistically deprioritize a student the more
        #   classes they've already been assigned (see fill_section).
        self.student_weights = numpy.ones((self.num_students,))

    def initialize(self):
        super(LegacyLotteryAssignmentController, self).initialize()

        #   Student application ranks (only used when use_student_apps is set).
        #   Derived from the already-populated self.priority/self.interest
        #   arrays rather than re-querying the database.
        self.ranks = 10 * numpy.ones(
            (self.num_students, self.num_sections), dtype=numpy.int32
        )
        if self.options['use_student_apps']:
            for i in range(1, self.effective_priority_limit+1):
                for si, sj in zip(*numpy.nonzero(self.priority[i])):
                    self.ranks[si, sj] = ESPUser.getRankInClass(self.student_ids[si], self.parent_classes[sj])
            for si, sj in zip(*numpy.nonzero(self.interest)):
                self.ranks[si, sj] = ESPUser.getRankInClass(self.student_ids[si], self.parent_classes[sj])

        #   Per-timeslot lunch flag, and the section-overlap ("same subject")
        #   matrix, used by fill_section's per-section candidate filtering.
        self.lunch_schedule = numpy.zeros((self.num_timeslots,))
        for day in self.lunch_timeslots:
            for ts_id in day:
                self.lunch_schedule[self.timeslot_indices[ts_id]] = True

        self.section_overlap = numpy.zeros(
            (self.num_sections, self.num_sections), dtype=numpy.bool
        )
        for i in range(self.num_sections):
            group_ids = numpy.nonzero(self.parent_classes == self.parent_classes[i])[0]
            self.section_overlap[tuple(numpy.meshgrid(group_ids, group_ids))] = True

        if self.options["fill_low_priorities"]:
            #   Which timeslots have a section starting -- only needed by the
            #   fill_low_priorities heuristic below.
            self.section_start_schedules = numpy.zeros(
                (self.num_sections, self.num_timeslots), dtype=numpy.bool
            )
            start_times = numpy.array(self.sections.annotate(start_time=Min('meeting_times')).values_list('id', 'start_time'))
            self.section_start_schedules[self.section_indices[start_times[:, 0]], self.timeslot_indices[start_times[:, 1]]] = True

            #   Compute who has a priority when.  Includes lower priorities, since this is used for places where we check not clobbering priorities.
            self.has_priority = [numpy.zeros((self.num_students, self.num_timeslots), dtype=numpy.bool) for i in range(self.effective_priority_limit+1)]
            for i in range(1, self.effective_priority_limit+1):
                priority_at_least_i = reduce(operator.or_, [self.priority[j] for j in range(i, self.effective_priority_limit+1)])
                numpy.dot(priority_at_least_i, self.section_schedules, out=self.has_priority[i])

            self.sections_at_same_time = numpy.dot(
                self.section_schedules, numpy.transpose(self.section_schedules)
            )

            #   And the same, overlappingly.
            self.has_overlapping_priority = [numpy.zeros((self.num_students, self.num_timeslots), dtype=numpy.bool) for i in range(self.effective_priority_limit+1)]
            for i in range(1, self.effective_priority_limit+1):
                priority_at_least_i = reduce(operator.or_, [self.priority[j] for j in range(i, self.effective_priority_limit+1)])
                numpy.dot(numpy.dot(priority_at_least_i, self.sections_at_same_time), self.section_schedules, out=self.has_overlapping_priority[i])

            #   Fill in preferences for students who haven't ranked them.  In particular, if a student has ranked some level of class in a timeblock (i.e. they plan to be at Splash that timeblock), but has not ranked any priority/n or lower-priority classes overlapping it, add a random class from their interesteds.

            for i in range(1, self.real_priority_limit+1): #Use self.real_priority_limit since we don't want to give people free grade range exceptions!
                should_fill = numpy.transpose(numpy.nonzero(self.has_priority[1]&~self.has_overlapping_priority[i]))
                if len(should_fill):
                    for student, timeslot in should_fill:
                        # student is interested, and class starts in this timeslot, and class does not overlap any lower or equal priorities
                        possible_classes = numpy.nonzero(self.interest[student] & self.section_start_schedules[:, timeslot] & ~numpy.dot(self.section_schedules, numpy.transpose(self.has_priority[i][student])))[0]
                        if len(possible_classes):
                            choice = numpy.random.choice(possible_classes)
                            self.priority[i][student, choice]=True

    def fill_section(self, si, priority=False, rank=10):
        """Assigns students to the section with index si.
        Performs some checks along the way to make sure this didn't break anything."""

        timeslots = numpy.nonzero(self.section_schedules[si,:])[0]

        if self.options["stats_display"]:
            logger.info(
                "-- Filling section %d (index %d, capacity %d, timeslots %s), priority=%s",
                self.section_ids[si],
                si,
                self.section_capacities[si],
                self.timeslot_ids[timeslots],
                priority,
            )

        #   Compute number of spaces - exit if section or program is already full.  Otherwise, set num_spaces to the number of students we can add without overfilling the section or program.
        num_spaces = self.section_capacities[si] - numpy.sum(
            self.student_sections[:, si]
        )
        if self.program_size_max:
            program_spaces_remaining = self.program_size_max - numpy.sum(
                (numpy.sum(self.student_schedules, 1) > 0)
            )
            if program_spaces_remaining == 0:
                if self.options["stats_display"]:
                    logger.info(
                        "   Program was already full with %d students",
                        numpy.sum((numpy.sum(self.student_schedules, 1) > 0)),
                    )
                return True
            else:
                num_spaces = min(num_spaces, program_spaces_remaining)
        if num_spaces == 0:
            if self.options["stats_display"]:
                logger.info(
                    "   Section was already full with %d students",
                    self.section_capacities[si],
                )
            return True
        assert num_spaces > 0

        #   Assign the matrix of sign-up preferences depending on whether we are considering priority bits or not
        if priority:
            signup = self.priority[priority]
            weight_factor = self.options["Kp"]
        else:
            signup = self.interest
            weight_factor = self.options["Ki"]

        #   Check that there is at least one timeslot associated with this section
        if timeslots.shape[0] == 0:
            if self.options["stats_display"]:
                logger.info("   Section was not assigned to any timeslots, aborting")
            return False

        #   Check that this section does not cover all lunch timeslots on any given day
        lunch_overlap = self.lunch_schedule * self.section_schedules[si,:]
        for i in range(self.lunch_timeslots.shape[0]):
            if len(self.lunch_timeslots[i]) != 0 and numpy.sum(lunch_overlap[self.timeslot_indices[self.lunch_timeslots[i]]]) >= (self.lunch_timeslots.shape[1]):
                if self.options['stats_display']: logger.info('   Section covered all lunch timeslots %s on day %d, aborting', self.lunch_timeslots[i,:], i)
                return False

        #   Get students who have indicated interest in the section
        possible_students = numpy.copy(signup[:, si])

        #   Filter students by the section's grade limits
        if self.options["check_grade"] and not (
            priority == self.effective_priority_limit and self.grade_range_exceptions
        ):
            possible_students *= self.student_grades >= self.section_grade_min[si]
            possible_students *= self.student_grades <= self.section_grade_max[si]

        if self.options["use_student_apps"]:
            possible_students *= self.ranks[:, si] == rank

        #   Filter students by who has fewer than the max number of timeslot enrollments
        if self.options['max_sections']:
            possible_students *= (numpy.sum(self.student_sections, axis=1) < self.options['max_sections'])

        #   Filter students by who has fewer than the max number of timeslot enrollments
        if self.options['max_timeslots']:
            possible_students *= (numpy.sum(self.student_schedules, axis=1) < self.options['max_timeslots'])

        #   Filter students by who has all of the section's timeslots available
        for i in range(timeslots.shape[0]):
            possible_students *= numpy.logical_not(
                self.student_schedules[:, timeslots[i]]
            )

        #   Filter students by who is not already registered for a different section of the class
        for sec_index in numpy.nonzero(self.section_overlap[:, si])[0]:
            possible_students *= numpy.logical_not(self.student_sections[:, sec_index])

        #   Filter students by lunch constraint - if class overlaps with lunch period, student must have 1 additional free spot
        #   NOTE: Currently only works with 2 lunch periods per day
        for i in range(timeslots.shape[0]):
            if numpy.sum(self.lunch_timeslots == self.timeslot_ids[timeslots[i]]) > 0:
                lunch_day = numpy.nonzero(
                    self.lunch_timeslots == self.timeslot_ids[timeslots[i]]
                )[0][0]
                for j in range(self.lunch_timeslots.shape[1]):
                    timeslot_index = self.timeslot_indices[
                        self.lunch_timeslots[lunch_day, j]
                    ]
                    if timeslot_index != timeslots[i]:
                        possible_students *= numpy.logical_not(
                            self.student_schedules[:, timeslot_index]
                        )

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
            selected_students = numpy.random.choice(
                candidate_students, num_spaces, replace=False, p=weights
            )
            section_filled = True

        #   Update student section assignments
        #   Check that none of these students are already assigned to this section
        assert numpy.sum(self.student_sections[selected_students, si]) == 0
        self.student_sections[selected_students, si] = True

        #   Update student schedules
        #   Check that none of the students are already occupied in those timeblocks
        for i in range(timeslots.shape[0]):
            assert (
                numpy.sum(self.student_schedules[selected_students, timeslots[i]]) == 0
            )
            self.student_schedules[selected_students, timeslots[i]] = True
            self.student_enrollments[selected_students, timeslots[i]] = (
                self.section_ids[si]
            )

            #   Update student utilies
            if priority:
                self.student_utilities[selected_students] += 1.5
            else:
                self.student_utilities[selected_students] += 1

        #   Update student weights
        self.student_weights[selected_students] /= weight_factor

        if self.options["stats_display"]:
            logger.info(
                "   Added %d/%d students (section filled: %s)",
                selected_students.shape[0],
                candidate_students.shape[0],
                section_filled,
            )

        return section_filled

    def compute_assignments(self, check_result=True):
        """Figure out what students should be assigned to what sections.
        Doesn't actually store results in the database.
        Can be run any number of times."""

        self.clear_assignments()

        ranks = (10,)
        if self.options['use_student_apps']:
            ranks = (10, 5)
        for rank in ranks:
            for i in range(1, self.effective_priority_limit+1):
                if self.options['stats_display']:
                    logger.info('\n== Assigning priority%s students%s',
                                str(i) if self.effective_priority_limit > 1 else '',
                                ' with rank %s' % rank if self.options['use_student_apps'] else '')
                #   Assign priority students to all sections in random order, grouped by duration
                #   so that longer sections aren't disadvantaged by scheduling conflicts
                #   Re-randomize for each priority level so that some sections don't keep getting screwed
                sections_by_length = [
                    numpy.nonzero(numpy.sum(self.section_schedules, axis=1) == j)[0]
                    for j in range(self.num_timeslots, 0, -1)
                ]
                for a in sections_by_length:
                    numpy.random.shuffle(a)
                    for section_index in a:
                        self.fill_section(section_index, priority=i, rank=rank)
            #   Sort sections in increasing order of number of interesting students
            #   TODO: Check with Alex that this is the desired algorithm
            interested_counts = numpy.sum(self.interest, 0)
            sorted_section_indices = numpy.argsort(
                interested_counts.astype(numpy.float) / self.section_capacities
            )
            if self.options["stats_display"]:
                logger.info(
                    "\n== Assigning interested students%s",
                    " with rank %s" % rank if self.options["use_student_apps"] else "",
                )
            for section_index in sorted_section_indices:
                self.fill_section(section_index, priority=False, rank=rank)

        if check_result:
            self.check_assignments()
