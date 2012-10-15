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
import Queue
import random

from datetime import date, datetime
import re
import os
import sys
import time

from esp.cal.models import Event
from esp.users.models import ESPUser
from esp.program.models import StudentRegistration, RegistrationType, RegistrationProfile, Program
from esp.dbmail.models import send_mail

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
            text += "On your first day, you must check in (at room 5-233), turn in your completed medical liability form, and pay the program fee (unless you are a financial aid recipient). After you do this, we will give you the room numbers of your classes.<br /><br />\n\n"
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
            text += "We're sorry that we couldn't accomodate your class preferences this time, and we hope to see you at a future ESP program.<br /<br />\n\n"
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
        if 'students_not_checked_in' in self.options.keys() and isinstance(self.options['students_not_checked_in'],QuerySet):
            self.students_not_checked_in = list(self.options['students_not_checked_in'].values_list('id',flat=True).distinct())
        self.Q_SR_NOW = Q(studentregistration__start_date__lt=self.deadline, studentregistration__end_date__gt=self.now)
        self.Q_SR_PROG = Q(studentregistration__section__parent_class__parent_program=self.program) & self.Q_SR_NOW
        self.Q_SR_REQ = Q(studentregistration__relationship__name="Request") & self.Q_SR_PROG
        self.Q_NOW = Q(start_date__lt=self.deadline, end_date__gt=self.now)
        self.Q_PROG = Q(section__parent_class__parent_program=self.program) & self.Q_NOW
        self.Q_REQ = Q(relationship__name="Request") & self.Q_PROG
        self.students = ESPUser.objects.filter(self.Q_SR_REQ).order_by('id').distinct()
        self.priority_limit = self.program.priorityLimit()
        self._init_Q_objects()
        self.sections = self.program.sections().filter(status__gt=0, parent_class__status__gt=0, meeting_times__isnull=False).order_by('id').select_related('parent_class','parent_class__parent_program','meeting_times').distinct()
        if not self.options['use_closed_classes']:
            self.options.filter(registration_status=0).distinct()
        self.timeslots = self.program.getTimeSlots().order_by('id').distinct()
        self.num_timeslots = len(self.timeslots)
        self.num_students = len(self.students)
        self.num_sections = len(self.sections)
        
        
        
        
        
        
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
        self.section_capacities = numpy.zeros((self.num_sections,), dtype=numpy.int32)
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
        for ts in lunch_timeslots:
            d = date(ts.start.year, ts.start.month, ts.start.day)
            lunch_by_day[dates.index(d)].append(ts.id)
            self.lunch_schedule[self.timeslot_indices[ts.id]] = True
        self.lunch_timeslots = numpy.array(lunch_by_day)
        
        #   Populate old enrollment matrix
        enroll_regs = StudentRegistration.objects.filter(self.Q_EN).values_list('user__id', 'section__id', 'section__meeting_times__id').distinct()
        era = numpy.array(enroll_regs, dtype=numpy.uint32)
        try:
            self.enroll_orig[self.student_indices[era[:, 0]], self.section_indices[era[:, 1]], self.timeslot_indices[era[:, 2]]] = True
        except IndexError:
            pass
        
        self.student_not_checked_in[numpy.transpose(numpy.nonzero(True-self.enroll_orig.any(axis=(1,2))))] = True
        
        #   Populate old enrollment matrix
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
        gradyear_pairs = numpy.array(RegistrationProfile.objects.filter(user__id__in=list(self.student_ids), most_recent_profile=True).values_list('user__id', 'student_info__graduation_year'), dtype=numpy.uint32)
        self.student_grades[self.student_indices[gradyear_pairs[:, 0]]] = 12 + ESPUser.current_schoolyear() - gradyear_pairs[:, 1] + self.program.incrementGrade()
        
        #   Find section capacities (TODO: convert to single query)
        for sec in self.sections:
            sec_ind = self.section_indices[sec.id]
            self.section_capacities[sec_ind] = sec.capacity - sec.num_students()
            self.section_capacities[sec_ind] += numpy.count_nonzero((self.enroll_orig[:, sec_ind, self.section_schedules[sec_ind,:]].any(axis=1) * self.request[:,:,self.section_schedules[sec_ind,:]].any(axis=(1,2)))) # number enrolled but want to switch out
            self.enroll_final[numpy.transpose(numpy.nonzero((self.enroll_orig[:, sec_ind, self.section_schedules[sec_ind,:]].any(axis=1) * (True - self.request[:,:,self.section_schedules[sec_ind,:]].any(axis=(1,2)))))), sec_ind, self.section_schedules[sec_ind,:]] = True
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
        
        if self.options['stats_display']: print '-- Filling section %d (index %d, capacity %d, timeslots %s), priority=%s' % (self.section_ids[si], si, self.section_capacities[si], self.timeslot_ids[timeslots], priority)
        
        #   Get students who have indicated interest in the section
        possible_students = self.request[:, si, :].any(axis=1)
        if priority:
            possible_students *= self.waitlist[priority][:, si, :].any(axis=1)
        else:
            possible_students *= self.waitlist[0][:, si, :].any(axis=1)
            
        #   Check that there is at least one timeslot associated with this section
        if timeslots.shape[0] == 0:
            if self.options['stats_display']: print '   Section was not assigned to any timeslots, aborting'
            return False
            
        #   Check that this section does not cover all lunch timeslots on any given day
        lunch_overlap = self.lunch_schedule * self.section_schedules[si, :]
        for i in range(self.lunch_timeslots.shape[0]):
            if self.lunch_timeslots[i].shape[0] != 0 and numpy.sum(lunch_overlap[self.timeslot_indices[self.lunch_timeslots[i, :]]]) >= (self.lunch_timeslots.shape[1]):
                if self.options['stats_display']: print '   Section covered all lunch timeslots %s on day %d, aborting' % (self.lunch_timeslots[i, :], i)
                return False
        

        
        
        #   Filter students by the section's grade limits
        if self.options['check_grade']:
            possible_students *= (self.student_grades >= self.section_grade_min[si])
            possible_students *= (self.student_grades <= self.section_grade_max[si])

        #   Filter students by who has all of the section's timeslots available
        for [ts_ind,] in timeslots:
            possible_students *= (True - self.enroll_final[:, :, ts_ind].any(axis=1))
            
        #   Filter students by who is not already registered for a different section of the class
        for sec_index in numpy.nonzero(self.same_subject[:, si])[0]:
            possible_students *= (True - self.enroll_final[:, sec_index, :].any(axis=1))
            
        #   Filter students by lunch constraint - if class overlaps with lunch period, student must have 1 additional free spot
        #   NOTE: Currently only works with 2 lunch periods per day
        for [ts_ind,] in timeslots:
            if numpy.sum(self.lunch_timeslots == self.timeslot_ids[ts_ind]) > 0:
                lunch_day = numpy.nonzero(self.lunch_timeslots == self.timeslot_ids[ts_ind])[0][0]
                for j in range(self.lunch_timeslots.shape[1]):
                    timeslot_index = self.timeslot_indices[self.lunch_timeslots[lunch_day, j]]
                    if timeslot_index != ts_ind:
                        possible_students *= (True - self.student_schedules[:, timeslot_index])
                        
        candidate_students = numpy.nonzero(possible_students)[0]
        num_spaces = self.section_capacities[si]
        if candidate_students.shape[0] <= num_spaces:
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
        
        if self.options['stats_display']: print '   Added %d/%d students (section filled: %s)' % (selected_students.shape[0], candidate_students.shape[0], section_filled)
        
        return section_filled
        
    def push_back_students(self):
        more_pushing = True
        students_to_kick = {}
        while more_pushing:
            more_pushing = False
            self.sorted_section_indices.sort(key = lambda sec_ind: -self.section_capacities[sec_ind])
            for sec_ind in self.sorted_section_indices:
                students_to_push = numpy.transpose(numpy.nonzero((self.enroll_orig[:, sec_ind, self.section_schedules[sec_ind,:]].any(axis=1) * (True - self.enroll_final[:,:,self.section_schedules[sec_ind,:]].any(axis=(1,2))))))
                more_pushing |= bool(len(students_to_push))
                for student_ind in students_to_push:
                    self.enroll_final[student_ind, sec_ind, self.section_schedules[sec_ind,:]] = True
                    if self.section_capacities[sec_ind] > 0:
                        self.section_capacities[sec_ind] -= 1
                    else:
                        if not sec_ind in students_to_kick.keys():
                            students_to_kick[sec_ind] = numpy.transpose(numpy.nonzero((self.enroll_final*self.request)[:, sec_ind, self.section_schedules[sec_ind,:]].any(axis=1)))
                            pq = Queue.PriorityQueue()
                            random.shuffle(students_to_kick[sec_ind])
                            for [student] in students_to_kick[sec_ind]:
                                old_sections = numpy.transpose(numpy.nonzero(self.enroll_orig[student, :, self.section_schedules[sec_ind,:]].any(axis=1)))
                                if not len(old_sections):
                                    pq.put((0, random.random(), student), False)
                                for [old_section] in old_sections:
                                    pq.put((self.section_scores[old_section], random.random(), student), False)
                            students_to_kick[sec_ind] = pq
                        self.enroll_final[students_to_kick[sec_ind].get(False)[2], sec_ind, self.section_schedules[sec_ind,:]] = False

    def compute_assignments(self):
        """ Figure out what students should be assigned to what sections.
            Doesn't actually store results in the database.
            Can be run any number of times. """
            
        self.clear_assignments()
        
        #   Assign priority students to all sections in random order
        self.sorted_section_indices = range(self.num_sections)
        self.sorted_section_indices.sort(key = lambda sec_ind: self.section_scores[sec_ind])
        for i in range(1,self.priority_limit+1) + [False,]:
            if self.options['stats_display']:
                print '\n== Assigning priority%s students' % (str(i) if self.priority_limit > 1 else '')
            for section_index in self.sorted_section_indices:
                self.fill_section(section_index, priority=i)
        
        self.push_back_students()
    
    def save_assignments(self, debug_display=False):
        """ Store lottery assignments in the database once they have been computed.
            This is a fairly time consuming step compared to computing the assignments. """
        
        assignments = numpy.transpose(numpy.nonzero((self.enroll_final * (True - self.enroll_orig)).any(axis=2)))
        removals = numpy.transpose(numpy.nonzero((self.enroll_orig * (True - self.enroll_final)).any(axis=2)))
        relationship, created = RegistrationType.objects.get_or_create(name='Enrolled')
        
        for (student_ind,section_ind) in removals:
            self.sections[section_ind].unpreregister_student(self.students[student_ind], prereg_verb = "Enrolled")
            self.changed[student_ind] = True
        for (student_ind,section_ind) in assignments:
            self.sections[section_ind].preregister_student(self.students[student_ind], overridefull=False, prereg_verb = "Enrolled", fast_force_create=False)
            self.changed[student_ind] = True
    
    def unsave_assignments(self):
        StudentRegistration.objects.filter(end_date__gte=self.now, end_date__lte=datetime(9000,1,1)).update(end_date=datetime(9999,1,1))
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
            print text_fn(student_ind,for_real=False) + sent_to
            sys.stdout.flush()
        if f:
            f.write((text_fn(student_ind,for_real=False) + sent_to).replace(u'\u2019', "'").replace(u'\u201c','"').replace(u'\u201d','"').encode('ascii','ignore'))
        if for_real:
            send_mail(self.subject, text_fn(student_ind,for_real=True), self.from_email, recipient_list, bcc=self.bcc, extra_headers=self.extra_headers)
            time.sleep(self.timeout)
    
    def send_emails(self, for_real = False):
        if self.options['stats_display']:
            print "Sending emails...."
            sys.stdout.flush()
        if hasattr(settings, 'EMAILTIMEOUT') and \
               settings.EMAILTIMEOUT is not None:
            self.timeout = settings.EMAILTIMEOUT
        else:
            self.timeout = 2
        f = open(os.getenv("HOME")+'/'+"classchanges.txt", 'w')
        self.subject = "[" + self.program.niceName() + "] Class Change"
        self.from_email = "%s <%s>" % (self.program.niceName(), self.program.director_email)
        self.bcc = self.from_email
        self.extra_headers = {}
        self.extra_headers['Reply-To'] = self.from_email
        for [student_ind] in numpy.transpose(numpy.nonzero(self.changed)):
            self.send_student_email(student_ind, changed = True, for_real = for_real, f = f)
        for [student_ind] in numpy.transpose(numpy.nonzero(True-self.changed)):
            self.send_student_email(student_ind, changed = False, for_real = for_real, f = f)
