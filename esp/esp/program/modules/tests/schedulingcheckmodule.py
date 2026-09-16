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
from esp.program.models import ClassCategories
from esp.program.modules.handlers.schedulingcheckmodule import RawSCFormatter, SchedulingCheckRunner
from esp.program.tests import ProgramFrameworkTest
from esp.resources.models import Resource, ResourceRequest, ResourceType
from esp.tagdict.models import Tag

import json


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
        ThreadLocals(get_response=lambda request: None).process_request(request)

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


class SchedulingCheckSnapshotTest(ProgramFrameworkTest):
    """Diagnostics must not change or blow up when the schedule moves under them.

    See issue #511: the checks used to re-query meeting times and rooms as they
    iterated, so a class unscheduled by someone else mid-run made later checks
    disagree with earlier ones, or index into an empty result and 500.
    """

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 2,
            'num_rooms': 4,
            'num_teachers': 3,
            'classes_per_teacher': 1,
            'sections_per_class': 1,
        })
        super().setUp(*args, **kwargs)

        request = RequestFactory().get('/manage/%s/scheduling_checks' % self.program.getUrlBase())
        ThreadLocals(get_response=lambda request: None).process_request(request)

        self.timeslots = list(self.program.getTimeSlots().order_by('start'))
        for teacher in self.teachers:
            for timeslot in self.timeslots:
                teacher.addAvailableTime(self.program, timeslot)

        self.sections = list(self.program.sections().order_by('id'))
        for i, section in enumerate(self.sections):
            timeslot = self.timeslots[i % len(self.timeslots)]
            section.assign_meeting_times([timeslot])
            section.assign_room(Resource.objects.get(name='Room %d' % i, event=timeslot))

    def tearDown(self):
        clear_current_request()
        super().tearDown()

    def _all_results(self, runner):
        return runner.run_diagnostics([name for name, title in runner.all_diagnostics()])

    def test_results_are_unchanged_when_a_section_is_unscheduled_mid_run(self):
        runner = SchedulingCheckRunner(self.program)
        before = self._all_results(runner)

        # Someone else unschedules a class while the run is in progress.
        victim = self.sections[0]
        victim.clearRooms()
        victim.clear_meeting_times()

        self.assertEqual(self._all_results(runner), before)

    def test_snapshotted_unsatisfied_requests_match_the_model(self):
        # The snapshot recomputes ClassSection.unsatisfied_requests() in memory,
        # so it has to agree with the model it replaces.
        section = self.sections[0]
        res_type = ResourceType.get_or_create('LCD Projector')
        ResourceRequest.objects.create(target=section, res_type=res_type, desired_value='Yes')

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        runner._build_snapshot()
        for snapshot_section in runner.all_sections:
            self.assertEqual(
                sorted(r.id for r in runner._unsatisfied_requests(snapshot_section)),
                sorted(r.id for r in snapshot_section.unsatisfied_requests()),
            )

    def test_snapshot_is_not_built_until_a_diagnostic_needs_it(self):
        # The diagnostics landing page builds a runner just to list the checks.
        runner = SchedulingCheckRunner(self.program)
        self.assertFalse(runner.built_snapshot)
        runner.all_diagnostics()
        self.assertFalse(runner.built_snapshot)
        runner.incompletely_scheduled_classes()
        self.assertTrue(runner.built_snapshot)

    def test_unapproved_scheduled_classes_reports_unreviewed_sections(self):
        # Unapproved sections are excluded from the snapshot, so this check has
        # to look them up separately or it can never report anything.
        section = self.sections[0]
        section.status = 0
        section.save()

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        self.assertIn(section, runner.unapproved_scheduled_classes())

    def test_no_overlap_classes_reports_each_class_once_per_block(self):
        first, second = self.sections[0], self.sections[1]
        second.assign_meeting_times(list(first.get_meeting_times()))
        class_ids = [first.parent_class_id, second.parent_class_id]
        Tag.setTag('no_overlap_classes', self.program, json.dumps({'materials': class_ids}))

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        rows = runner.no_overlap_classes()

        self.assertEqual(len(rows), 1)
        self.assertEqual(sorted(cls.id for cls in rows[0]['Classes']), sorted(class_ids))

    def test_teachers_who_like_running_compares_rooms_across_back_to_back_sections(self):
        teacher = self.teachers[0]
        first, second = self.sections[0], self.sections[1]
        for section in (first, second):
            section.parent_class.teachers.set([teacher])
        # Adjacent timeslots, different rooms: the teacher has to run.
        first.clearRooms()
        second.clearRooms()
        first.assign_meeting_times([self.timeslots[0]])
        first.assign_room(Resource.objects.get(name='Room 0', event=self.timeslots[0]))
        second.assign_meeting_times([self.timeslots[1]])
        second.assign_room(Resource.objects.get(name='Room 1', event=self.timeslots[1]))

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        rows = runner.teachers_who_like_running()

        self.assertEqual([row['Username'] for row in rows], [teacher])
        self.assertEqual(rows[0]['Room 1'].name, 'Room 0')
        self.assertEqual(rows[0]['Room 2'].name, 'Room 1')

    def test_teachers_who_like_running_ignores_sections_without_meeting_times(self):
        teacher = self.teachers[0]
        for section in self.sections:
            section.parent_class.teachers.set([teacher])
        # Two sections with rooms but no times would previously make the sort
        # key compare None to None and raise TypeError.
        for section in self.sections[:2]:
            section.clear_meeting_times()

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        self.assertEqual(runner.teachers_who_like_running(), [])


class SchedulingCheckLunchTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 2,
            'num_rooms': 4,
            'num_teachers': 2,
            'classes_per_teacher': 1,
            'sections_per_class': 1,
        })
        super().setUp(*args, **kwargs)

        request = RequestFactory().get('/manage/%s/scheduling_checks' % self.program.getUrlBase())
        ThreadLocals(get_response=lambda request: None).process_request(request)

        self.timeslots = list(self.program.getTimeSlots().order_by('start'))
        self.lunch_slot = self.timeslots[0]

        # Reserve the first timeslot for lunch by scheduling a lunch class in it.
        lunch_category = ClassCategories.objects.create(category='Lunch', symbol='L', seq=0, is_lunch=True)
        lunch_section = self.program.sections().order_by('id')[0]
        lunch_section.parent_class.category = lunch_category
        lunch_section.parent_class.save()
        lunch_section.assign_meeting_times([self.lunch_slot])

        # A teacher scheduled straight through lunch.
        self.hungry_section = self.program.sections().order_by('id')[1]
        self.hungry_teacher = self.hungry_section.parent_class.get_teachers()[0]
        self.hungry_section.assign_meeting_times([self.lunch_slot])
        self.hungry_section.assign_room(Resource.objects.get(name='Room 0', event=self.lunch_slot))

    def tearDown(self):
        clear_current_request()
        super().tearDown()

    def test_hungry_teachers_reports_teacher_scheduled_through_lunch(self):
        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        rows = runner.hungry_teachers()

        self.assertEqual([row['Username'] for row in rows], [self.hungry_teacher])
        self.assertEqual(rows[0]['Classes over lunch'], str(self.hungry_section))

    def test_hungry_teachers_survives_unscheduling_mid_run(self):
        # The old implementation re-queried sections per lunch block and indexed
        # the first result, so an unschedule between queries raised IndexError.
        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        before = runner.hungry_teachers()

        self.hungry_section.clearRooms()
        self.hungry_section.clear_meeting_times()

        self.assertEqual(runner.hungry_teachers(), before)

    def test_classes_which_cover_lunch_reports_the_section(self):
        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        self.assertEqual(runner.classes_which_cover_lunch(), [self.hungry_section])
