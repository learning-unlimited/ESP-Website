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

from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.tests.support import TestProgramManager
from esp.program.modules.module_ext import AJAXChangeLog
import json
import time

class AJAXSchedulingModuleTestBase(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj
        # Set up the program -- we want to be sure of these parameters
        kwargs.update({
            'num_rooms': 4,
            'num_timeslots': 4, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 3, 'classes_per_teacher': 2, 'sections_per_class': 1
            })
        super(AJAXSchedulingModuleTestBase, self).setUp(*args, **kwargs)
        self.program_manager = TestProgramManager(self.client, self.program, self.teachers, self.rooms, self.timeslots)

        # Set the section durations to 1:50
        for sec in self.program.sections():
            sec.duration = '1.83'
            sec.save()

        #some useful urls
        self.ajax_url_base = '/manage/%s/' % self.program.getUrlBase()
        self.changelog_url = self.ajax_url_base + 'ajax_change_log'
        self.schedule_class_url = '/manage/%s/' % self.program.getUrlBase() + 'ajax_schedule_class'


    def loginAdmin(self):
        """Log in an admin user."""
        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'), "Failed to log in admin user.")

    def emptySchedule(self):
        """Empty the schedule and teacher availability."""
        for s in self.program.sections():
            s.clearRooms()
            s.clear_meeting_times()
        for t in self.teachers:
            t.clearAvailableTimes(self.program)

    def forceAvailability(self):
        for teacher in self.teachers:
            for ts in self.program.getTimeSlots():
                teacher.addAvailableTime(self.program, ts)


    def clearScheduleAvailability(self):
        self.emptySchedule()
        self.loginAdmin()
        self.forceAvailability()

class AJAXSchedulingModuleTest(AJAXSchedulingModuleTestBase):

    def setUp(self, *args, **kwargs):
        super(AJAXSchedulingModuleTest, self).setUp(*args, **kwargs)
        self.changelog, created = AJAXChangeLog.objects.get_or_create(program=self.program)

    def testModelAPI(self):
        """Schedule classes using the on-model methods."""
        self.emptySchedule()

        # Fetch three consecutive vacancies in one room.
        rooms = self.rooms[0].identical_resources().filter(event__in=self.timeslots).order_by('event__start')
        self.assertTrue(rooms.count() >= 3, "Not enough timeslots to run this test.")

        # Now we attempt to schedule the sections overlapping.
        s1, s2 = [t.getTaughtSections(self.program)[0] for t in self.teachers[:2]]

        # First, meeting times should be assigned without trouble.
        m1 = [rooms[0].event, rooms[1].event]
        m2 = [rooms[1].event, rooms[2].event]
        s1.assign_meeting_times(m1)
        s2.assign_meeting_times(m2)
        self.assertTrue(set(s1.get_meeting_times()) == set(m1), "Failed to assign meeting times.")
        self.assertTrue(set(s2.get_meeting_times()) == set(m2), "Failed to assign meeting times.")

        # Return values should be success on the first one and failure on the second.
        self.assertTrue(s1.assign_room(rooms[0])[0] == True, "Received negative response when scheduling first class.")
        self.assertTrue(set(s1.classrooms()) == set(rooms[:2]), "Failed to schedule first class.")
        self.assertTrue(s2.assign_room(rooms[0])[0] == False, "Failed to detect conflict with first class.")

        # Check that the second attempt did not take.
        self.assertTrue(set(s1.classrooms()) == set(rooms[:2]), "First class's schedule modified.")
        self.assertTrue(not s2.classrooms().exists(), "Second class should not have any classrooms assigned.")


    def testWebAPI(self):
        """Schedule classes using the ajax_schedule_class view."""
        self.clearScheduleAvailability()

        # Attempt to give a teacher a schedule conflict.
        t = self.teachers[0]

        # Fetch two consecutive vacancies in two different rooms
        rooms = self.rooms[0].identical_resources().filter(event__in=self.timeslots).order_by('event__start')
        self.assertTrue(rooms.count() >= 2, "Not enough timeslots to run this test.")
        a1 = '\n'.join(['%s,%s' % (r.event.id, r.identical_id()) for r in rooms[0:2]])
        rooms = self.rooms.exclude(name=rooms[0].name)[0].identical_resources().filter(event__in=self.timeslots).order_by('event__start')
        self.assertTrue(rooms.count() >= 2, "Not enough timeslots to run this test.")
        a2 = '\n'.join(['%s,%s' % (r.event.id, r.identical_id()) for r in rooms[0:2]])

        # Schedule one class.
        ajax_url = '/manage/%s/ajax_schedule_class' % self.program.getUrlBase()
        s1, s2 = t.getTaughtSections(self.program)[:2]
        timeslots = self.program.getTimeSlots().order_by('start')
        self.client.post(ajax_url, {'action': 'deletereg', 'cls': s1.id})
        self.client.post(ajax_url, {'action': 'assignreg', 'cls': s1.id, 'block_room_assignments': a1, 'override': 'false'})
        self.assertTrue(set(s1.get_meeting_times()) == set(timeslots[0:2]), "Failed to assign meeting times.")
        # Try to schedule the other class.
        self.client.post(ajax_url, {'action': 'deletereg', 'cls': s2.id})
        self.client.post(ajax_url, {'action': 'assignreg', 'cls': s2.id, 'block_room_assignments': a2, 'override': 'false'})
        self.assertTrue(set(s1.get_meeting_times()) == set(timeslots[0:2]), "Existing meeting times clobbered.")
        self.assertTrue(set(s2.get_meeting_times()) == set(), "Failed to prevent teacher conflict.")


    #############################################################
    #
    #   Changelog tests
    #
    #############################################################
    #TODO:  is there a reason we send the time back?
    #TODO:  make the system handle last fetched index 0
    #TODO:  think about test cleanup.
    def testChangeLog(self):
        self.clearScheduleAvailability()

        #put something in the changelog to fetch
        self.program_manager.scheduleClass()

        #fetch the changelog
        changelog_response = self.client.get(self.changelog_url, {'last_fetched_index': 0 })
        self.assertTrue(changelog_response.status_code == 200, "Changelog not successfully retreieved")
        changelog = json.loads(changelog_response.content)["changelog"]
        self.assertTrue(len(changelog) == 1, "Change log does not contain exactly one class: " + str(changelog) )

    #TODO use a new program for each test
    def testChangeLogIndexZero(self):
        self.clearScheduleAvailability()
        self.program_manager.scheduleClass()
        changelog_response = self.client.get(self.changelog_url, {'last_fetched_index': 0 })
        changelog = json.loads(changelog_response.content)["changelog"]
        self.assertTrue(len(changelog) == 1, "Change log does not contain exactly one class: " + str(changelog) )


    def testChangeLogUnscheduledClasses(self):
        self.clearScheduleAvailability()

        (section, times, rooms, success) = self.program_manager.scheduleClass()
        self.failUnless(success)

        self.program_manager.unschedule_class(section.id)

        #change log should include unscheduled classes
        changelog_response = self.client.get(self.changelog_url, {'last_fetched_index': 1 })
        changelog = json.loads(changelog_response.content)["changelog"]
        self.assertTrue(len(changelog) == 1, "Change log did not contain the unscheduled class: " + str(changelog))
        #TODO:  more detailed testing here

    def testChangeLogFailedScheduling(self):
        #change log should not include failed scheduling of classes
        self.clearScheduleAvailability()
        (s1, times, rooms, success) = self.program_manager.scheduleClass()
        self.failUnless(success)

        #Long setup to create an unsuccessful scheduling attempt
        #choose another section taught by the same teacher
        teacher = s1.parent_class.get_teachers()[0]
        sections = [s2 for s2 in teacher.getTaughtSections() if s2.id != s1.id]
        assert len(sections) > 0
        #our test set up makes this true, but we want to be notified if this changes and tests are going to break because of it
        s2 = sections[0]
        #schedule it
        (section, times, rooms, success) = self.program_manager.scheduleClass(section=s2, timeslots=times, rooms=rooms)
        self.failIf(success)

        #change log should not include it
        changelog_response = self.client.get(self.changelog_url, {'last_fetched_index': 1 })
        changelog = json.loads(changelog_response.content)["changelog"]
        self.assertTrue(len(changelog) == 0, "Change log shows unsuccessfully scheduled class: " + str(changelog))
