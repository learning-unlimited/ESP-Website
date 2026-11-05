"""Tests for ScheduleManipulator.swap_sections."""

import json
import unittest

from esp.program.controllers.autoscheduler import data_model, testutils
from esp.program.controllers.autoscheduler.manipulator import \
    ScheduleManipulator

SCORER_WEIGHTS = {
    "NumSectionsScorer": 100.0,
    "NumTeachersScorer": 50.0,
    "RoomSizeMismatchScorer": 30.0,
    "HungryTeacherScorer": 70.0,
    "StudentClassHoursScorer": 50.0,
}


def make_schedule():
    """The standard test schedule plus section 3, which has the same duration
    as section 1, and sections 4 and 5, which share a longer duration (so
    each of those pairs can be swapped). Each new section has its own teacher,
    available at all times."""
    schedule = testutils.create_test_schedule_1()
    for teacher_id, section_id, duration, category in [(4, 3, 0.83, 0),
                                                       (5, 4, 1.83, 1),
                                                       (6, 5, 1.83, 1)]:
        teacher = data_model.AS_Teacher(list(schedule.timeslots), teacher_id)
        schedule.teachers[teacher_id] = teacher
        schedule.class_sections[section_id] = data_model.AS_ClassSection(
            [teacher], duration, 20, category, [], section_id, 0)
    return schedule


class SwapSectionsTest(unittest.TestCase):
    def setUp(self):
        self.schedule = make_schedule()
        self.manipulator = ScheduleManipulator(
            self.schedule, constraint_names=[],
            scorer_names_and_weights=SCORER_WEIGHTS)
        self.rooms = self.schedule.classrooms["26-100"].availability
        self.s1 = self.schedule.class_sections[1]
        self.s2 = self.schedule.class_sections[2]
        self.s3 = self.schedule.class_sections[3]
        self.s4 = self.schedule.class_sections[4]
        self.s5 = self.schedule.class_sections[5]

    def schedule_both(self):
        self.assertTrue(self.manipulator.schedule_section(
            self.s1, self.rooms[0]))
        self.assertTrue(self.manipulator.schedule_section(
            self.s3, self.rooms[1]))

    def test_swaps_two_scheduled_sections(self):
        self.schedule_both()
        self.assertTrue(self.manipulator.swap_sections(self.s1, self.s3))
        self.assertEqual(self.s1.assigned_roomslots, [self.rooms[1]])
        self.assertEqual(self.s3.assigned_roomslots, [self.rooms[0]])
        self.assertIs(self.rooms[1].assigned_section, self.s1)
        self.assertIs(self.rooms[0].assigned_section, self.s3)
        self.assertEqual(
            [a["action"] for a in self.manipulator.history],
            ["schedule", "schedule", "swap"])

    def test_undo_of_swap_restores_original_placement(self):
        self.schedule_both()
        self.manipulator.swap_sections(self.s1, self.s3)
        self.assertTrue(self.manipulator.undo())
        self.assertEqual(self.s1.assigned_roomslots, [self.rooms[0]])
        self.assertEqual(self.s3.assigned_roomslots, [self.rooms[1]])
        self.assertIs(self.rooms[0].assigned_section, self.s1)
        self.assertIs(self.rooms[1].assigned_section, self.s3)
        self.assertEqual(
            [a["action"] for a in self.manipulator.history],
            ["schedule", "schedule"])

    def test_swap_keeps_scores_consistent(self):
        """Scores after a swap match those of a fresh manipulator with the
        sections placed directly in the swapped positions."""
        self.schedule_both()
        self.manipulator.swap_sections(self.s1, self.s3)

        other_schedule = make_schedule()
        other = ScheduleManipulator(
            other_schedule, constraint_names=[],
            scorer_names_and_weights=SCORER_WEIGHTS)
        other_rooms = other_schedule.classrooms["26-100"].availability
        other.schedule_section(other_schedule.class_sections[1],
                               other_rooms[1])
        other.schedule_section(other_schedule.class_sections[3],
                               other_rooms[0])
        self.assertAlmostEqual(self.manipulator.scorer.score_schedule(),
                               other.scorer.score_schedule())

    def test_swaps_sections_spanning_several_roomslots(self):
        self.assertTrue(self.manipulator.schedule_section(
            self.s4, self.rooms[0]))
        self.assertTrue(self.manipulator.schedule_section(
            self.s5, self.rooms[3]))
        self.assertTrue(self.manipulator.swap_sections(self.s4, self.s5))
        self.assertEqual(self.s4.assigned_roomslots, self.rooms[3:5])
        self.assertEqual(self.s5.assigned_roomslots, self.rooms[0:2])
        for roomslot in self.rooms[0:2]:
            self.assertIs(roomslot.assigned_section, self.s5)
        for roomslot in self.rooms[3:5]:
            self.assertIs(roomslot.assigned_section, self.s4)

        self.assertTrue(self.manipulator.undo())
        self.assertEqual(self.s4.assigned_roomslots, self.rooms[0:2])
        self.assertEqual(self.s5.assigned_roomslots, self.rooms[3:5])

    def test_swap_survives_saving_and_replaying_history(self):
        self.schedule_both()
        self.manipulator.swap_sections(self.s1, self.s3)
        saved = json.loads(json.dumps(self.manipulator.jsonify_history()))

        schedule = make_schedule()
        replay = ScheduleManipulator(
            schedule, constraint_names=[],
            scorer_names_and_weights=SCORER_WEIGHTS)
        self.assertTrue(replay.load_history(saved))
        rooms = schedule.classrooms["26-100"].availability
        self.assertEqual(schedule.class_sections[1].assigned_roomslots,
                         [rooms[1]])
        self.assertEqual(schedule.class_sections[3].assigned_roomslots,
                         [rooms[0]])
        self.assertEqual([a["action"] for a in replay.history],
                         ["schedule", "schedule", "swap"])

    def test_rejected_swap_leaves_history_and_schedule_unchanged(self):
        # Sections 1 and 2 have different durations. Section 2 can only start
        # in the second roomslot.
        self.assertTrue(self.manipulator.schedule_section(
            self.s1, self.rooms[0]))
        self.assertTrue(self.manipulator.schedule_section(
            self.s2, self.rooms[1]))
        history_length = len(self.manipulator.history)
        self.assertFalse(self.manipulator.swap_sections(self.s1, self.s2))
        self.assertEqual(len(self.manipulator.history), history_length)
        self.assertEqual(self.s1.assigned_roomslots, [self.rooms[0]])
        self.assertEqual(self.s2.assigned_roomslots, self.rooms[1:3])
