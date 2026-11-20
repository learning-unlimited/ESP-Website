"""Tests for AutoschedulerController.export_assignments."""

import unittest
from types import SimpleNamespace

from esp.program.controllers.autoscheduler.controller import \
    AutoschedulerController
from esp.program.controllers.autoscheduler.manipulator import \
    ScheduleManipulator
from esp.program.controllers.autoscheduler.test_manipulator_swap import \
    make_schedule


class ExportAssignmentsTest(unittest.TestCase):
    """export_assignments with every kind of history record."""

    def setUp(self):
        """Build a controller around a manipulator, skipping the database
        setup that AutoschedulerController.__init__ does."""
        self.schedule = make_schedule()
        self.manipulator = ScheduleManipulator(
            self.schedule, constraint_names=[], scorer_names_and_weights={})
        self.controller = AutoschedulerController.__new__(
            AutoschedulerController)
        self.controller.options = {}
        self.controller.optimizer = SimpleNamespace(
            manipulator=self.manipulator)
        self.rooms = self.schedule.classrooms["26-100"].availability
        self.s1 = self.schedule.class_sections[1]
        self.s3 = self.schedule.class_sections[3]

    def test_export_with_swap_in_history(self):
        """A swap record (which has "sections", not "section") exports
        without error and records the initial state of both sections."""
        self.assertTrue(self.manipulator.schedule_section(
            self.s1, self.rooms[0]))
        self.assertTrue(self.manipulator.schedule_section(
            self.s3, self.rooms[1]))
        self.assertTrue(self.manipulator.swap_sections(self.s1, self.s3))

        history, hashes = self.controller.export_assignments()[0]

        self.assertEqual([a["action"] for a in history],
                         ["schedule", "schedule", "swap"])
        self.assertEqual(set(hashes), {self.s1.id, self.s3.id})
        self.assertEqual(hashes[self.s1.id], self.s1.initial_state)
        self.assertEqual(hashes[self.s3.id], self.s3.initial_state)

    def test_export_swap_only_history(self):
        """A history made of swaps of already-scheduled sections includes
        both sections in the exported hashes."""
        self.assertTrue(self.manipulator.schedule_section(
            self.s1, self.rooms[0], force=True))
        self.assertTrue(self.manipulator.schedule_section(
            self.s3, self.rooms[1], force=True))
        self.manipulator.history = []
        self.assertTrue(self.manipulator.swap_sections(self.s1, self.s3))

        _, hashes = self.controller.export_assignments()[0]

        self.assertEqual(set(hashes), {self.s1.id, self.s3.id})

    def test_export_without_swap(self):
        """Histories without swaps still export one hash per section."""
        self.assertTrue(self.manipulator.schedule_section(
            self.s1, self.rooms[0]))
        self.assertTrue(self.manipulator.move_section(
            self.s1, self.rooms[2]))

        _, hashes = self.controller.export_assignments()[0]

        self.assertEqual(set(hashes), {self.s1.id})

    def test_export_empty_history(self):
        """With no actions taken, nothing is exported."""
        history, hashes = self.controller.export_assignments()[0]

        self.assertEqual(history, [])
        self.assertEqual(hashes, {})
