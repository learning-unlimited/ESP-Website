# This file is part of the ESP project.
#
# The ESP project is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The ESP project is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with the ESP project.  If not, see <https://www.gnu.org/licenses/>.

from django.test import RequestFactory

from esp.middleware.threadlocalrequest import ThreadLocals, clear_current_request
from esp.program.modules.handlers.schedulingcheckmodule import RawSCFormatter, SchedulingCheckRunner
from esp.program.tests import ProgramFrameworkTest
from esp.resources.models import Resource


class SchedulingCheckModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 2,
            'num_rooms': 5,
            'num_teachers': 8,
            'classes_per_teacher': 1,
            'sections_per_class': 1,
        })
        super().setUp(*args, **kwargs)

        request = RequestFactory().get('/manage/%s/scheduling_checks' % self.program.getUrlBase())
        ThreadLocals().process_request(request)

        self.timeslots = list(self.program.getTimeSlots().order_by('start'))

    def tearDown(self):
        clear_current_request()
        super().tearDown()

    def _room(self, name, timeslot):
        return Resource.objects.get(name=name, event=timeslot)

    def _schedule_section(self, section, timeslot, room_name, moderators):
        section.clearRooms()
        section.clear_meeting_times()
        section.assign_meeting_times([timeslot])
        section.assign_room(self._room(room_name, timeslot))
        section.moderators.set(moderators)

    def test_moderator_movement_dependency_loop_is_reported(self):
        sections = list(self.program.sections().order_by('id')[:4])
        self.assertEqual(len(sections), 4)

        moderator_a = self.teachers[0]
        moderator_b = self.teachers[1]
        slot_0 = self.timeslots[0]
        slot_1 = self.timeslots[1]

        # A and B swap rooms between consecutive blocks, creating a dependency loop.
        self._schedule_section(sections[0], slot_0, 'Room 0', [moderator_a])
        self._schedule_section(sections[1], slot_0, 'Room 1', [moderator_b])
        self._schedule_section(sections[2], slot_1, 'Room 1', [moderator_a])
        self._schedule_section(sections[3], slot_1, 'Room 0', [moderator_b])

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        results = runner.moderator_movement_dependency_loops()

        loop_rows = [row for row in results if row['Loop'] == 'Yes']
        self.assertTrue(loop_rows)
        self.assertTrue(any(
            moderator_a.username in row['Dependency Chain'] and moderator_b.username in row['Dependency Chain']
            for row in loop_rows
        ))

    def test_moderator_dependency_chain_without_loop_is_reported(self):
        sections = list(self.program.sections().order_by('id')[:5])
        self.assertEqual(len(sections), 5)

        moderator_a = self.teachers[0]
        moderator_b = self.teachers[1]
        moderator_d = self.teachers[3]
        slot_0 = self.timeslots[0]
        slot_1 = self.timeslots[1]

        # A depends on B to replace room movement; B has no reciprocal dependency.
        self._schedule_section(sections[0], slot_0, 'Room 0', [moderator_a])
        self._schedule_section(sections[1], slot_0, 'Room 1', [moderator_b])
        self._schedule_section(sections[2], slot_1, 'Room 2', [moderator_a])
        self._schedule_section(sections[3], slot_1, 'Room 0', [moderator_b])
        self._schedule_section(sections[4], slot_1, 'Room 1', [moderator_d])

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        results = runner.moderator_movement_dependency_loops()

        non_loop_rows = [row for row in results if row['Loop'] == 'No']
        self.assertTrue(non_loop_rows)
        self.assertTrue(any(row['Dependency Chain'].startswith('%s -> %s' % (moderator_a.username, moderator_b.username))
                            for row in non_loop_rows))

    def test_moderator_branching_dependencies_are_all_reported(self):
        sections = list(self.program.sections().order_by('id')[:5])
        self.assertEqual(len(sections), 5)

        moderator_a = self.teachers[0]
        moderator_b = self.teachers[1]
        moderator_c = self.teachers[2]
        slot_0 = self.timeslots[0]
        slot_1 = self.timeslots[1]

        # Block 0 assignments.
        self._schedule_section(sections[0], slot_0, 'Room 0', [moderator_a])
        self._schedule_section(sections[1], slot_0, 'Room 1', [moderator_b])
        self._schedule_section(sections[2], slot_0, 'Room 2', [moderator_c])

        # Block 1 assignments:
        # - A moves to Room 2
        # - B and C both move into A's old room (Room 0), creating branches A->B and A->C
        # - C then depends on A through Room 2, creating loop A->C->A
        self._schedule_section(sections[3], slot_1, 'Room 2', [moderator_a])
        self._schedule_section(sections[4], slot_1, 'Room 0', [moderator_b, moderator_c])

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        results = runner.moderator_movement_dependency_loops()

        chains = [row['Dependency Chain'] for row in results]
        self.assertTrue(any(chain.startswith('%s -> %s' % (moderator_a.username, moderator_b.username)) for chain in chains))
        self.assertTrue(any(chain.startswith('%s -> %s -> %s' % (moderator_a.username, moderator_c.username, moderator_a.username))
                            for chain in chains))

    def test_moderator_long_dependency_chain_without_loop_is_reported(self):
        sections = list(self.program.sections().order_by('id')[:8])
        self.assertEqual(len(sections), 8)

        moderator_a = self.teachers[0]
        moderator_b = self.teachers[1]
        moderator_c = self.teachers[2]
        moderator_d = self.teachers[3]
        slot_0 = self.timeslots[0]
        slot_1 = self.timeslots[1]

        # Build a non-loop chain A -> B -> C -> D across two contiguous blocks.
        self._schedule_section(sections[0], slot_0, 'Room 0', [moderator_a])
        self._schedule_section(sections[1], slot_0, 'Room 1', [moderator_b])
        self._schedule_section(sections[2], slot_0, 'Room 2', [moderator_c])
        self._schedule_section(sections[3], slot_0, 'Room 3', [moderator_d])

        self._schedule_section(sections[4], slot_1, 'Room 4', [moderator_a])
        self._schedule_section(sections[5], slot_1, 'Room 0', [moderator_b])
        self._schedule_section(sections[6], slot_1, 'Room 1', [moderator_c])
        self._schedule_section(sections[7], slot_1, 'Room 2', [moderator_d])

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        results = runner.moderator_movement_dependency_loops()

        long_non_loop_chain = '%s -> %s -> %s -> %s' % (
            moderator_a.username,
            moderator_b.username,
            moderator_c.username,
            moderator_d.username,
        )
        self.assertTrue(any(row['Dependency Chain'] == long_non_loop_chain and row['Loop'] == 'No'
                            for row in results))

    def test_moderator_long_dependency_loop_is_reported(self):
        sections = list(self.program.sections().order_by('id')[:6])
        self.assertEqual(len(sections), 6)

        moderator_a = self.teachers[0]
        moderator_b = self.teachers[1]
        moderator_c = self.teachers[2]
        slot_0 = self.timeslots[0]
        slot_1 = self.timeslots[1]

        # Build a loop A -> B -> C -> A across two contiguous blocks.
        self._schedule_section(sections[0], slot_0, 'Room 0', [moderator_a])
        self._schedule_section(sections[1], slot_0, 'Room 1', [moderator_b])
        self._schedule_section(sections[2], slot_0, 'Room 2', [moderator_c])

        self._schedule_section(sections[3], slot_1, 'Room 2', [moderator_a])
        self._schedule_section(sections[4], slot_1, 'Room 0', [moderator_b])
        self._schedule_section(sections[5], slot_1, 'Room 1', [moderator_c])

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        results = runner.moderator_movement_dependency_loops()

        long_loop_chain = '%s -> %s -> %s -> %s' % (
            moderator_a.username,
            moderator_b.username,
            moderator_c.username,
            moderator_a.username,
        )
        self.assertTrue(any(row['Dependency Chain'] == long_loop_chain and row['Loop'] == 'Yes'
                            for row in results))
