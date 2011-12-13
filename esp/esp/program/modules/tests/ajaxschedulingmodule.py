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
  Email: web-team@lists.learningu.org
"""

from esp.program.tests import ProgramFrameworkTest

class AJAXSchedulingModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        # Set up the program -- we want to be sure of these parameters
        kwargs.update({
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 2, 'classes_per_teacher': 1, 'sections_per_class': 1
            })
        super(AJAXSchedulingModuleTest, self).setUp(*args, **kwargs)

        # Set the section durations to 1:50
        for sec in self.program.sections():
            sec.duration = '1.83'
            sec.save()

    def testModelAPI(self):
        """Schedule classes using the on-model methods."""

        # Fetch three consecutive vacancies in one room.
        rooms = self.rooms[0].identical_resources().filter(event__in=self.timeslots).order_by('event__start')
        self.failUnless(rooms.count() >= 3, "Not enough timeslots to run this test.")

        # Now we attempt to schedule the sections overlapping.
        s1, s2 = self.program.sections()[:2]

        # First, meeting times should be assigned without trouble.
        m1 = [rooms[0].event, rooms[1].event]
        m2 = [rooms[1].event, rooms[2].event]
        s1.assign_meeting_times(m1)
        s2.assign_meeting_times(m2)
        self.failUnless(set(s1.get_meeting_times()) == set(m1), "Failed to assign meeting times.")
        self.failUnless(set(s2.get_meeting_times()) == set(m2), "Failed to assign meeting times.")

        # Return values should be success on the first one and failure on the second.
        self.failUnless(s1.assign_room(rooms[0])[0] == True, "Received negative response when scheduling first class.")
        self.failUnless(set(s1.classrooms()) == set(rooms[:2]), "Failed to schedule first class.")
        self.failUnless(s2.assign_room(rooms[0])[0] == False, "Failed to detect conflict with first class.")

        # Check that the second attempt did not take.
        self.failUnless(set(s1.classrooms()) == set(rooms[:2]), "First class's schedule modified.")
        self.failUnless(not s2.classrooms().exists(), "Second class should not have any classrooms assigned.")
