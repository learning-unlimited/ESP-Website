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
import Queue
import random

from datetime import date, datetime
import re
import os
import sys
import time

from esp.cal.models import Event
from esp.users.models import ESPUser
from esp.program.models import StudentRegistration, RegistrationType, RegistrationProfile, Program, ClassSection
from esp.dbmail.models import send_mail
from esp.utils.query_utils import nest_Q

from django.conf import settings
from django.db.models.query import QuerySet
from django.db.models import Q

class ClassChangeController(object):

    default_options = {
        'check_grade': False,
        'stats_display': False,
        'use_closed_classes': True
    }

    WAIT_REGEX_PATTERN = r"^Waitlist/(\d+)$"
    WAIT_REGEX = re.compile(WAIT_REGEX_PATTERN)

    def get_student_schedule(self, student_ind, for_real = False):
        """ generate student schedules """
        show_rooms = not (self.student_not_checked_in[student_ind] and for_real)
        schedule = "<table border='1'>\n<tr>\n<th>Time%s</th>\n<th>Class and Teacher</th>\n<th>Code</th>\n</tr>\n" % (" and Room" if show_rooms else "")
        sections = list(self.students[student_ind].getSections(self.program, ["Enrolled"]).distinct())
        sections.sort(key = lambda section: section.meeting_times.order_by('start')[0].start)
        for cls in sections:
            schedule += "<tr>\n<td>"+", ".join(cls.friendly_times())+("<br />"+", ".join(cls.prettyrooms()) if show_rooms else "")+"</td>\n<td>"+cls.title()+"<br />"+", ".join(cls.parent_class.getTeacherNames())+"</td>\n<td>"+cls.emailcode()+"</td>\n</tr>\n"
        schedule += "</table>\n"
        return schedule.encode('ascii','ignore')

    def get_changed_student_email_text(self, student_ind, for_real = False):
        student = self.students[student_ind]
        text = "<html>\nHello "+student.first_name+",<br /><br />\n\n"
        text += "We've processed your class change request, and have updated your schedule. Your new schedule is as follows: <br /><br />\n\n"
        text += "%s\n\n<br /><br />\n\n" % self.get_student_schedule(student_ind, for_real)
        if self.student_not_checked_in[student_ind]:
            text += "On your first day, you must check in at room 1-136, turn in your completed liability form, and pay the program fee (unless you are a financial aid recipient or have paid online). We will give you the room numbers of your classes at check-in.<br /><br />\n\n"
        text += "We hope you enjoy your new schedule. See you soon!<br /><br />"
        text += "The " + self.program.niceName() + " Directors\n"
        text += "</html>"
        text = text.encode('ascii','ignore')
        return text

    def get_unchanged_student_email_text(self, student_ind, for_real = False):
        student = self.students[student_ind]
        text = "<html>\nHello "+student.first_name+",<br /><br />\n\n"
        text += "We've processed your class change request, and unfortunately are unable to update your schedule. "
        if self.enroll_final[student_ind,:,:].any():
            text += "Your schedule is still as follows: <br /><br />\n\n"
            text += "%s\n\n<br /><br />\n\n" % self.get_student_schedule(student_ind, for_real)
            text += "See you soon!<br /><br />"
        else:
            text += "We're sorry that we couldn't accommodate your class preferences this time, and we hope to see you at a future " + self.program.niceName() + " program.<br /<br />\n\n"
        text += "The " + self.program.niceName() + " Directors\n"
        text += "</html>"
        text = text.encode('ascii','ignore')
        return text

    def _init_Q_objects(self):
        self.Q_SR_STUDENTS = Q(studentregistration__user__in=self.students) & self.Q_SR_PROG
        self.Q_SR_WAIT = [Q(studentregistration__relationship__name=("Priority/%s" % str(i))) & self.Q_SR_STUDENTS for i in range(self.priority_limit+1)]
        self.Q_SR_WAIT[0] = Q(studentregistration__relationship__name__regex=ClassChangeController.WAIT_REGEX_PATTERN) & self.Q_SR_STUDENTS
        self.Q_SR_EN = Q(studentregistration__relationship__name="Enrolled") & self.Q_SR_STUDENTS

        self.Q_STUDENTS = Q(user__in=self.students) & self.Q_PROG
        self.Q_WAIT = [Q(relationship__name=("Priority/%s" % str(i))) & self.Q_STUDENTS for i in range(self.priority_limit+1)]
        self.Q_WAIT[0] = Q(relationship__name__regex=ClassChangeController.WAIT_REGEX_PATTERN) & self.Q_STUDENTS
        self.Q_EN = Q(relationship__name="Enrolled") & self.Q_STUDENTS

    def __init__(self, program, **kwargs):
        """ Set constant parameters for class changes. """

        assert isinstance(program,(Program,int))
        self.program = program
        if isinstance(program,int):
            self.program = Program.objects.get(id=program)
        print self.program
        iscorrect = raw_input("Is this the correct program (y/[n])? ")
        assert (iscorrect.lower() == 'y' or iscorrect.lower() == 'yes')
        self.now = datetime.now()
        self.options = ClassChangeController.default_options.copy()
        self.options.update(kwargs)
        self.students_not_checked_in = []
        self.deadline = self.now
        if 'deadline' in self.options.keys():
            self.deadline = self.options['deadline']

        self.Q_SR_NOW = nest_Q(StudentRegistration.is_valid_qobject(self.now), 'studentregistration')
        self.Q_SR_PROG = Q(studentregistration__section__parent_class__parent_program=self.program, studentregistration__section__meeting_times__isnull=False) & self.Q_SR_NOW
        self.Q_SR_REQ = Q(studentregistration__relationship__name="Request") & self.Q_SR_PROG
        self.Q_NOW = StudentRegistration.is_valid_qobject(self.now)
        self.Q_PROG = Q(section__parent_class__parent_program=self.program, section__meeting_times__isnull=False) & self.Q_NOW
        self.Q_REQ = Q(relationship__name="Request") & self.Q_PROG

        self.students = ESPUser.objects.filter(self.Q_SR_REQ).order_by('id').distinct()
        if 'students_not_checked_in' in self.options.keys() and isinstance(self.options['students_not_checked_in'],QuerySet):
            self.students_not_checked_in = list(self.options['students_not_checked_in'].values_list('id',flat=True).distinct())
        else:
            self.students_not_checked_in = list(self.students.exclude(id__in=self.program.students()['attended']).values_list('id',flat=True).distinct())

        self.priority_limit = self.program.priorityLimit()
        self._init_Q_objects()
        self.sections = self.program.sections().filter(status__gt=0, parent_class__status__gt=0, meeting_times__isnull=False).order_by('id').select_related('parent_class','parent_class__parent_program').distinct()
        if not self.options['use_closed_classes']:
            self.sections = self.sections.filter(registration_status=0).distinct()
        self.timeslots = self.program.getTimeSlots().order_by('id').distinct()
        self.num_timeslots = len(self.timeslots)
        self.num_students = len(self.students)
        self.num_sections = len(self.sections)






        numpy.random.seed(self.now.microsecond)

        self.initialize()

        if self.options['stats_display']:
            logger.info('Initialized lottery assignment for %d students, %d sections, %d timeslots', self.num_students, self.num_sections, self.num_timeslots)

    def print_stats(self, popular_count=10,
            print_section_notation=False, list_no_class_students=False):
        """Print basic stats about the program and class changes.

        Print some basic stats about the program and this class changes
        controller that you might want to verify before running anything.
        Partly cribbed from the stub wiki page that tells people how to run this
        module. Includes a list of the <popular_count> most requested classes
        and their capacities."""


        print "Class Changes Stats"
        print "==================="
        print
        print "Student counts"
        print "--------------"
        print "{:5d} not checked in".format(len(self.students_not_checked_in))
        print "{:5d} attended".format(len(self.program.students()['attended']))
        print "{:5d} with requests".format(len(self.students))
        print "{:5d} attended with requests".format(len(
                set(self.students.values_list('id', flat=True)) &
                set(self.program.students()['attended'].values_list('id', flat=True))))

        print
        print "Request counts"
        print "--------------"
        print "{:5d} requests".format(numpy.count_nonzero(self.request))
        print "{:5d} student-timeslots with requests".format(numpy.count_nonzero(self.request.any(axis=1)))
        print
        print "Student histograms"
        print "(only students with >= 1 request)"
        print "---------------------------------"
        req_freqs = numpy.bincount(self.request.sum(axis=(1,2)))
        for i in range(req_freqs.size):
            if req_freqs[i]:
                print "{:5d} students with {:3d} request(s)".format(req_freqs[i], i)

        print
        ts_freqs = numpy.bincount(self.request.any(axis=1).sum(axis=1))
        for i in range(ts_freqs.size):
            if ts_freqs[i]:
                print "{:5d} students with {:3d} timeslot(s) with requests".format(ts_freqs[i], i)
        print
        oe_freqs = numpy.bincount(self.enroll_orig.any(axis=1).sum(axis=1))
        for i in range(ts_freqs.size):
            if oe_freqs[i]:
                print "{:5d} students originally enrolled in {:3d} section(s)".format(oe_freqs[i], i)

        # Sum requests, enrollments, etc. along the student and timeslot axis
        # to get a count for each section
        request_freq = numpy.sum(self.request, axis=(0, 2))

        enroll_orig_counts = numpy.sum(self.enroll_orig, axis=(0, 2))
        enroll_final_counts = numpy.sum(self.enroll_final, axis=(0, 2))
        dropped_counts = numpy.sum(self.enroll_orig & ~self.enroll_final, axis=(0, 2))
        added_counts = numpy.sum(~self.enroll_orig & self.enroll_final, axis=(0, 2))


        print
        print "Tentatively changed enrollments"
        print "(not useful if you haven't run compute_assignments)"
        print "---------------------------------------------------"
        print "{:5d} unchanged".format(numpy.sum(self.enroll_orig & self.enroll_final))
        print "{:5d} dropped".format(numpy.sum(dropped_counts))
        print "{:5d} added".format(numpy.sum(added_counts))
        print
        print "Most popularly requested sections"
        print "---------------------------------"
        if print_section_notation:
            print
            print "  Notation: # = N (C -> O / T) [E - D + A = F]"
            print "    N = number of requests"
            print "    C = original remaining capacity"
            print "    O = original optimistic capacity if all requesters switch out"
            print "    T = total capacity"
            print "    E = requesters enrolled originally"
            print "    D = requesters (tentatively) dropped"
            print "    A = requesters (tentatively) added"
            print "    F = requesters enrolled in (tentative) final assignment"
            print
            print "---------------------------------"
        # argsort returns the indices that would sort the array of frequencies;
        # then we iterate over it backwards to get indices sorted by decreasing
        # frequency
        for section_index in numpy.argsort(request_freq)[::-1][:popular_count]:
            section = self.sections[section_index]
            print "# = {:5d} ({:3d} ->{:3d} /{:3d}) [{:3d} -{:3d} +{:3d} =>{:3d}]: {}".format(
                    request_freq[section_index],
                    section.capacity - section.num_students(),
                    self.section_capacities_orig[section_index],
                    section.capacity,
                    enroll_orig_counts[section_index],
                    dropped_counts[section_index],
                    added_counts[section_index],
                    enroll_final_counts[section_index],
                    section)

        print
        print "Students by number of changes"
        print "-----------------------------"
        changed_classes_freq = numpy.bincount(
                (self.enroll_final & ~self.enroll_orig).sum(axis=(1,2)))
        for i in range(changed_classes_freq.size):
            if changed_classes_freq[i]:
                print "{:5d} students with {:3d} added sections".format(changed_classes_freq[i], i)

        print
        print "Students originally with no classes"
        print "-----------------------------------"
        orig_no_class_student_indices = numpy.nonzero(~self.enroll_orig.any(axis=(1, 2)))
        final_classes_freq = numpy.bincount(
                self.enroll_final.sum(axis=(1,2))[orig_no_class_student_indices])
        for i in range(final_classes_freq.size):
            if final_classes_freq[i]:
                print "{:5d} students with {:3d} classes".format(final_classes_freq[i], i)

        print
        print "Students who still have no classes"
        print "----------------------------------"
        final_no_class_student_indices, = numpy.nonzero(~self.enroll_final.any(axis=(1, 2)))
        no_class_request_freq = numpy.bincount(
                self.request.sum(axis=(1,2))[final_no_class_student_indices])
        for i in range(no_class_request_freq.size):
            if no_class_request_freq[i]:
                print "{:5d} students made {:3d} requests".format(no_class_request_freq[i], i)

        if list_no_class_students:
            for student_index in final_no_class_student_indices:
                print self.students[student_index], "requested:"
                for section_index in numpy.nonzero(self.request[student_index,:,:].any(axis=1))[0]:
                    section = self.sections[section_index]
                    print "# = {:5d} ({:3d} ->{:3d} /{:3d}): {}".format(
                            request_freq[section_index],
                            section.capacity - section.num_students(),
                            self.section_capacities_orig[section_index],
                            section.capacity,
                            section)
                print

    def sanity_check(self):
        """Print a report checking that students didn't lose classes.

        For each student and each slot they originally had a class,
        sanity-check that they either stayed in it or got into a class they
        preferred.

        In other words, find all student-timeslots where the student had a
        section but no longer does, or now has a section they didn't request;
        these are usually bad. They might not be, if the student dropped a
        class spanning multiple timeslots to switch into a class that partially
        overlaps. Still, hopefully multiple-timeslot classes are rare enough
        that this is useful."""

        print "Sanity check"
        print "(this will look bad if you haven't computed assignments)"

        bad_drops = self.enroll_orig.any(axis=1) & ~self.enroll_final.any(axis=1)
        num_bad_drops = numpy.count_nonzero(bad_drops)
        print
        print "Bad student-timeslot drops:", num_bad_drops
        print "---------------------------------"
        print "(May not be bad if students drop a class spanning multiple"
        print "timeslots to switch into a class that partially overlaps)"
        for student_index, timeslot_index in numpy.transpose(
                numpy.nonzero(bad_drops)):
            orig_section_indices, = numpy.nonzero(self.enroll_orig[student_index, :, timeslot_index])
            # there should really be only one such index??
            if orig_section_indices.size == 1:
                orig_section = self.sections[orig_section_indices[0]]
            else:
                orig_section = "(????? {} sections found)".format(orig_section_indices.size)

            print "{:>20} had {} @ {}".format(
                    self.students[student_index],
                    orig_section,
                    self.timeslots[timeslot_index])

        unrequested_changes = self.enroll_final & ~self.enroll_orig & ~self.request
        num_unrequested_changes = numpy.count_nonzero(unrequested_changes)
        print
        print "Unrequested changes:", num_unrequested_changes
        print "-------------------------"
        for student_index, section_index, timeslot_index in numpy.transpose(
                numpy.nonzero(unrequested_changes)):
            print "{:>20} got {} @ {}".format(
                    self.students[student_index],
                    self.sections[section_index],
                    self.timeslots[timeslot_index])

        print
        if num_bad_drops or num_unrequested_changes:
            print "^^^", num_bad_drops + num_unrequested_changes, "possible issues found ^^^"
        else:
            print "All good!"

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

        self.changed = numpy.zeros((self.num_students,), dtype=numpy.bool)
        self.section_capacities = numpy.copy(self.section_capacities_orig)
        self.section_scores = numpy.copy(self.section_scores_orig)
        self.enroll_final = numpy.copy(self.enroll_final_orig)

    def initialize(self):
        """ Gather all of the information needed to run the lottery assignment.
            This includes:
            -   Students' interest (priority and interested bits)
            -   Class schedules and capacities
            -   Timeslots (incl. lunch periods for each day)
        """

        self.enroll_orig = numpy.zeros((self.num_students, self.num_sections, self.num_timeslots), dtype=numpy.bool)
        self.enroll_final = numpy.zeros((self.num_students, self.num_sections, self.num_timeslots), dtype=numpy.bool)
        self.request = numpy.zeros((self.num_students, self.num_sections, self.num_timeslots), dtype=numpy.bool)
        self.waitlist = [numpy.zeros((self.num_students, self.num_sections, self.num_timeslots), dtype=numpy.bool) for i in range(self.priority_limit+1)]
        self.section_schedules = numpy.zeros((self.num_sections, self.num_timeslots), dtype=numpy.bool)
        # section_capacities tracks *remaining* capacity.
        self.section_capacities = numpy.zeros((self.num_sections,), dtype=numpy.int32)
        # A section's score is number of students requesting minus capacity.
        # It's positive if we can't let everybody who wants it take it. Higher
        # scores mean a class is more in demand.
        self.section_scores = numpy.zeros((self.num_sections,), dtype=numpy.int32)
        self.same_subject = numpy.zeros((self.num_sections, self.num_sections), dtype=numpy.bool)
        self.section_conflict = numpy.zeros((self.num_sections, self.num_sections), dtype=numpy.bool) # is this a section that takes place in the same timeblock

        #   Get student, section, timeslot IDs and prepare lookup table
        (self.student_ids, self.student_indices) = self.get_ids_and_indices(self.students)
        (self.section_ids, self.section_indices) = self.get_ids_and_indices(self.sections)
        (self.timeslot_ids, self.timeslot_indices) = self.get_ids_and_indices(self.timeslots)
        self.parent_classes = numpy.array(self.sections.values_list('parent_class__id', flat=True))

        self.student_not_checked_in = numpy.zeros((self.num_students,), dtype=numpy.bool)
        self.student_not_checked_in[self.student_indices[self.students_not_checked_in]] = True

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

        for i in range(len(lunch_by_day)):
            if len(lunch_by_day[i]) > ts_count:
                ts_count = len(lunch_by_day[i])
        self.lunch_timeslots = numpy.zeros((len(lunch_by_day), ts_count), dtype=numpy.int32)
        for i in range(len(lunch_by_day)):
            self.lunch_timeslots[i, :len(lunch_by_day[i])] = numpy.array(lunch_by_day[i])

        #   Populate old enrollment matrix
        enroll_regs = StudentRegistration.objects.filter(self.Q_EN).values_list('user__id', 'section__id', 'section__meeting_times__id').distinct()
        era = numpy.array(enroll_regs, dtype=numpy.uint32)
        try:
            self.enroll_orig[self.student_indices[era[:, 0]], self.section_indices[era[:, 1]], self.timeslot_indices[era[:, 2]]] = True
        except IndexError:
            pass

        self.student_not_checked_in[numpy.transpose(numpy.nonzero(~(self.enroll_orig.any(axis=(1,2)))))] = True

        #   Populate request matrix
        request_regs = StudentRegistration.objects.filter(self.Q_REQ).values_list('user__id', 'section__id', 'section__meeting_times__id').distinct()
        rra = numpy.array(request_regs, dtype=numpy.uint32)
        try:
            self.request[self.student_indices[rra[:, 0]], self.section_indices[rra[:, 1]], self.timeslot_indices[rra[:, 2]]] = True
        except IndexError:
            pass

        #   Populate waitlist matrix
        waitlist_regs = [StudentRegistration.objects.filter(self.Q_WAIT[i]).values_list('user__id', 'section__id', 'section__meeting_times__id').distinct() for i in range(self.priority_limit+1)]
        wra = [numpy.array(waitlist_regs[i], dtype=numpy.uint32) for i in range(self.priority_limit+1)]
        self.waitlist[0][:,:,:] = True
        for i in range(1, self.priority_limit+1):
            try:
                self.waitlist[i][self.student_indices[wra[i][:, 0]], self.section_indices[wra[i][:, 1]], self.timeslot_indices[wra[i][:, 2]]] = True
                self.waitlist[0][self.student_indices[wra[i][:, 0]], self.section_indices[wra[i][:, 1]], self.timeslot_indices[wra[i][:, 2]]] = False
            except IndexError:
                pass

        #   Populate section schedule
        section_times = numpy.array(self.sections.values_list('id', 'meeting_times__id'))
        self.section_schedules[self.section_indices[section_times[:, 0]], self.timeslot_indices[section_times[:, 1]]] = True

        #   Populate section overlap matrix
        for i in range(self.num_sections):
            group_ids = numpy.nonzero(self.parent_classes == self.parent_classes[i])[0]
            self.same_subject[numpy.meshgrid(group_ids, group_ids)] = True

            sec_times = numpy.transpose(numpy.nonzero(self.section_schedules[i, :]))
            for [ts_ind,] in sec_times:
                self.section_conflict[numpy.transpose(numpy.nonzero(self.section_schedules[:, ts_ind])), i] = True
                self.section_conflict[i, numpy.transpose(numpy.nonzero(self.section_schedules[:, ts_ind]))] = True
            self.section_conflict[i, i] = False

        #   Populate section grade limits
        self.section_grade_min = numpy.array(self.sections.values_list('parent_class__grade_min', flat=True), dtype=numpy.uint32)
        self.section_grade_max = numpy.array(self.sections.values_list('parent_class__grade_max', flat=True), dtype=numpy.uint32)

        #   Populate student grades; grade will be assumed to be 0 if not entered on profile
        self.student_grades = numpy.zeros((self.num_students,))
        gradyear_pairs = numpy.array(RegistrationProfile.objects.filter(user__id__in=list(self.student_ids), most_recent_profile=True, student_info__graduation_year__isnull=False).values_list('user__id', 'student_info__graduation_year'), dtype=numpy.uint32)
        self.student_grades[self.student_indices[gradyear_pairs[:, 0]]] = 12 + ESPUser.program_schoolyear(self.program) - gradyear_pairs[:, 1]

        #   Find section capacities (TODO: convert to single query)
        for sec in self.sections:
            sec_ind = self.section_indices[sec.id]
            self.section_capacities[sec_ind] = sec.capacity - sec.num_students()
            sec_enroll_orig = self.enroll_orig[:, sec_ind, self.section_schedules[sec_ind,:]].any(axis=1)
            any_overlapping_requests = self.request[:,:,self.section_schedules[sec_ind,:]].any(axis=(1,2))
            # Optimistically add number enrolled but want to switch out to capacity
            self.section_capacities[sec_ind] += numpy.count_nonzero(sec_enroll_orig * any_overlapping_requests)
            # Commit to enrolling students into this section if they were
            # originally in it and they didn't request any overlapping classes
            self.enroll_final[numpy.transpose(numpy.nonzero(sec_enroll_orig * ~(any_overlapping_requests))), sec_ind, self.section_schedules[sec_ind,:]] = True
            self.section_scores[sec_ind] = -self.section_capacities[sec_ind]
            self.section_scores[sec_ind] += numpy.count_nonzero(self.request[:, sec_ind, :].any(axis=1)) # number who want to switch in
        self.section_capacities_orig = numpy.copy(self.section_capacities)
        self.section_scores_orig = numpy.copy(self.section_scores)
        self.enroll_final_orig = numpy.copy(self.enroll_final)
        self.clear_assignments()

    def fill_section(self, si, priority=False):
        """ Assigns students to the section with index si.
            Performs some checks along the way to make sure this didn't break anything. """

        timeslots = numpy.transpose(numpy.nonzero(self.section_schedules[si, :]))

        if self.options['stats_display']: logger.info('-- Filling section %d (index %d, capacity %d, timeslots %s), priority=%s', self.section_ids[si], si, self.section_capacities[si], self.timeslot_ids[timeslots], priority)

        #   Get students who have indicated interest in the section
        possible_students = self.request[:, si, :].any(axis=1)
        if priority:
            possible_students *= self.waitlist[priority][:, si, :].any(axis=1)
        else:
            possible_students *= self.waitlist[0][:, si, :].any(axis=1)

        #   Check that there is at least one timeslot associated with this section
        if timeslots.shape[0] == 0:
            if self.options['stats_display']: logger.info('   Section was not assigned to any timeslots, aborting')
            return False

        #   Check that this section does not cover all lunch timeslots on any given day
        lunch_overlap = self.lunch_schedule * self.section_schedules[si, :]
        for i in range(self.lunch_timeslots.shape[0]):
            if len(self.lunch_timeslots[i]) != 0 and numpy.sum(lunch_overlap[self.timeslot_indices[self.lunch_timeslots[i]]]) >= (self.lunch_timeslots.shape[1]):
                if self.options['stats_display']: logger.info('   Section covered all lunch timeslots %s on day %d, aborting', self.lunch_timeslots[i, :], i)
                return False




        #   Filter students by the section's grade limits
        if self.options['check_grade']:
            possible_students *= (self.student_grades >= self.section_grade_min[si])
            possible_students *= (self.student_grades <= self.section_grade_max[si])

        #   Filter students by who has all of the section's timeslots available
        for [ts_ind,] in timeslots:
            possible_students *= ~(self.enroll_final[:, :, ts_ind].any(axis=1))

        #   Filter students by who is not already registered for a different section of the class
        for sec_index in numpy.nonzero(self.same_subject[:, si])[0]:
            possible_students *= ~(self.enroll_final[:, sec_index, :].any(axis=1))

        #   Filter students by lunch constraint - if class overlaps with lunch period, student must have 1 additional free spot
        #   NOTE: Currently only works with 2 lunch periods per day
        for [ts_ind,] in timeslots:
            if numpy.sum(self.lunch_timeslots == self.timeslot_ids[ts_ind]) > 0:
                lunch_day = numpy.nonzero(self.lunch_timeslots == self.timeslot_ids[ts_ind])[0][0]
                for j in range(self.lunch_timeslots.shape[1]):
                    timeslot_index = self.timeslot_indices[self.lunch_timeslots[lunch_day, j]]
                    if timeslot_index != ts_ind:
                        possible_students *= ~(self.student_schedules[:, timeslot_index])

        candidate_students = numpy.nonzero(possible_students)[0]
        num_spaces = self.section_capacities[si]
        if self.options['stats_display']:
            logger.info('   About to try to add %d candidates to %d spaces', candidate_students.shape[0], num_spaces)
            logger.info('   ' + str(candidate_students.shape))
        # Clamp num_spaces to 0. It can be negative if students enrolled in a
        # class before it was moved to a smaller classroom. Whoops.
        if candidate_students.shape[0] <= max(num_spaces, 0):
            #   If the section has enough space for all students that applied, let them all in.
            selected_students = candidate_students
            section_filled = False
        else:
            #   If the section does not have enough space, select the students up to the maximum
            #   capacity of the section, with the students' weight values serving as the probability
            #   distribution to draw from.
            selected_students = numpy.random.choice(candidate_students, num_spaces, replace=False)
            section_filled = True

        #   Update student section assignments
        #   Check that none of these students are already assigned to this section
        assert(numpy.sum(self.enroll_final[selected_students, si, :]) == 0)
        self.enroll_final[selected_students, si, timeslots] = True
        self.section_capacities[si] -= selected_students.shape[0]

        if self.options['stats_display']: logger.info('   Added %d/%d students (section filled: %s)', selected_students.shape[0], candidate_students.shape[0], section_filled)

        return section_filled

    def push_back_students(self):
        more_pushing = True
        students_to_kick = {}
        while more_pushing:
            more_pushing = False
            # Sort sections by decreasing capacity
            self.sorted_section_indices.sort(key = lambda sec_ind: -self.section_capacities[sec_ind])
            for sec_ind in self.sorted_section_indices:
                # 1-dimensional matrix of whether students were originally
                # enrolled in this class section
                any_enroll_orig = self.enroll_orig[:, sec_ind, self.section_schedules[sec_ind,:]].any(axis=1)
                # 1-dimensional matrix of whether students are free during the
                # times of this class section in the enrollment we've computed
                # so far
                no_enroll_final = ~(self.enroll_final[:,:,self.section_schedules[sec_ind,:]].any(axis=(1,2)))
                # Find students that were originally enrolled in this class and
                # did not get any classes overlapping it in the enrollment
                # we've computed so far
                students_to_push = numpy.transpose(numpy.nonzero(any_enroll_orig * no_enroll_final))
                more_pushing |= bool(len(students_to_push))
                for student_ind in students_to_push:
                    # Enroll them back into this class, since we guarantee that
                    # if you didn't get anything better, you get your old
                    # classes.
                    self.enroll_final[student_ind, sec_ind, self.section_schedules[sec_ind,:]] = True
                    if self.section_capacities[sec_ind] > 0:
                        self.section_capacities[sec_ind] -= 1
                    else:
                        # If the class is out of capacity, we have to kick
                        # students who got it in the lottery.

                        # The first time we ever encounter this section, build
                        # a priority queue of students to kick.
                        if not sec_ind in students_to_kick.keys():
                            # Indices of students that are enrolled in this
                            # class by requesting it, in the enrollment we've
                            # computed so far.
                            students_to_kick[sec_ind] = numpy.transpose(numpy.nonzero((self.enroll_final*self.request)[:, sec_ind, self.section_schedules[sec_ind,:]].any(axis=1)))
                            pq = Queue.PriorityQueue()
                            random.shuffle(students_to_kick[sec_ind])
                            for [student] in students_to_kick[sec_ind]:
                                # For each student, get class sections they
                                # were previously enrolled in at any timeslot
                                # overlapping the section we're kicking them
                                # from.
                                old_sections = numpy.transpose(numpy.nonzero(self.enroll_orig[student, :, self.section_schedules[sec_ind,:]].any(axis=1)))
                                # Put the student in the priority queue,
                                # prioritizing noisily based on how in-demand
                                # their old section was. Prefer to kick
                                # students whose old sections have empty spaces
                                # or are less in demand.
                                if not len(old_sections):
                                    pq.put((0, random.random(), student), False)
                                for [old_section] in old_sections:
                                    pq.put((self.section_scores[old_section], random.random(), student), False)
                            students_to_kick[sec_ind] = pq

                        # Try to kick a student.
                        try:
                            self.enroll_final[students_to_kick[sec_ind].get(False)[2], sec_ind, self.section_schedules[sec_ind,:]] = False
                        except Queue.Empty:
                            pass

    def compute_assignments(self):
        """ Figure out what students should be assigned to what sections.
            Doesn't actually store results in the database.
            Can be run any number of times. """

        self.clear_assignments()

        #   Assign priority students to all sections, ordered by section_score
        self.sorted_section_indices = range(self.num_sections)
        self.sorted_section_indices.sort(key = lambda sec_ind: self.section_scores[sec_ind])
        for i in range(1,self.priority_limit+1) + [False,]:
            if self.options['stats_display']:
                logger.info('\n== Assigning priority%s students', str(i) if self.priority_limit > 1 else '')
            for section_index in self.sorted_section_indices:
                self.fill_section(section_index, priority=i)

        self.push_back_students()

    def save_assignments(self):
        """ Store lottery assignments in the database once they have been computed.
            This is a fairly time consuming step compared to computing the assignments. """

        assignments = numpy.transpose(numpy.nonzero((self.enroll_final * ~(self.enroll_orig)).any(axis=2)))
        removals = numpy.transpose(numpy.nonzero((self.enroll_orig * ~(self.enroll_final)).any(axis=2)))
        relationship, created = RegistrationType.objects.get_or_create(name='Enrolled')

        for (student_ind,section_ind) in removals:
            self.sections[section_ind].unpreregister_student(self.students[student_ind], prereg_verb = "Enrolled")
            self.changed[student_ind] = True
        for (student_ind,section_ind) in assignments:
            self.sections[section_ind].preregister_student(self.students[student_ind], overridefull=False, prereg_verb = "Enrolled", fast_force_create=False)
            self.changed[student_ind] = True

    def unsave_assignments(self):
        StudentRegistration.objects.filter(end_date__gte=self.now, end_date__lte=datetime(9000,1,1)).update(end_date=None)
        StudentRegistration.objects.filter(start_date__gte=self.now).delete()

    def send_student_email(self, student_ind, changed = True, for_real = False, f = None):
        student = self.students[student_ind]
        recipient_list = [student.email, self.from_email]
        if changed:
            text_fn = self.get_changed_student_email_text
        else:
            text_fn = self.get_unchanged_student_email_text
        sent_to = "\n\nSent to " + student.username + ", " + student.name() + " <" + student.email + ">\n\n------------------------\n\n"
        if self.options['stats_display']:
            logger.info(text_fn(student_ind,for_real=False) + sent_to)
            sys.stdout.flush()
        if f:
            f.write((text_fn(student_ind,for_real=False) + sent_to).replace(u'\u2019', "'").replace(u'\u201c','"').replace(u'\u201d','"').encode('ascii','ignore'))
        if for_real:
            send_mail(self.subject, text_fn(student_ind,for_real=True), self.from_email, recipient_list, bcc=self.bcc, extra_headers=self.extra_headers)
            time.sleep(self.timeout)

    def send_emails(self, for_real = False):
        if self.options['stats_display']:
            logger.info("Sending emails....")
            sys.stdout.flush()
        if hasattr(settings, 'EMAILTIMEOUT') and \
               settings.EMAILTIMEOUT is not None:
            self.timeout = settings.EMAILTIMEOUT
        else:
            self.timeout = 2
        f = open(os.getenv("HOME")+'/'+"classchanges.txt", 'w')
        self.subject = "[" + self.program.niceName() + "] Class Change"
        self.from_email = "%s <%s>" % (self.program.niceName(), self.program.director_email)
        self.bcc = [self.from_email]
        self.extra_headers = {}
        self.extra_headers['Reply-To'] = self.from_email
        for [student_ind] in numpy.transpose(numpy.nonzero(self.changed)):
            self.send_student_email(student_ind, changed = True, for_real = for_real, f = f)
        for [student_ind] in numpy.transpose(numpy.nonzero(~(self.changed))):
            self.send_student_email(student_ind, changed = False, for_real = for_real, f = f)
