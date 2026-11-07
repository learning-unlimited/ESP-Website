"""Tests for AutoschedulerController's history handling."""

import json
import unittest
from types import SimpleNamespace
from unittest import mock

from esp.program.controllers.autoscheduler import controller as controller_mod
from esp.program.controllers.autoscheduler.controller import \
    AutoschedulerController
from esp.program.controllers.autoscheduler.exceptions import SchedulingError
from esp.program.controllers.autoscheduler.manipulator import \
    ScheduleManipulator
from esp.program.controllers.autoscheduler.test_manipulator_swap import \
    make_schedule


class ControllerTestCase(unittest.TestCase):
    """Base class: a controller built around a manipulator, skipping the
    database setup done by AutoschedulerController.__init__."""

    def setUp(self):
        """Create the schedule, manipulator, controller and shortcuts."""
        self.schedule = make_schedule()
        self.manipulator = ScheduleManipulator(
            self.schedule, constraint_names=[], scorer_names_and_weights={})
        self.controller = AutoschedulerController.__new__(
            AutoschedulerController)
        self.controller.options = {}
        self.controller.schedule = self.schedule
        self.controller.optimizer = SimpleNamespace(
            manipulator=self.manipulator)
        self.rooms = self.schedule.classrooms["26-100"].availability
        self.s1 = self.schedule.class_sections[1]
        self.s3 = self.schedule.class_sections[3]

    def simplified(self):
        """The simplified version of the manipulator's history."""
        return self.controller.simplify_history(self.manipulator.history)


class SimplifyHistoryTest(ControllerTestCase):
    """simplify_history collapses a history to one action per section."""

    def test_empty_history(self):
        """An empty history stays empty."""
        self.assertEqual(self.simplified(), [])

    def test_schedule_only(self):
        """A lone schedule stays a schedule."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.assertEqual(self.simplified(), [{
            "action": "schedule", "section": self.s1,
            "start_roomslot": self.rooms[0]}])

    def test_move_only(self):
        """A move of an already scheduled section stays a move."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.history = []
        self.manipulator.move_section(self.s1, self.rooms[3])
        self.assertEqual(self.simplified(), [{
            "action": "move", "section": self.s1,
            "start_roomslot": self.rooms[3],
            "prev_start_roomslot": self.rooms[0]}])

    def test_unschedule_only(self):
        """A lone unschedule stays an unschedule."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.history = []
        self.manipulator.unschedule_section(self.s1)
        self.assertEqual(self.simplified(), [{
            "action": "unschedule", "section": self.s1,
            "prev_start_roomslot": self.rooms[0]}])

    def test_schedule_then_move_is_one_schedule(self):
        """Scheduling and then moving a section is a schedule at the end
        position."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.move_section(self.s1, self.rooms[3])
        self.assertEqual(self.simplified(), [{
            "action": "schedule", "section": self.s1,
            "start_roomslot": self.rooms[3]}])

    def test_unschedule_then_schedule_is_a_move(self):
        """Unscheduling and rescheduling elsewhere counts as a move."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.history = []
        self.manipulator.unschedule_section(self.s1)
        self.manipulator.schedule_section(self.s1, self.rooms[4])
        self.assertEqual(self.simplified(), [{
            "action": "move", "section": self.s1,
            "start_roomslot": self.rooms[4],
            "prev_start_roomslot": self.rooms[0]}])

    def test_schedule_then_unschedule_is_dropped(self):
        """A section that is scheduled and then unscheduled has no net
        effect, so it does not appear (and does not raise)."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.unschedule_section(self.s1)
        self.assertEqual(self.simplified(), [])

    def test_swap_becomes_two_moves(self):
        """A swap of scheduled sections becomes a move for each section."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.schedule_section(self.s3, self.rooms[1])
        self.manipulator.history = []
        self.assertTrue(self.manipulator.swap_sections(self.s1, self.s3))
        result = {a["section"]: a for a in self.simplified()}
        self.assertEqual(set(result), {self.s1, self.s3})
        self.assertEqual(result[self.s1]["action"], "move")
        self.assertEqual(result[self.s1]["prev_start_roomslot"],
                         self.rooms[0])
        self.assertEqual(result[self.s1]["start_roomslot"], self.rooms[1])
        self.assertEqual(result[self.s3]["prev_start_roomslot"],
                         self.rooms[1])
        self.assertEqual(result[self.s3]["start_roomslot"], self.rooms[0])

    def test_one_action_per_section(self):
        """Several actions on different sections give one action each."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.schedule_section(self.s3, self.rooms[1])
        self.manipulator.move_section(self.s1, self.rooms[4])
        result = self.simplified()
        self.assertEqual({a["section"] for a in result}, {self.s1, self.s3})
        self.assertEqual(len(result), 2)


class ImportAssignmentsTest(ControllerTestCase):
    """import_assignments replays an exported history."""

    def export(self):
        """Export the current history and section states."""
        return self.controller.export_assignments()[0]

    def test_round_trip(self):
        """A history exported from one schedule replays on a fresh one."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.schedule_section(self.s3, self.rooms[1])
        # Assignments are stored as JSON, so go through a real dump/load.
        data = json.loads(json.dumps(self.export()))

        other = ControllerTestCase("setUp")
        other.setUp()
        other.controller.import_assignments(data)

        self.assertIs(other.s1.assigned_roomslots[0], other.rooms[0])
        self.assertIs(other.s3.assigned_roomslots[0], other.rooms[1])
        self.assertEqual([a["action"] for a in other.manipulator.history],
                         ["schedule", "schedule"])

    def test_changed_section_is_rejected(self):
        """A section whose saved state has changed since export raises."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        history, hashes = self.export()
        hashes[self.s1.id] = "something else"

        with mock.patch.object(controller_mod, "ClassSection") as cls:
            cls.objects.get.return_value.emailcode.return_value = "S1s1"
            with self.assertRaises(SchedulingError):
                self.controller.import_assignments([history, hashes])

    def test_unreplayable_history_is_rejected(self):
        """A history that can't be performed raises SchedulingError."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        history, hashes = self.export()
        history = history + history  # scheduling the same section twice

        other = ControllerTestCase("setUp")
        other.setUp()
        with self.assertRaises(SchedulingError):
            other.controller.import_assignments([history, hashes])
