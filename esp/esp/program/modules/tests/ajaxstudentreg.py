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

from esp.middleware.esperrormiddleware import AjaxErrorMiddleware
from esp.program.models.class_ import ClassSection
from esp.program.tests import ProgramFrameworkTest

from django_selenium.testcases import SeleniumTestCase
import random
import json
import logging
logger = logging.getLogger(__name__)

# TODO(gkanwar): Remove non-selenium tests from this TestCase
class AjaxStudentRegTest(ProgramFrameworkTest, SeleniumTestCase):
    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        # Set up the program -- we want to be sure of these parameters
        kwargs.update( {
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 6, 'classes_per_teacher': 1, 'sections_per_class': 2,
            'num_rooms': 6,
            } )
        ProgramFrameworkTest.setUp(self, *args, **kwargs)
        SeleniumTestCase.setUp(self)

        self.add_student_profiles()
        self.schedule_randomly()

        # Get and remember the instance of StudentClassRegModule
        pm = ProgramModule.objects.get(handler='StudentClassRegModule')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.moduleobj.user = self.students[0]

    def expect_empty_schedule(self, response):
        resp_data = json.loads(response.content)
        self.assertTrue('student_schedule_html' in resp_data)
        search_str = 'Your schedule for %s is empty.  Please add classes below!' % self.program.niceName()
        self.assertTrue(search_str in resp_data['student_schedule_html'], 'Could not find empty fragment "%s" in response "%s"' % (search_str, resp_data['student_schedule_html']))

    def expect_sections_in_schedule(self, response, sections=[]):
        resp_data = json.loads(response.content)
        self.assertTrue('student_schedule_html' in resp_data)
        for sec in sections:
            self.assertTrue(sec.title() in resp_data['student_schedule_html'])
            self.assertTrue(sec.friendly_times()[0] in resp_data['student_schedule_html'])

    def expect_ajaxerror(self, request_url, post_data, error_str):
        # TODO(benkraft): can this be simplified by converting to
        # self.assertRaises?
        error_received = False
        error_msg = ''
        try:
            response = self.client.post(request_url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        except AjaxErrorMiddleware.AjaxError as inst:
            error_received = True
            error_msg = inst.args[0]
        except Exception as inst:
            logger.info('Caught unexpected Ajax student reg error %s: willing '
                        'to see AjaxErrorMiddleware.AjaxError.', inst)
            raise

        if not error_received:
            #   If AjaxErrorMiddleware is engaged, we should get a JSON response.
            response_dict = json.loads(response.content)
            self.assertTrue(int(response_dict['status']) == 200)
            error_received = True
            error_msg = response_dict['error']

        self.assertTrue(error_received)
        self.assertTrue(error_msg == error_str, 'Unexpected Ajax error: "%s", expected "%s"' % (error_msg, error_str))

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
        sec2 = random.choice(ClassSection.objects.filter(parent_class__parent_program=program, meeting_times=sec1.start_time()).exclude(parent_class__id=sec1.parent_class.id))
        self.expect_ajaxerror('/learn/%s/ajax_addclass' % program.getUrlBase(), {'class_id': sec2.parent_class.id, 'section_id': sec2.id}, 'This section conflicts with your schedule--check out the other sections!')

        #   Try adding another section of same class and check that we get an error
        sec3 = random.choice(sec1.parent_class.get_sections().exclude(id=sec1.id))
        self.expect_ajaxerror('/learn/%s/ajax_addclass' % program.getUrlBase(), {'class_id': sec3.parent_class.id, 'section_id': sec3.id}, 'You are already signed up for a section of this class!')

        #   Try adding another class that we can actually take and check that it's there
        sec4 = random.choice(program.sections().exclude(parent_class__id=sec1.parent_class.id).exclude(meeting_times=sec1.meeting_times.all()))
        response = self.client.post('/learn/%s/ajax_addclass' % program.getUrlBase(), {'class_id': sec4.parent_class.id, 'section_id': sec4.id}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_sections_in_schedule(response, [sec1, sec4])

    def test_ajax_clearslot(self):
        program = self.program

        #   Pick a student, log in, schedule 2 classes
        student = random.choice(self.students)
        self.assertTrue( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )
        sec1 = random.choice(program.sections())
        sec1.preregister_student(student)
        sec2 = random.choice(program.sections().exclude(parent_class__id=sec1.parent_class.id).exclude(meeting_times=sec1.meeting_times.all()))
        sec2.preregister_student(student)

        #   Get the schedule and check that both classes are there
        response = self.client.get('/learn/%s/ajax_schedule' % program.getUrlBase(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_sections_in_schedule(response, [sec1, sec2])

        #   Clear 1 timeslot and check that only the desired class remains
        response = self.client.get('/learn/%s/ajax_clearslot/%d' % (program.getUrlBase(), sec1.meeting_times.all()[0].id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_sections_in_schedule(response, [sec2])

        #   Clear other timeslot and check that the schedule is empty
        response = self.client.get('/learn/%s/ajax_clearslot/%d' % (program.getUrlBase(), sec2.meeting_times.all()[0].id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.expect_empty_schedule(response)

    def test_lottery(self):
        # TODO(gkanwar): Make this test actually do something, or remove it
        program = self.program

        self.webdriver.get('/learn/%s/lotterystudentreg' % program.getUrlBase())

