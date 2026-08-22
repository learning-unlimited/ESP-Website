from __future__ import with_statement

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from io import open
from six.moves import range
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
  Email: web-team@learningu.org
"""

import logging

logger = logging.getLogger(__name__)
import numpy
from pkg_resources import parse_version

assert parse_version(numpy.version.short_version) >= parse_version("1.7.0")
import numpy.random

from datetime import date, datetime

from esp.cal.models import Event
from esp.users.models import ESPUser, StudentInfo
from esp.program.models import (
    StudentRegistration,
    StudentSubjectInterest,
    RegistrationType,
    RegistrationProfile,
    ClassSection,
)
from esp.program.models.class_ import ClassCategories
from esp.mailman import add_list_members, remove_list_member, list_contents
from esp.tagdict.models import Tag

from django.conf import settings
import os
import zlib
import base64
import hashlib
import json
import lzma
from io import BytesIO


class LotteryException(Exception):
    """Top level exception class for lottery related problems."""

    pass


class LotterySectionException(LotteryException):
    """Something is wrong with a class section."""

    def __init__(self, section, msg, **kwargs):
        super(LotteryException, self).__init__(
            "Class section %d (%s) %s" % (section.id, section.emailcode(), msg),
            **kwargs
        )


class LotterySubjectException(LotteryException):
    """Something is wrong with a class subject."""

    def __init__(self, subject, msg, **kwargs):
        super(LotteryException, self).__init__(
            "Class subject %s %s" % (subject.emailcode(), msg), **kwargs
        )


def diagnose_bad_section(section, program):
    if section.status <= 0:
        return LotterySectionException(section, "has lottery preferences but is not approved.")
    elif section.registration_status != 0:
        return LotterySectionException(section, "has lottery preferences but is not open to registration.")
    elif not section.meeting_times.exists():
        return LotterySectionException(section, "has lottery preferences but is not scheduled.")
    elif section.parent_class.status <= 0:
        return LotterySubjectException(section.parent_class, "has lottery preferences but is not approved.")
    elif section.parent_class.parent_program != program:
        return LotterySubjectException(
            section.parent_class, "does not belong to the right program."
        )
    else:
        return LotterySectionException(
            section, "is not associated with the lottery (unknown reason)."
        )


class BaseLotteryAssignmentController(object):
    """Shared data extraction, stats, and persistence for lottery assignment
    algorithms. Subclasses implement compute_assignments() (the actual
    assignment step); everything else -- extracting preferences/schedules
    from the database, computing/displaying stats, and saving results -- is
    common to all algorithms."""

    # map from default option key to (default value, help text)
    # help text is false if it should not be displayed on a web interface (specifically, lottery frontend module)
    default_options = {
        'check_grade': (False, 'Whether to validate grade constraints'),
        'stats_display': (False, False),
        'directory': (os.getenv("HOME"), False),
        'use_student_apps': (False, 'Whether to use student application ranks'),
        'fill_low_priorities': (False, 'Whether to push students who have interested classes marked but no priority, to priority'),
        'max_timeslots': (0, 'The maximum number of timeslots for which a student should be enrolled (0 means no limit)'),
        'max_sections': (0, 'The maximum number of sections in which a student should be enrolled (0 means no limit)')
    }

    def __init__(self, program, **kwargs):
        """Set constant parameters for a lottery assignment."""

        self.program = program

        if Tag.getProgramTag("program_size_by_grade", self.program):
            # TODO(benkraft): Consider implementing this.  Stanford's use case
            # as of Fall 2015 (for which program_size_by_grade was written)
            # doesn't need it, but we might want to implement it anyway, or
            # remove the program size logic from the lottery entirely.
            print(
                "WARNING: The lottery doesn't support the "
                "program_size_by_grade Tag yet.  It will run without a "
                "program cap, and allow all students who have marked "
                "preferences to get classes."
            )
            self.program_size_max = 0
        else:
            self.program_size_max = self.program.program_size_max
        students = self.program.students()
        if "twophase_star_students" in students:
            # We can't do the join in SQL, because the query generated takes at least half an hour.  So do it in python.
            stars = set(students['twophase_star_students'].values_list('id', flat=True))
            prioritys = set(students['twophase_priority_students'].values_list('id', flat=True))
            self.lotteried_students = list(stars|prioritys)

        elif "lotteried_students" in students:
            self.lotteried_students = students["lotteried_students"]
        else:
            raise Exception('Cannot retrieve lottery preferences for program, please ensure that it has the lottery module.')
        self.sections = self.program.sections().filter(status__gt=0, parent_class__status__gt=0, registration_status=0, meeting_times__isnull=False).order_by('id').select_related('parent_class', 'parent_class__parent_program').prefetch_related('meeting_times').distinct()
        self.timeslots = self.program.getTimeSlots()
        self.num_timeslots = len(self.timeslots)
        self.num_students = len(self.lotteried_students)
        self.num_sections = len(self.sections)
        self.real_priority_limit = (
            self.program.priorityLimit()
        )  # For most purposes, you probably want to use self.effective_priority_limit instead.
        self.grade_range_exceptions = self.program.useGradeRangeExceptions()
        self.effective_priority_limit = (
            self.real_priority_limit + 1
            if self.grade_range_exceptions
            else self.real_priority_limit
        )

        self.options = {
            key: value[0]
            for key, value in self.default_options.items()
        }
        self.options.update(kwargs)

        self.now = datetime.now()
        numpy.random.seed(self.now.microsecond)

        self.initialize()

        if self.options["stats_display"]:
            logger.info(
                "Initialized lottery assignment for %d students, %d sections, %d timeslots",
                self.num_students,
                self.num_sections,
                self.num_timeslots,
            )

    @staticmethod
    def find_preflight_issues(program):
        """Scan for every condition that would unconditionally make
        initialize() raise a LotteryException for this program. The
        corresponding runtime checks in initialize()/
        put_prefs_in_array() are unchanged and still raise on the first
        problem they actually hit, as a final safety net -- this is purely
        for showing admins the full picture before they submit."""

        issues = []

        if program.sections().filter(
            status__gt=0, parent_class__status__gt=0,
            registration_status=0, meeting_times__isnull=False,
        ).count() == 0:
            issues.append(
                "No eligible sections found for this program. Sections must "
                "be approved, open to registration, and scheduled."
            )

        if len(BaseLotteryAssignmentController.get_lotteried_student_ids(program)) == 0:
            issues.append("No students have signed up for the lottery for this program.")

        good_section_ids = set(
            program.sections()
            .filter(
                status__gt=0,
                parent_class__status__gt=0,
                registration_status=0,
                meeting_times__isnull=False,
            )
            .values_list("id", flat=True)
        )
        relationship_names = [
            "Priority/%s" % i for i in range(program.priorityLimit() + 1)
        ]
        if program.useGradeRangeExceptions():
            relationship_names.append("GradeRangeException")

        bad_section_ids = (
            StudentRegistration.valid_objects()
            .filter(
                section__parent_class__parent_program=program,
                relationship__name__in=relationship_names,
            )
            .exclude(section__id__in=good_section_ids)
            .values_list("section__id", flat=True)
            .distinct()
        )

        bad_sections = ClassSection.objects.filter(
            id__in=list(bad_section_ids)
        ).select_related("parent_class", "parent_class__parent_program").order_by("id")

        issues.extend(str(diagnose_bad_section(section, program)) for section in bad_sections)
        return issues

    def get_index_array(self, arr):
        """Given an array of arbitrary integers, create a new array that maps
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
        """Get an array of the IDs of the objects stored in the QuerySet qs."""

        return numpy.array(qs.order_by("id").values_list("id", flat=True))

    def get_ids_and_indices(self, qs):
        """Get a tuple of the IDs and lookup indices of the objects stored in the QuerySet qs."""

        if "order_by" in dir(qs):
            # We have a QuerySet.
            a1 = numpy.array(qs.order_by("id").values_list("id", flat=True))
        else:
            a1 = numpy.array(qs)
        a2 = self.get_index_array(a1)
        return (a1, a2)

    def clear_assignments(self):
        """Reset the state of the controller so that new assignments may be computed,
        but without fetching any information from the database."""

        self.student_schedules = numpy.zeros(
            (self.num_students, self.num_timeslots), dtype=numpy.bool
        )
        self.student_enrollments = numpy.zeros(
            (self.num_students, self.num_timeslots), dtype=numpy.int32
        )
        self.student_sections = numpy.zeros(
            (self.num_students, self.num_sections), dtype=numpy.bool
        )
        self.student_utilities = numpy.zeros((self.num_students,), dtype=numpy.float)

    def put_prefs_in_array(self, prefs, array):
        """Helper function for self.initialize().

        Given ValuesListQuerySet of preferences (student, section) and a students-by-sections array (likely self.interest or self.priority[i]), set the entries of the array corresponding to the preferences True.  Check that all values in question are valid.

        prefs should be a ValuesListQuerySet of tuples (user, section), such as that generated by StudentRegistration.objects.filter(...).values_list('user__id', 'section__id').distinct().
        array should be a boolean array of dimension self.num_students by self.num_sections, such as self.interest or self.priority[i].
        """
        if prefs.exists():
            pref_array = numpy.array(prefs, dtype=numpy.uint32)
            student_ixs = self.student_indices[pref_array[:, 0]]
            section_ixs = self.section_indices[pref_array[:, 1]]

            #   - Missing student (this should never happen and would indicate an error in the code)
            assert (
                numpy.min(student_ixs) >= 0
            ), "Got a preference for a student who doesn't exist!"

            #   - Missing section (this can happen due to factors outside the code's control)
            if numpy.min(section_ixs) < 0:
                #   Try to diagnose what is wrong with the sections we are not tracking
                bad_section_id = pref_array[numpy.nonzero(section_ixs < 0)[0][0], 1]
                #   Use .get(), since all class sections should be present in the database.
                #   (If any does not exist, that is a problem with the code and should cause
                #   a server error.)
                bad_section = ClassSection.objects.get(id=bad_section_id)
                raise diagnose_bad_section(bad_section, self.program)

            array[student_ixs, section_ixs] = True

    def initialize(self):
        """Gather all of the information needed to run the lottery assignment.
        This includes:
        -   Students' interest (priority and interested bits)
        -   Class schedules and capacities
        -   Timeslots (incl. lunch periods for each day)
        """

        if self.num_sections == 0:
            raise LotteryException(
                "No eligible sections found for this program. "
                "Sections must be approved, open to registration, and scheduled."
            )
        if self.num_students == 0:
            raise LotteryException(
                "No students have signed up for the lottery for this program."
            )

        self.interest = numpy.zeros(
            (self.num_students, self.num_sections), dtype=numpy.bool
        )
        self.priority = [
            numpy.zeros((self.num_students, self.num_sections), dtype=numpy.bool)
            for i in range(self.effective_priority_limit + 1)
        ]
        self.section_schedules = numpy.zeros(
            (self.num_sections, self.num_timeslots), dtype=numpy.bool
        )
        self.section_capacities = numpy.zeros((self.num_sections,), dtype=numpy.uint32)
        self.section_labels = numpy.zeros((self.num_sections,), dtype=object)

        # One array to keep track of the utility of each student
        # (defined as hours of interested class + 1.5*hours of priority classes)
        # and the other arrary to keep track of student weigths (defined as # of classes signed up for)
        self.student_utility_weights = numpy.zeros(
            (self.num_students,), dtype=numpy.float
        )
        self.student_utilities = numpy.zeros((self.num_students,), dtype=numpy.float)

        #   Get student, section, timeslot IDs and prepare lookup table
        (self.student_ids, self.student_indices) = self.get_ids_and_indices(
            self.lotteried_students
        )
        (self.section_ids, self.section_indices) = self.get_ids_and_indices(
            self.sections
        )
        (self.timeslot_ids, self.timeslot_indices) = self.get_ids_and_indices(
            self.timeslots
        )
        self.parent_classes = numpy.array(
            self.sections.values_list("parent_class__id", flat=True)
        )

        #   Get IDs of timeslots allocated to lunch by day
        #   (note: requires that this is constant across days)
        lunch_timeslots = (
            Event.objects.filter(
                meeting_times__parent_class__parent_program=self.program,
                meeting_times__parent_class__category__category="Lunch",
            )
            .order_by("start")
            .distinct()
        )
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
        self.lunch_timeslots = numpy.array(lunch_by_day)

        #   Populate interest matrix; this uses both the StudentRegistrations (which apply to a particular section) and StudentSubjectIntegests (which apply to all sections of the class).  If one does not exist, ignore it.  Be careful to only return SRs and SSIs for accepted sections of accepted classes; this might matter for SSIs where only some sections of the class are accepted.
        interest_regs_sr = (
            StudentRegistration.valid_objects()
            .filter(
                section__parent_class__parent_program=self.program,
                section__status__gt=0,
                section__parent_class__status__gt=0,
                section__registration_status=0,
                section__meeting_times__isnull=False,
                relationship__name="Interested",
            )
            .values_list("user__id", "section__id")
            .distinct()
        )
        interest_regs_ssi = (
            StudentSubjectInterest.valid_objects()
            .filter(
                subject__parent_program=self.program,
                subject__status__gt=0,
                subject__sections__status__gt=0,
                subject__sections__registration_status=0,
                subject__sections__meeting_times__isnull=False,
            )
            .values_list("user__id", "subject__sections__id")
            .distinct()
        )
        self.put_prefs_in_array(interest_regs_sr, self.interest)
        self.put_prefs_in_array(interest_regs_ssi, self.interest)

        #   Populate priority matrix
        priority_regs = [
            StudentRegistration.valid_objects()
            .filter(
                section__parent_class__parent_program=self.program,
                relationship__name="Priority/%s" % i,
            )
            .values_list("user__id", "section__id")
            .distinct()
            for i in range(self.real_priority_limit + 1)
        ]
        if self.grade_range_exceptions:
            priority_regs.append(StudentRegistration.valid_objects().filter(section__parent_class__parent_program=self.program, relationship__name='GradeRangeException').values_list('user__id', 'section__id').distinct())
        for i in range(1, self.effective_priority_limit+1):
            self.put_prefs_in_array(priority_regs[i], self.priority[i])

        #   Set student utility weights. Counts number of classes that students selected. Used only for computing the overall_utility stat
        self.student_utility_weights = numpy.sum(self.interest.astype(float), 1) + sum([numpy.sum(self.priority[i].astype(float), 1) for i in range(1, self.effective_priority_limit+1)])

        #   Populate section schedule
        section_times = numpy.array(self.sections.values_list('id', 'meeting_times__id'))
        self.section_schedules[self.section_indices[section_times[:, 0]], self.timeslot_indices[section_times[:, 1]]] = True

        #   Populate section grade limits
        self.section_grade_min = numpy.array(
            self.sections.values_list("parent_class__grade_min", flat=True),
            dtype=numpy.uint32,
        )
        self.section_grade_max = numpy.array(
            self.sections.values_list("parent_class__grade_max", flat=True),
            dtype=numpy.uint32,
        )

        #   Populate student grades; grade will be assumed to be 0 if not entered on profile
        self.student_grades = numpy.zeros((self.num_students,))
        gradyear_pairs = numpy.array(
            RegistrationProfile.objects.filter(
                user__id__in=list(self.student_ids),
                most_recent_profile=True,
                student_info__graduation_year__isnull=False,
            ).values_list("user__id", "student_info__graduation_year"),
            dtype=numpy.uint32,
        )
        self.student_grades[self.student_indices[gradyear_pairs[:, 0]]] = (
            12 + ESPUser.program_schoolyear(self.program) - gradyear_pairs[:, 1]
        )

        #   Find section capacities and email-code labels (TODO: convert to single query)
        for sec in self.sections:
            self.section_capacities[self.section_indices[sec.id]] = sec.capacity
            self.section_labels[self.section_indices[sec.id]] = sec.emailcode()

        # Populate section lengths (hours)
        self.section_lengths = numpy.array(
            [x.nonzero()[0].size for x in self.section_schedules]
        )

    def compute_assignments(self, check_result=True):
        """Figure out what students should be assigned to what sections.
        Doesn't actually store results in the database.
        Can be run any number of times.

        Must be implemented by a subclass -- this is where the algorithms
        (legacy randomized greedy fill, ILP, ...) differ."""

        raise NotImplementedError(
            "compute_assignments() must be implemented by a subclass of "
            "BaseLotteryAssignmentController."
        )

    def check_assignments(self):
        """Check the result for desired properties, before it is saved."""

        #   Check that no sections are overfilled
        assert (
            numpy.sum(numpy.sum(self.student_sections, 0) > self.section_capacities)
            == 0
        )

        #   Check that no student's schedule violates the lunch constraints: 1 or more open lunch periods per day
        for i in range(self.lunch_timeslots.shape[0]):
            timeslots = numpy.array([]) if (self.lunch_timeslots[i].shape[0] == 0) else self.timeslot_indices[self.lunch_timeslots[i,:]]
            if (timeslots.shape[0] == 0): continue
            assert(numpy.sum(numpy.sum(self.student_schedules[:, timeslots] > self.lunch_timeslots.shape[1] - 1)) == 0)

        #   Check that each student's schedule is consistent with their assigned sections
        for i in range(self.num_students):
            assert(numpy.sum(self.student_schedules[i,:] != numpy.sum(self.section_schedules[numpy.nonzero(self.student_sections[i,:])[0],:], 0)) == 0)

    def compute_stats(self, display=True):
        """Compute statistics to provide feedback to the user about how well the
        lottery assignment worked."""

        stats = {}

        priority_matches = [
            self.student_sections * self.priority[i]
            for i in range(self.effective_priority_limit + 1)
        ]
        priority_assigned = [
            numpy.sum(priority_matches[i], 1)
            for i in range(self.effective_priority_limit + 1)
        ]
        priority_requested = [
            numpy.sum(self.priority[i], 1)
            for i in range(self.effective_priority_limit + 1)
        ]
        priority_fractions = [0 for i in range(self.effective_priority_limit + 1)]

        # We expect that there will occasionally be 0/0 division errors,
        # whenver a student has not specified any classes for a particular
        # priority level.  We handle this by calling nan_to_num(), but by
        # default numpy will still raise and print a RuntimeWarning.  We can
        # safely ignore this by passing 'ignore' to the errstate() context
        # manager.  However, if display mode is on, then we can still print
        # these warnings along with the rest of the debugging messages by
        # passing 'warn'.
        np_errstate = "warn" if display else "ignore"

        for i in range(1, self.effective_priority_limit+1):
            with numpy.errstate(divide=np_errstate, invalid=np_errstate):
                priority_fractions[i] = numpy.nan_to_num(
                    priority_assigned[i].astype(numpy.float) / priority_requested[i]
                )

        interest_matches = self.student_sections * self.interest
        interest_assigned = numpy.sum(interest_matches, 1)
        interest_requested = numpy.sum(self.interest, 1)
        with numpy.errstate(divide=np_errstate, invalid=np_errstate):
            interest_fractions = numpy.nan_to_num(
                interest_assigned.astype(numpy.float) / interest_requested
            )

        if self.effective_priority_limit > 1:
            for i in range(1, self.effective_priority_limit+1):
                stats['priority_%s_requested'%i] = priority_requested[i]
                stats['priority_%s_assigned'%i] = priority_assigned[i]
                stats['overall_priority_%s_ratio'%i] = float(numpy.sum(priority_assigned[i])) / numpy.sum(priority_requested[i])
        else:
            stats["priority_requested"] = priority_requested[1]
            stats["priority_assigned"] = priority_assigned[1]
            stats["overall_priority_ratio"] = float(
                numpy.sum(priority_assigned[1])
            ) / numpy.sum(priority_requested[1])

        if self.options['use_student_apps']:
            stats['ranks'] = self.ranks
            for rank in (10, 5, 1):
                stats['rank_%s_assigned'%rank] = numpy.logical_and(self.ranks == rank, self.student_sections)
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

        #   Timeslot-based metrics
        stats["timeslots_filled"] = numpy.sum(self.student_schedules, axis=1)
        for j in range(1, self.effective_priority_limit + 1):
            stats["timeslots_priority_%s" % j] = numpy.dot(
                self.priority[j], self.section_schedules
            ).sum(axis=1)
        stats["hist_timeslots_filled"] = dict(
            enumerate(numpy.bincount(stats["timeslots_filled"]))
        )

        #   Compute histograms of assigned vs. requested classes
        hist_priority = [{} for i in range(self.effective_priority_limit+1)]
        for j in range(1, self.effective_priority_limit+1):
            for i in range(self.num_students):
                key = (priority_assigned[j][i], priority_requested[j][i])
                if key not in hist_priority[j]:
                    hist_priority[j][key] = 0
                hist_priority[j][key] += 1
            if self.options["use_student_apps"]:
                stats["hist_priority_%s" % j] = hist_priority[j]
        if not self.options["use_student_apps"]:
            stats["hist_priority"] = hist_priority[1]

        hist_interest = {}
        for i in range(self.num_students):
            key = (interest_assigned[i], interest_requested[i])
            if key not in hist_interest:
                hist_interest[key] = 0
            hist_interest[key] += 1
        stats['hist_interest'] = hist_interest

        #   Section-filledness distribution.  Computed entirely from arrays
        #   populated in initialize() (section_capacities/section_labels) --
        #   no per-section DB queries -- so that from_snapshot() can drive
        #   this from a frozen LotteryInputSnapshot with no DB access at all.
        section_filledness=[]
        for n in range(self.num_sections):
            pref_array=numpy.zeros((self.num_students,), dtype=numpy.bool_)
            pref_array=numpy.logical_or(pref_array,self.interest[:,n])
            for rank_level in self.priority:
                pref_array=numpy.logical_or(pref_array,rank_level[:,n])
            num_prefs=numpy.sum(pref_array)

            section_capacity = self.section_capacities[n] or 0
            if section_capacity==0 or num_prefs==0:
                continue

            enrolled_array=self.student_sections[:,n]
            num_enrolled=numpy.sum(enrolled_array)

            # Capacity, not the old "expected capacity" heuristic
            # (min(capacity, num_prefs//2)) -- how full a section actually
            # is against what it can actually hold.
            enrollment_percentage=100*num_enrolled/section_capacity

            section_filledness.append((self.section_labels[n],enrollment_percentage))
        stats['section_filledness']=section_filledness

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
        sum_of_weights = 0.0
        screwed_students = []
        for i in range(self.num_students):
            utility = numpy.sqrt(self.student_utilities[i])
            weight = numpy.sqrt((self.student_utility_weights[i]))
            weighted_overall_utility += utility * weight
            sum_of_weights += weight
            screwed_students.append(((1 + utility) / (1 + weight), self.student_ids[i]))

        overall_utility = weighted_overall_utility / sum_of_weights
        screwed_students.sort()

        stats["overall_utility"] = overall_utility
        stats["students_by_screwedness"] = screwed_students


        if self.options["stats_display"] or display:
            self.display_stats(stats)

        self.stats = stats
        return stats

    def display_stats(self, stats):
        logger.info("Lottery results for %s", self.program.niceName())
        logger.info("--------------------------------------")
        for label, lines in self.extract_stats(stats):
            logger.info("%s:", label.title())
            for line in lines:
                logger.info(line)
        """
        logger.info('Example results:')
        no_pri_indices = numpy.nonzero(stats['priority_assigned'] == 0)[0]
        logger.info('1) First %d students who got none of their priority classes:', min(5, no_pri_indices.shape[0]))
        for i in range(min(5, no_pri_indices.shape[0])):
            sid = stats['student_ids'][no_pri_indices[i]]
            student = ESPUser.objects.get(id=sid)
            logger.info('   Student: %s (grade %s)', student.name(), student.getGrade())
            cs_ids = self.section_ids[numpy.nonzero(self.priority[no_pri_indices[i], :])[0]]
            logger.info('   - Priority classes: %s', ClassSection.objects.filter(id__in=list(cs_ids)))
            cs_ids = self.section_ids[numpy.nonzero(self.interest[no_pri_indices[i], :])[0]]
            logger.info('   - Interested classes: %s', ClassSection.objects.filter(id__in=list(cs_ids)))
            """

    def extract_stats(self, stats):
        sections = []

        student_distribution = []
        for i, count in stats['hist_timeslots_filled'].items():
            student_distribution.append('%6d students got a schedule with %d filled slots' % (count, i))
        sections.append(('student schedule-filledness distribution', student_distribution))

        section_distribution=[]
        section_filledness_percentage_bin_step=10
        for filledness_percentage_bin in range(0,100,section_filledness_percentage_bin_step):
            num_secs=0
            next_bin_step=filledness_percentage_bin+section_filledness_percentage_bin_step
            is_last_bin=next_bin_step>=100
            for section, filledness_percentage in stats['section_filledness']:
                if filledness_percentage_bin<=filledness_percentage and (filledness_percentage<next_bin_step or is_last_bin):
                    num_secs+=1
            if is_last_bin:
                section_distribution.append('%6d sections at %d%% or more of capacity'%(num_secs,filledness_percentage_bin))
            else:
                section_distribution.append('%6d sections at %d%%-%d%% of capacity'%(num_secs,filledness_percentage_bin,next_bin_step))
        sections.append(('section-filledness distribution',section_distribution))

        sections.append(('counts', [
            '%6d students applied to the lottery' % stats['num_lottery_students'],
            '%6d students were enrolled in at least 1 class' % stats['num_enrolled_students'],
            '%6d total enrollments' % stats['num_registrations'],
            '%6d available sections' % stats['num_sections'],
            '%6d sections were filled to capacity' % stats['num_full_classes'],
        ]))

        ratios = []
        if self.effective_priority_limit>1:
            for i in range(1, self.effective_priority_limit+1):
                ratios.append('%2.2f%% of priority %s classes were enrolled' % (stats['overall_priority_%s_ratio' % i] * 100.0, i))
        else:
            ratios.append('%2.2f%% of priority classes were enrolled' % (stats['overall_priority_ratio'] * 100.0))
        ratios.append('%2.2f%% of interested classes were enrolled' % (stats['overall_interest_ratio'] * 100.0))
        sections.append(('ratios', ratios))

        return sections

    def chart_constructor(self, labels, values, xaxis_label, yaxis_label, title):
        # Constructs a dict to be converted to json and used to make a chart.js chart

        return {
            'type':'bar',
            'data':{
                'labels': labels,
                'datasets':[
                    {
                        'data': values,
                        'label': yaxis_label,
                        'backgroundColor':'#456900',
                    },
                ],
            },
            'options': {
                'responsive': False,
                'animation': False,
                'events': [],
                'plugins': {
                    'legend': {'display': False},
                    'title': {
                        'display': True,
                        'text': title
                    },
                },
                'scales': {
                    'x': {
                        'title': {
                            'text': xaxis_label,
                            'display': True
                        },
                    },
                    'y': {
                        'title': {
                            'text': yaxis_label,
                            'display': True
                        },
                    },
                },
            },
        }

    def extract_chart_stats(self, stats):
        charts=[]

        student_distribution_labels = []
        student_distribution_values = []
        for i, count in stats['hist_timeslots_filled'].items():
            student_distribution_labels.append(int(i))
            student_distribution_values.append(int(count))
        charts.append(self.chart_constructor(student_distribution_labels,student_distribution_values,'num filled slots in schedule','num students w/ this many filled slots', 'student schedule-filledness distribution'))

        section_distribution_labels=[]
        section_distribution_values=[]
        section_filledness_percentage_bin_step=10
        for filledness_percentage_bin in range(0,100,section_filledness_percentage_bin_step):
            num_secs=0
            next_bin_step=filledness_percentage_bin+section_filledness_percentage_bin_step
            is_last_bin=next_bin_step>=100
            for section, filledness_percentage in stats['section_filledness']:
                if filledness_percentage_bin<=filledness_percentage and (filledness_percentage<next_bin_step or is_last_bin):
                    num_secs+=1
            section_distribution_values.append(num_secs)
            if is_last_bin:
                section_distribution_labels.append('%d%% or more'%filledness_percentage_bin)
            else:
                section_distribution_labels.append('%d%%-%d%%'%(filledness_percentage_bin,next_bin_step))
        charts.append(self.chart_constructor(section_distribution_labels,section_distribution_values,'percentage filled of section\'s capacity','num sections w/ this filledness', 'section-filledness distribution'))

        return charts

    def get_computed_schedule(self, student_id, mode='assigned'):
        #   mode can be 'assigned', 'interested', or 'priority'
        if mode == 'assigned':
            assignments = numpy.nonzero(self.student_sections[self.student_indices[student_id],:])[0]
        elif mode == 'interested':
            assignments = numpy.nonzero(self.interest[self.student_indices[student_id],:])[0]
        elif mode == 'priority':
            assignments = numpy.nonzero(self.priority[1][self.student_indices[student_id],:])[0]
        else:
            import re

            p = re.search(r"(?<=priority_)\d*", mode).group(0)
            if p:
                assignments = numpy.nonzero(self.priority[p][self.student_indices[student_id],:])[0]
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

        if directory is None:
            directory = self.options['directory']

        if stats is None:
            stats = self.compute_stats(display=False) #Calculate stats if I didn't get any

        studentlist = stats['students_by_screwedness']
        if n is not None: studentlist = studentlist[:n]
        tday = datetime.today().strftime('%Y-%m-%d')

        fullfilename = directory + "/screwed_csv_" + tday + ".csv"

        csvfile = open(fullfilename, "wb")
        csvwriter = csv.writer(csvfile)

        csvwriter.writerow(["Student", "Student ID", "StudentScrewedScore", "#Classes"])

        for s in studentlist:
            csvwriter.writerow(
                [
                    ESPUser.objects.get(id=s[1]).name().encode("ascii", "ignore"),
                    s[1],
                    s[0],
                    len(self.get_computed_schedule(s[1])),
                ]
            )

        csvfile.close()
        logger.info("File can be found at: %s", fullfilename)

    def save_assignments(self, try_mailman=True):
        """Store lottery assignments in the database once they have been computed.
        This is a fairly time consuming step compared to computing the assignments."""

        self.clear_saved_assignments()

        assignments = numpy.nonzero(self.student_sections)
        student_ids = self.student_ids[assignments[0]]
        section_ids = self.section_ids[assignments[1]]

        assert student_ids.shape == section_ids.shape

        relationship, created = RegistrationType.objects.get_or_create(name='Enrolled')
        self.now = datetime.now()   # The time that all the registrations start at, in case all lottery registrations need to be manually reverted later
        srs = StudentRegistration.objects.bulk_create([StudentRegistration(user_id=student_ids[i], section_id=section_ids[i], relationship=relationship, start_date=self.now) for i in range(student_ids.shape[0])])
        # Trigger any relevant caches
        for sr in srs:
            sr.save()
        if self.options['stats_display']:
            logger.info("StudentRegistration enrollments all created to start at %s", self.now)
            logger.info('Created %d registrations', student_ids.shape[0])

        # As mailman has sometimes not worked in the past,
        # leave the option to disable.
        if try_mailman:
            self.update_mailman_lists()

    def clear_saved_assignments(self, delete=False):
        """Expire/delete all previous StudentRegistration enrollments associated with the program."""

        old_registrations = StudentRegistration.objects.filter(
            section__parent_class__parent_program=self.program,
            relationship__name="Enrolled",
        )
        if delete:
            old_registrations.delete()
        else:
            old_registrations.filter(StudentRegistration.is_valid_qobject()).update(
                end_date=datetime.now()
            )

    def export_assignments(self):
        def export_array(arr):
            s = BytesIO()
            numpy.savetxt(s, arr)
            return s.getvalue()

        student_sections = export_array(self.student_sections)
        student_ids = export_array(self.student_ids)
        section_ids = export_array(self.section_ids)
        return base64.b64encode(zlib.compress(student_sections + b'|' + student_ids + b'|' + section_ids)).decode()

    def import_assignments(self, data):
        data_parts = zlib.decompress(base64.b64decode(data.encode())).split(b'|')

        if len(data_parts) != 3:
            raise ValueError(
                "provided lottery_data is corrupted (doesn't contain three parts)"
            )

        # ndmin is for corner cases where one of the array dimensions is 1.  If you don't include the ndmin parameter,
        # then "mono-dimensional axes will be squeezed" (see the numpy documentation), and the resulting array
        # would not have the right shape.
        self.student_sections = numpy.loadtxt(BytesIO(data_parts[0]), ndmin=2)
        self.student_ids = numpy.loadtxt(BytesIO(data_parts[1]), ndmin=1)
        self.section_ids = numpy.loadtxt(BytesIO(data_parts[2]), ndmin=1)

    @staticmethod
    def clear_mailman_list(list_name):
        contents = list_contents(list_name)
        for address in contents:
            remove_list_member(list_name, address)

    def update_mailman_lists(self, delete=True):
        if hasattr(settings, "USE_MAILMAN") and settings.USE_MAILMAN:
            program_list = "%s_%s-students" % (
                self.program.program_type,
                self.program.program_instance,
            )
            self.clear_mailman_list(program_list)
            # Add all registered students into the program mailing list, even
            # if they didn't get enrolled into any classes.
            add_list_members(
                program_list,
                ESPUser.objects.filter(id__in=list(self.student_ids)).distinct(),
            )
            for i in range(self.num_sections):
                section = ClassSection.objects.get(id=self.section_ids[i])
                list_names = ["%s-%s" % (section.emailcode(), "students"), "%s-%s" % (section.parent_class.emailcode(), "students")]
                student_ids = self.student_ids[numpy.nonzero(self.student_sections[:, i])]
                students = ESPUser.objects.filter(id__in=student_ids).distinct()
                for list_name in list_names:
                    self.clear_mailman_list(list_name)
                    add_list_members(list_name, students)

    # ------------------------------------------------------------------
    # Frozen-snapshot persistence (LotteryInputSnapshot/LotteryRun):
    # canonical extraction, content-addressed hashing, and DB-free stats
    # reconstruction, for the async/remote-solved ILP run flow.
    # ------------------------------------------------------------------

    def snapshot_data(self):
        """Canonical, DB-independent serialization of the extracted lottery
        *input data* for this run (deliberately excludes algorithm/weight
        params, and excludes anything only needed for computing assignments
        rather than stats -- e.g. lunch/grade data, which matter before
        capture, not after). Feeds both input_hash() (so identical
        extractions on the same program dedup to one stored snapshot) and
        the blob from_snapshot() reconstructs frozen stats from.

        Student ids are kept as literal DB ids (JSON string keys) --
        remapping them to dense indices didn't save anything after
        compression. Section/timeslot ids ARE remapped to dense indices,
        with "sections"/"timeslots" as the id lookup tables."""

        priority_regs = []
        for i in range(1, self.effective_priority_limit + 1):
            level = {}
            for si, sj in zip(*numpy.nonzero(self.priority[i])):
                level.setdefault(str(int(self.student_ids[si])), []).append(int(sj))
            for section_idxs in level.values():
                section_idxs.sort()
            priority_regs.append(level)

        interests = {}
        for si, sj in zip(*numpy.nonzero(self.interest)):
            interests.setdefault(str(int(self.student_ids[si])), []).append(int(sj))
        for section_idxs in interests.values():
            section_idxs.sort()

        section_times = {}
        for sj, t in zip(*numpy.nonzero(self.section_schedules)):
            section_times.setdefault(str(int(sj)), []).append(int(t))
        for timeslot_idxs in section_times.values():
            timeslot_idxs.sort()

        return {
            "students": [int(x) for x in self.student_ids],
            "priority_regs": priority_regs,
            "interests": interests,
            "sections": [int(x) for x in self.section_ids],
            "section_labels": [str(x) for x in self.section_labels],
            "timeslots": [int(x) for x in self.timeslot_ids],
            "section_capacities": {str(sj): int(self.section_capacities[sj]) for sj in range(self.num_sections)},
            "section_times": section_times,
        }

    def _canonical_snapshot_bytes(self):
        # sort_keys makes this independent of dict/query insertion order,
        # not just human-readable -- both the hash and the stored blob rely
        # on that determinism.
        return json.dumps(self.snapshot_data(), sort_keys=True, separators=(',', ':')).encode('utf-8')

    def input_hash(self):
        """SHA-256 of the canonical snapshot -- identical data (independent
        of query order and of all params) always hashes the same, so
        param-iterations on the same program's data share one
        LotteryInputSnapshot row."""

        return hashlib.sha256(self._canonical_snapshot_bytes()).hexdigest()

    def encode_snapshot_blob(self):
        """xz-compressed canonical JSON, for LotteryInputSnapshot.data."""

        return lzma.compress(self._canonical_snapshot_bytes())

    @classmethod
    def decode_snapshot_blob(cls, blob):
        return json.loads(lzma.decompress(blob).decode('utf-8'))

    @classmethod
    def from_snapshot(cls, program, snapshot_data, enrolled_pairs):
        """Reconstruct just enough state to run compute_stats()/
        extract_stats()/extract_chart_stats() -- entirely from a frozen
        LotteryInputSnapshot + a run's enrolled_pairs, with NO database
        access at all, so the resulting stats stay frozen to the run's
        moment even if the live program data changes afterward. Bypasses
        __init__()/initialize() (no live DB extraction) via cls.__new__()."""

        self = cls.__new__(cls)
        self.program = program
        self.options = {key: value[0] for key, value in cls.default_options.items()}

        priority_regs = snapshot_data["priority_regs"]
        interests = snapshot_data["interests"]
        sections = snapshot_data["sections"]

        self.effective_priority_limit = len(priority_regs)
        self.num_sections = len(sections)
        self.num_timeslots = len(snapshot_data["timeslots"])

        student_ids_list = [int(sid) for sid in snapshot_data["students"]]
        self.num_students = len(student_ids_list)
        self.student_ids = numpy.array(student_ids_list)
        student_indices = {sid: i for i, sid in enumerate(student_ids_list)}

        self.section_ids = numpy.array(sections)
        self.section_labels = numpy.array(snapshot_data["section_labels"], dtype=object)
        self.timeslot_ids = numpy.array(snapshot_data["timeslots"])
        section_id_to_idx = {sid: i for i, sid in enumerate(sections)}

        self.interest = numpy.zeros((self.num_students, self.num_sections), dtype=numpy.bool)
        for sid_str, section_idxs in interests.items():
            si = student_indices[int(sid_str)]
            for sj in section_idxs:
                self.interest[si, sj] = True

        self.priority = [numpy.zeros((self.num_students, self.num_sections), dtype=numpy.bool)]
        for level in priority_regs:
            level_array = numpy.zeros((self.num_students, self.num_sections), dtype=numpy.bool)
            for sid_str, section_idxs in level.items():
                si = student_indices[int(sid_str)]
                for sj in section_idxs:
                    level_array[si, sj] = True
            self.priority.append(level_array)

        self.section_capacities = numpy.zeros((self.num_sections,), dtype=numpy.uint32)
        for sj_str, cap in snapshot_data["section_capacities"].items():
            self.section_capacities[int(sj_str)] = cap

        self.section_schedules = numpy.zeros((self.num_sections, self.num_timeslots), dtype=numpy.bool)
        for sj_str, timeslot_idxs in snapshot_data["section_times"].items():
            for t in timeslot_idxs:
                self.section_schedules[int(sj_str), t] = True

        # Not part of the frozen snapshot (compute_stats only passes this
        # through informationally, nothing derives from it) -- zero-filled.
        self.student_grades = numpy.zeros((self.num_students,))

        self.student_utility_weights = numpy.sum(self.interest.astype(float), 1) + sum(
            numpy.sum(self.priority[i].astype(float), 1) for i in range(1, self.effective_priority_limit + 1)
        )

        self.student_sections = numpy.zeros((self.num_students, self.num_sections), dtype=numpy.bool)
        self.student_schedules = numpy.zeros((self.num_students, self.num_timeslots), dtype=numpy.bool)
        self.student_enrollments = numpy.zeros((self.num_students, self.num_timeslots), dtype=numpy.int32)
        self.student_utilities = numpy.zeros((self.num_students,), dtype=numpy.float)

        for student_id, section_id in enrolled_pairs:
            si = student_indices.get(student_id)
            sj = section_id_to_idx.get(section_id)
            if si is None or sj is None:
                continue  # shouldn't happen for a well-formed run; don't blow up stats over it
            self.student_sections[si, sj] = True
            is_priority = any(
                self.priority[i][si, sj] for i in range(1, self.effective_priority_limit + 1)
            )
            utility_per_timeslot = 1.5 if is_priority else 1.0
            for t in numpy.nonzero(self.section_schedules[sj])[0]:
                self.student_schedules[si, t] = True
                self.student_enrollments[si, t] = section_id
                self.student_utilities[si] += utility_per_timeslot

        return self

    @classmethod
    def save_from_pairs(cls, program, enrolled_pairs, lotteried_student_ids=None, try_mailman=True):
        """Save lottery results directly from sparse (student_id, section_id)
        pairs -- e.g. a completed remote/async run's captured result. Mirrors
        save_assignments()."""

        old_registrations = StudentRegistration.objects.filter(
            section__parent_class__parent_program=program,
            relationship__name="Enrolled",
        )
        old_registrations.filter(StudentRegistration.is_valid_qobject()).update(end_date=datetime.now())

        relationship, created = RegistrationType.objects.get_or_create(name='Enrolled')
        now = datetime.now()
        srs = StudentRegistration.objects.bulk_create([
            StudentRegistration(user_id=student_id, section_id=section_id, relationship=relationship, start_date=now)
            for student_id, section_id in enrolled_pairs
        ])
        for sr in srs:
            sr.save()

        if try_mailman:
            if lotteried_student_ids is None:
                lotteried_student_ids = cls.get_lotteried_student_ids(program)
            cls._update_mailman_lists_from_pairs(program, enrolled_pairs, lotteried_student_ids)

    @staticmethod
    def get_lotteried_student_ids(program):
        """The full set of student ids currently entered in the lottery for
        `program` -- same derivation __init__ uses for self.lotteried_students,
        factored out as a *live* fallback for save_from_pairs()'s mailman
        sync when no frozen roster (from a LotteryInputSnapshot) is
        available. Prefer passing lotteried_student_ids explicitly when one
        is on hand -- this queries current state, not state as of
        submission."""

        students = program.students()
        if "twophase_star_students" in students:
            stars = set(students['twophase_star_students'].values_list('id', flat=True))
            prioritys = set(students['twophase_priority_students'].values_list('id', flat=True))
            return sorted(stars | prioritys)
        elif "lotteried_students" in students:
            lotteried = students["lotteried_students"]
            if hasattr(lotteried, "values_list"):
                return list(lotteried.values_list('id', flat=True))
            return [u.id if hasattr(u, 'id') else u for u in lotteried]
        else:
            raise LotteryException('Cannot retrieve lottery preferences for program, please ensure that it has the lottery module.')

    @classmethod
    def _update_mailman_lists_from_pairs(cls, program, enrolled_pairs, lotteried_student_ids):
        if not (hasattr(settings, "USE_MAILMAN") and settings.USE_MAILMAN):
            return

        program_list = "%s_%s-students" % (program.program_type, program.program_instance)
        cls.clear_mailman_list(program_list)
        add_list_members(program_list, ESPUser.objects.filter(id__in=lotteried_student_ids).distinct())

        by_section = {}
        for student_id, section_id in enrolled_pairs:
            by_section.setdefault(section_id, []).append(student_id)
        for section_id, section_student_ids in by_section.items():
            section = ClassSection.objects.get(id=section_id)
            list_names = ["%s-%s" % (section.emailcode(), "students"), "%s-%s" % (section.parent_class.emailcode(), "students")]
            students = ESPUser.objects.filter(id__in=section_student_ids).distinct()
            for list_name in list_names:
                cls.clear_mailman_list(list_name)
                add_list_members(list_name, students)
