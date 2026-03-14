from django.test import RequestFactory

from esp.middleware.threadlocalrequest import ThreadLocals, clear_current_request
from esp.program.modules.handlers.schedulingcheckmodule import RawSCFormatter, SchedulingCheckRunner
from esp.program.tests import ProgramFrameworkTest
from esp.resources.models import Resource


class SchedulingCheckModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 2,
            'num_rooms': 3,
            'num_teachers': 5,
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
