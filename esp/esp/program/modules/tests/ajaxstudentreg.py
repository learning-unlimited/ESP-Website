__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
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

from esp.program.models import (BooleanExpression, BooleanToken, ClassSubject, Program,
                                ScheduleConstraint, ScheduleTestOccupied, ScheduleTestSectionList,
                                unmet_requirements)
from esp.program.models.class_ import ClassSection
from esp.program.tests import ProgramFrameworkTest

import random
import json
import logging

logger = logging.getLogger(__name__)

class AjaxStudentRegTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        # Set up the program -- we want to be sure of these parameters
        kwargs.update( {
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 6, 'classes_per_teacher': 1, 'sections_per_class': 2,
            'num_rooms': 6,
            } )
        ProgramFrameworkTest.setUp(self, *args, **kwargs)

        self.add_student_profiles()
        self.schedule_randomly()

        # Get and remember the instance of StudentClassRegModule
        pm = ProgramModule.objects.get(handler='StudentClassRegModule')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.moduleobj.user = self.students[0]

    def expect_empty_schedule(self, response):
        resp_data = json.loads(str(response.content, encoding='UTF-8'))
        self.assertTrue('student_schedule_html' in resp_data)
        search_str = 'Your schedule for %s is empty.  Please add classes below!' % self.program.niceName()
        self.assertTrue(search_str in resp_data['student_schedule_html'], f'Could not find empty fragment "{search_str}" in response "{resp_data["student_schedule_html"]}"')

    def expect_sections_in_schedule(self, response, sections=[]):
        resp_data = json.loads(str(response.content, encoding='UTF-8'))
        self.assertTrue('student_schedule_html' in resp_data)
        for sec in sections:
            self.assertTrue(sec.title() in resp_data['student_schedule_html'])
            self.assertTrue(sec.friendly_times()[0] in resp_data['student_schedule_html'])

    def expect_ajaxerror(self, request_url, post_data, error_str):
        # We expect the server to return a JSON response with status 200 and an error message.

        response = self.client.post(request_url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # Parse the JSON response
        resp_data = json.loads(str(response.content, encoding='UTF-8'))

        # Check that the request was successful but contained an error message
        self.assertTrue(int(resp_data['status']) == 200)
        error_msg = resp_data['error']

        self.assertTrue(error_msg == error_str, f'Unexpected Ajax error: "{error_msg}", expected "{error_str}"')

    def test_ajax_schedule(self):
        program = self.program

        #   Pick a student and log in
        student = random.choice(self.students)
        self.assertTrue( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )

        #   Sign up for a class directly
        sec = random.choice(program.sections())
        sec.preregister_student(student)

        #   Get the schedule
        response = self.client.get('/learn/%s/ajax_schedule' % program.getUrlBase(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_sections_in_schedule(response, [sec])

        #   Reschedule that class and try again
        sec.clearRooms()
        sec.meeting_times.clear()
        sec = ClassSection.objects.get(id=sec.id)
        vt = sec.viable_times()
        new_timeslot = random.choice(vt)
        sec.assign_start_time(new_timeslot)
        sec = ClassSection.objects.get(id=sec.id)
        response = self.client.get('/learn/%s/ajax_schedule' % program.getUrlBase(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_sections_in_schedule(response, [sec])

        #   Remove the class and ensure that it's gone
        sec.unpreregister_student(student)
        sec = ClassSection.objects.get(id=sec.id)
        response = self.client.get('/learn/%s/ajax_schedule' % program.getUrlBase(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_empty_schedule(response)

    def test_ajax_addclass(self):
        program = self.program

        #   Pick a student, clear schedule and log in
        student = random.choice(self.students)
        self.assertTrue( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )

        #   Get the schedule and check that it's empty
        response = self.client.get('/learn/%s/ajax_schedule' % program.getUrlBase(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_empty_schedule(response)

        #   Add a class that we know we can take; check that schedule comes back with it
        sec1 = random.choice(program.sections())
        response = self.client.post('/learn/%s/ajax_addclass' % program.getUrlBase(), {'class_id': sec1.parent_class.id, 'section_id': sec1.id}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_sections_in_schedule(response, [sec1])

        #   Try adding another class at the same time and check that we get an error
        #   Handle case where no conflicting sections exist
        conflicting_sections = list(ClassSection.objects.filter(parent_class__parent_program=program, meeting_times=sec1.start_time()).exclude(parent_class=sec1.parent_class))

        if not conflicting_sections:
            self.skipTest("Skipping rest of test_ajax_addclass: No conflicting sections found (random seed).")

        sec2 = random.choice(conflicting_sections)
        self.expect_ajaxerror('/learn/%s/ajax_addclass' % program.getUrlBase(), {'class_id': sec2.parent_class.id, 'section_id': sec2.id}, 'This section conflicts with your schedule--check out the other sections!')

        #   Try adding another section of same class and check that we get an error
        #   Handle case where no other sections exist
        other_sections = list(sec1.parent_class.get_sections().exclude(id=sec1.id))

        if not other_sections:
            self.skipTest("Skipping rest of test_ajax_addclass: No other sections of the same class found.")

        sec3 = random.choice(other_sections)
        self.expect_ajaxerror('/learn/%s/ajax_addclass' % program.getUrlBase(), {'class_id': sec3.parent_class.id, 'section_id': sec3.id}, 'You are already signed up for a section of this class!')

        #   Try adding another class that we can actually take and check that it's there
        #   Handle case where no valid sections exist
        valid_sections = list(program.sections().exclude(parent_class=sec1.parent_class).exclude(meeting_times__in=sec1.meeting_times.all()))

        if not valid_sections:
            self.skipTest("Skipping rest of test_ajax_addclass: No valid non-conflicting sections found.")

        sec4 = random.choice(valid_sections)
        response = self.client.post('/learn/%s/ajax_addclass' % program.getUrlBase(), {'class_id': sec4.parent_class.id, 'section_id': sec4.id}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_sections_in_schedule(response, [sec1, sec4])

    def _create_other_program_section(self):
        """Minimal second program + accepted class/section for cross-program 404 checks."""
        other_prog = Program.objects.create(
            url='TestProgram/OtherAddClass',
            name='TestProgram Other AddClass',
            grade_min=7,
            grade_max=12,
            director_email='info@test.learningu.org',
            program_size_max=3000,
        )
        other_prog.program_modules.set(self.program.program_modules.all())
        other_prog.class_categories.set(self.program.class_categories.all())

        category = self.program.class_categories.first()
        other_class = ClassSubject.objects.create(
            title='Other Program Class',
            category=category,
            grade_min=7,
            grade_max=12,
            parent_program=other_prog,
            class_size_max=30,
            class_info='Cross-program section for ajax_addclass auth checks',
        )
        other_class.makeTeacher(self.teachers[0])
        other_class.accept()
        if not other_class.get_sections().exists():
            other_class.add_section(duration=50 / 60.0)
        return other_class.get_sections()[0]

    def test_ajax_addclass_mismatched_ids(self):
        """Mismatched section/class/program IDs must 404; valid addclass must still enroll.

        Covers the ownership checks restored alongside select_for_update():
        section id, parent class id, and parent program.
        """
        program = self.program

        student = random.choice(self.students)
        self.assertTrue( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )

        sec1 = random.choice(program.sections())
        other_class_sections = list(program.sections().exclude(parent_class=sec1.parent_class))
        if not other_class_sections:
            self.skipTest("Skipping test_ajax_addclass_mismatched_ids: no section from a different class found.")
        sec_other = random.choice(other_class_sections)

        #   invalid / nonexistent section_id
        response = self.client.post('/learn/%s/ajax_addclass' % program.getUrlBase(), {'class_id': sec1.parent_class.id, 'section_id': 999999}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 404)

        #   section belonging to a different class in the same program
        response = self.client.post('/learn/%s/ajax_addclass' % program.getUrlBase(), {'class_id': sec_other.parent_class.id, 'section_id': sec1.id}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 404)

        #   section belonging to a different program
        foreign_sec = self._create_other_program_section()
        response = self.client.post(
            '/learn/%s/ajax_addclass' % program.getUrlBase(),
            {'class_id': foreign_sec.parent_class.id, 'section_id': foreign_sec.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 404)

        #   none of the bad requests should have enrolled the student
        response = self.client.get('/learn/%s/ajax_schedule' % program.getUrlBase(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_empty_schedule(response)

        #   valid registration still succeeds after the constrained lookup
        response = self.client.post(
            '/learn/%s/ajax_addclass' % program.getUrlBase(),
            {'class_id': sec1.parent_class.id, 'section_id': sec1.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.expect_sections_in_schedule(response, [sec1])

    def test_ajax_clearslot(self):
        program = self.program

        #   Pick a student, log in, schedule 2 classes
        student = random.choice(self.students)
        self.assertTrue( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )
        sec1 = random.choice(program.sections())
        sec1.preregister_student(student)

        # Ensure we actually found a non-conflicting second class
        valid_second_sections = list(program.sections().exclude(parent_class=sec1.parent_class).exclude(meeting_times__in=sec1.meeting_times.all()))

        if not valid_second_sections:
            self.skipTest("Skipping remainder of test_ajax_clearslot due to bad random seed.")

        sec2 = random.choice(valid_second_sections)
        sec2.preregister_student(student)

        #   Get the schedule and check that both classes are there
        response = self.client.get('/learn/%s/ajax_schedule' % program.getUrlBase(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_sections_in_schedule(response, [sec1, sec2])

        #   Clear 1 timeslot and check that only the desired class remains
        response = self.client.get(f'/learn/{program.getUrlBase()}/ajax_clearslot/{sec1.meeting_times.all()[0].id}', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_sections_in_schedule(response, [sec2])

        #   Clear other timeslot and check that the schedule is empty
        response = self.client.get(f'/learn/{program.getUrlBase()}/ajax_clearslot/{sec2.meeting_times.all()[0].id}', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_empty_schedule(response)


class ScheduleConstraintWarningBlockingTest(ProgramFrameworkTest):
    """Schedule constraints can warn or block changes."""

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 6, 'classes_per_teacher': 1, 'sections_per_class': 2,
            'num_rooms': 6,
            })
        ProgramFrameworkTest.setUp(self, *args, **kwargs)
        self.add_student_profiles()
        self.schedule_randomly()

    def add_constraint(self, requirement_label, enforce=False):
        """Create an unconditional constraint and return (constraint, requirement)."""
        condition = BooleanExpression.objects.create(label='always')
        BooleanToken.objects.create(exp=condition, text='True', seq=0)
        requirement = BooleanExpression.objects.create(label=requirement_label)
        constraint = ScheduleConstraint.objects.create(program=self.program, condition=condition,
                                                       requirement=requirement, on_failure='',
                                                       enforce=enforce)
        return constraint, requirement

    def require_class_during(self, timeslot, enforce=False):
        """Require any class during this timeslot."""
        constraint, requirement = self.add_constraint(
            'have a class during %s' % timeslot.short_description, enforce)
        ScheduleTestOccupied.objects.create(exp=requirement, timeblock=timeslot, seq=0)
        return constraint

    def require_section_during(self, section, timeslot, enforce=False):
        """Require this particular section during this timeslot."""
        constraint, requirement = self.add_constraint(
            'keep %s during %s' % (section.emailcode(), timeslot.short_description), enforce)
        ScheduleTestSectionList.objects.create(exp=requirement, timeblock=timeslot,
                                               section_ids=str(section.id), seq=0)
        return constraint

    def two_sections_sharing(self, timeslot):
        """Two sections of different classes, both scheduled into this timeslot."""
        sections = list(self.program.sections())
        held = sections[0]
        replacement = next((sec for sec in sections
                            if sec.parent_class_id != held.parent_class_id), None)
        self.assertIsNotNone(replacement, 'Program should have sections of more than one class')
        held.meeting_times.set([timeslot])
        replacement.meeting_times.set([timeslot])
        return held, replacement

    def login_student(self):
        student = random.choice(self.students)
        self.assertTrue(self.client.login(username=student.username, password='password'),
                        "Couldn't log in as student %s" % student.username)
        return student

    def test_unmet_requirements_reports_only_failures(self):
        student = random.choice(self.students)
        sec = random.choice(self.program.sections())
        timeslot = sec.meeting_times.all()[0]
        constraint = self.require_class_during(timeslot)

        #   Nothing scheduled yet, so the requirement is unmet.
        self.assertEqual(unmet_requirements(student, self.program), [constraint.requirement.label])

        sec.preregister_student(student)
        self.assertEqual(unmet_requirements(student, self.program), [])

    def test_clearslot_removes_class_and_warns(self):
        student = self.login_student()
        sec = random.choice(self.program.sections())
        sec.preregister_student(student)
        timeslot = sec.meeting_times.all()[0]
        constraint = self.require_class_during(timeslot)

        #   Removing the only class in the timeslot leaves the requirement unmet,
        #   which used to be refused outright.
        response = self.client.get('/learn/%s/ajax_clearslot/%d' % (self.program.getUrlBase(), timeslot.id),
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(student.getSections(self.program).exists(),
                         'Class should have been removed despite the unmet requirement')

        #   ...and the student is told about it on the schedule that comes back.
        schedule_html = json.loads(str(response.content, encoding='UTF-8'))['student_schedule_html']
        self.assertIn(constraint.requirement.label, schedule_html)

    def test_addclass_adds_class_and_warns(self):
        self.login_student()
        sec = random.choice(self.program.sections())
        #   Require a class during a timeslot this section does not cover, so the
        #   requirement is still unmet after the add.
        other_timeslots = [ts for ts in self.program.getTimeSlots()
                           if ts.id not in set(sec.meeting_times.values_list('id', flat=True))]
        self.assertTrue(other_timeslots, 'Program should have more than one timeslot')
        constraint = self.require_class_during(other_timeslots[0])

        response = self.client.post('/learn/%s/ajax_addclass' % self.program.getUrlBase(),
                                    {'class_id': sec.parent_class.id, 'section_id': sec.id},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        schedule_html = json.loads(str(response.content, encoding='UTF-8'))['student_schedule_html']
        self.assertIn(sec.title(), schedule_html)
        self.assertIn(constraint.requirement.label, schedule_html)

    def test_schedule_without_constraints_has_no_warning(self):
        student = self.login_student()
        sec = random.choice(self.program.sections())
        sec.preregister_student(student)

        response = self.client.get('/learn/%s/ajax_schedule' % self.program.getUrlBase(),
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        schedule_html = json.loads(str(response.content, encoding='UTF-8'))['student_schedule_html']
        self.assertNotIn('Please check your schedule', schedule_html)

    def test_enforced_constraint_blocks_removal_that_newly_breaks_it(self):
        student = self.login_student()
        sec = random.choice(self.program.sections())
        sec.preregister_student(student)
        timeslot = sec.meeting_times.all()[0]
        self.require_class_during(timeslot, enforce=True)

        #   ESPError_NoLog currently renders as a 500 error page.
        response = self.client.get('/learn/%s/ajax_clearslot/%d' % (self.program.getUrlBase(), timeslot.id),
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 500)
        self.assertTrue(student.getSections(self.program).filter(id=sec.id).exists(),
                        'Enforced constraint should have prevented the removal')

    def test_enforced_constraint_does_not_trap_a_schedule_already_in_violation(self):
        student = self.login_student()
        sec = random.choice(self.program.sections())
        sec.preregister_student(student)

        #   Require a class in a timeslot the student has nothing in, so the
        #   schedule is in violation before they touch anything.
        empty_timeslots = [ts for ts in self.program.getTimeSlots()
                           if ts.id not in set(sec.meeting_times.values_list('id', flat=True))]
        self.assertTrue(empty_timeslots, 'Program should have more than one timeslot')
        self.require_class_during(empty_timeslots[0], enforce=True)

        response = self.client.get('/learn/%s/ajax_clearslot/%d' % (
            self.program.getUrlBase(), sec.meeting_times.all()[0].id),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(student.getSections(self.program).exists(),
                         'A schedule that already violates a constraint should still be changeable')

    def test_enforced_constraint_blocks_add_that_newly_breaks_it(self):
        student = self.login_student()
        timeslot = self.program.getTimeSlots()[0]
        held, replacement = self.two_sections_sharing(timeslot)
        held.preregister_student(student)
        constraint = self.require_section_during(held, timeslot, enforce=True)

        #   Displacing the required section is what breaks the requirement.
        response = self.client.post('/learn/%s/ajax_addclass' % self.program.getUrlBase(),
                                    {'class_id': replacement.parent_class.id,
                                     'section_id': replacement.id, 'force_replace': 'true'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        resp_data = json.loads(str(response.content, encoding='UTF-8'))
        self.assertIn('error', resp_data, 'Expected the add to be refused, got %r' % resp_data)
        self.assertIn(constraint.requirement.label, resp_data['error'])
        self.assertTrue(student.getSections(self.program).filter(id=held.id).exists(),
                        'The displaced section should not have been removed')
        self.assertFalse(student.getSections(self.program).filter(id=replacement.id).exists())

    def test_enforced_constraint_allows_a_replacement_that_keeps_it_satisfied(self):
        """A swap within the same timeslot is a net no-op for an "any class" requirement."""
        student = self.login_student()
        timeslot = self.program.getTimeSlots()[0]
        held, replacement = self.two_sections_sharing(timeslot)
        held.preregister_student(student)
        self.require_class_during(timeslot, enforce=True)

        response = self.client.post('/learn/%s/ajax_addclass' % self.program.getUrlBase(),
                                    {'class_id': replacement.parent_class.id,
                                     'section_id': replacement.id, 'force_replace': 'true'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        resp_data = json.loads(str(response.content, encoding='UTF-8'))
        self.assertNotIn('error', resp_data, 'Replacement should be allowed, got %r' % resp_data)
        self.assertTrue(student.getSections(self.program).filter(id=replacement.id).exists())
