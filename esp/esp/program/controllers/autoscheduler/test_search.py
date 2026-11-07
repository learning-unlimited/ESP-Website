"""Tests for SearchOptimizer."""

import datetime
import unittest

from esp.program.controllers.autoscheduler import data_model, testutils
from esp.program.controllers.autoscheduler.manipulator import \
    ScheduleManipulator
from esp.program.controllers.autoscheduler.search import SearchOptimizer

SCORER_WEIGHTS = {"NumSectionsScorer": 100.0}


def make_schedule():
    """The standard test schedule plus section 3, which has the same duration
    as section 1 and its own teacher, available at all times."""
    schedule = testutils.create_test_schedule_1()
    teacher = data_model.AS_Teacher(list(schedule.timeslots), 4)
    schedule.teachers[4] = teacher
    schedule.class_sections[3] = data_model.AS_ClassSection(
        [teacher], 0.83, 20, 0, [], 3, 0)
    return schedule


class SearchOptimizerTest(unittest.TestCase):
    """optimize_section and revert."""

    def setUp(self):
        """Create a schedule, a manipulator, an optimizer and shortcuts."""
        self.schedule = make_schedule()
        self.manipulator = ScheduleManipulator(
            self.schedule, constraint_names=[],
            scorer_names_and_weights=SCORER_WEIGHTS)
        self.optimizer = SearchOptimizer(self.manipulator)
        self.rooms = self.schedule.classrooms["26-100"].availability
        self.s1 = self.schedule.class_sections[1]
        self.s2 = self.schedule.class_sections[2]
        self.s3 = self.schedule.class_sections[3]

    def test_depth_zero_does_nothing(self):
        """A depth of 0 returns no actions and changes nothing."""
        self.assertEqual(self.optimizer.optimize_section(self.s1, 0), [])
        self.assertFalse(self.s1.is_scheduled())
        self.assertEqual(self.manipulator.history, [])

    def test_expired_timeout_does_nothing(self):
        """A timeout that has already passed returns no actions."""
        timeout = datetime.datetime.now() - datetime.timedelta(seconds=1)
        self.assertEqual(
            self.optimizer.optimize_section(self.s1, 2, timeout), [])
        self.assertFalse(self.s1.is_scheduled())

    def test_schedules_unscheduled_section(self):
        """An unscheduled section gets scheduled, and the actions returned
        are the ones left in the history."""
        actions = self.optimizer.optimize_section(self.s1, 1)

        self.assertTrue(self.s1.is_scheduled())
        self.assertEqual([a["action"] for a in actions], ["schedule"])
        self.assertEqual(self.manipulator.history, actions)

    def test_scheduled_section_is_not_moved_without_improvement(self):
        """A section that is already scheduled stays where it is, since moving
        it does not raise the score."""
        self.assertTrue(self.manipulator.schedule_section(
            self.s1, self.rooms[0]))
        before = self.s1.assigned_roomslots

        actions = self.optimizer.optimize_section(self.s1, 1)

        self.assertEqual(actions, [])
        self.assertEqual(self.s1.assigned_roomslots, before)
        self.assertEqual(len(self.manipulator.history), 1)

    def test_no_eviction_at_depth_one(self):
        """At depth 1 a section is never scheduled by evicting another one."""
        room = self.schedule.classrooms["26-100"]
        # Occupy every slot so the only way in is to evict someone.
        for i, section in enumerate([self.s1, self.s3]):
            self.assertTrue(self.manipulator.schedule_section(
                section, room.availability[i], force=True))
        for classroom in self.schedule.classrooms.values():
            for roomslot in classroom.availability:
                if roomslot.assigned_section is None:
                    roomslot.assigned_section = self.s2
        history_before = list(self.manipulator.history)

        actions = self.optimizer.optimize_section(self.s2, 1)

        self.assertEqual(actions, [])
        self.assertEqual(self.manipulator.history, history_before)
        self.assertTrue(self.s1.is_scheduled())
        self.assertTrue(self.s3.is_scheduled())

    def test_failed_reschedule_of_evicted_section_reverts_only_attempt(self):
        """If an evicted section can't be put back, only the attempt is
        undone; earlier, unrelated history survives. Section 2 can only go in
        roomslot 1 of room 26-100, so trying section 3 there evicts it
        for good."""
        self.assertTrue(self.manipulator.schedule_section(
            self.s2, self.rooms[1]))

        actions = self.optimizer.optimize_section(self.s3, 2)

        self.assertTrue(self.s2.is_scheduled())
        self.assertTrue(self.s3.is_scheduled())
        self.assertEqual([a["action"] for a in actions], ["schedule"])
        self.assertEqual(
            [a["action"] for a in self.manipulator.history],
            ["schedule", "schedule"])
        self.assertEqual(self.manipulator.history[0]["section"], self.s2)

    def test_failed_second_eviction_rolls_back_the_first(self):
        """Section 2 needs two roomslots, so scheduling it evicts sections 1
        and 4. Section 1 can be placed elsewhere, but section 4's teacher is
        only free in the timeslot it already occupies, so the attempt fails.
        Everything, including the work done to relocate section 1, is undone
        and the original assignments and history survive."""
        teacher = data_model.AS_Teacher([self.schedule.timeslots[2]], 5)
        self.schedule.teachers[5] = teacher
        s4 = data_model.AS_ClassSection([teacher], 0.83, 20, 0, [], 4, 0)
        self.schedule.class_sections[4] = s4
        self.manipulator = ScheduleManipulator(
            self.schedule, constraint_names=[],
            scorer_names_and_weights=SCORER_WEIGHTS)
        self.optimizer = SearchOptimizer(self.manipulator)
        self.assertTrue(self.manipulator.schedule_section(
            self.s1, self.rooms[1]))
        self.assertTrue(self.manipulator.schedule_section(s4, self.rooms[2]))
        history_before = list(self.manipulator.history)

        actions = self.optimizer.optimize_section(self.s2, 3)

        self.assertEqual(actions, [])
        self.assertFalse(self.s2.is_scheduled())
        self.assertIs(self.s1.assigned_roomslots[0], self.rooms[1])
        self.assertIs(s4.assigned_roomslots[0], self.rooms[2])
        self.assertEqual(self.manipulator.history, history_before)

    def test_moves_scheduled_section_when_it_improves_the_score(self):
        """With a scorer that prefers a better-sized room, an already
        scheduled section is moved, and the move is returned."""
        manipulator = ScheduleManipulator(
            self.schedule, constraint_names=[],
            scorer_names_and_weights={"RoomSizeMismatchScorer": 100.0})
        optimizer = SearchOptimizer(manipulator)
        self.assertTrue(manipulator.schedule_section(self.s1, self.rooms[0]))
        score_before = manipulator.scorer.score_schedule()

        actions = optimizer.optimize_section(self.s1, 1)

        self.assertEqual([a["action"] for a in actions], ["move"])
        self.assertEqual(self.s1.assigned_roomslots[0].room.name, "10-250")
        self.assertGreater(manipulator.scorer.score_schedule(), score_before)
        self.assertEqual([a["action"] for a in manipulator.history],
                         ["schedule", "move"])

    def test_search_leaves_consistent_scores(self):
        """After a search, the incrementally updated score equals a fresh
        one."""
        self.assertTrue(self.manipulator.schedule_section(
            self.s2, self.rooms[1]))
        self.optimizer.optimize_section(self.s3, 2)
        incremental = self.manipulator.scorer.score_schedule()

        fresh = ScheduleManipulator(
            self.schedule, constraint_names=[],
            scorer_names_and_weights=SCORER_WEIGHTS)

        self.assertAlmostEqual(
            incremental, fresh.scorer.score_schedule())

    def test_revert_undoes_exactly_n_actions(self):
        """revert(n) undoes the last n history records and no more."""
        self.assertTrue(self.manipulator.schedule_section(
            self.s1, self.rooms[0]))
        self.assertTrue(self.manipulator.schedule_section(
            self.s3, self.rooms[4]))
        self.assertTrue(self.manipulator.schedule_section(
            self.s2, self.rooms[1]))

        self.optimizer.revert(2)

        self.assertEqual(len(self.manipulator.history), 1)
        self.assertTrue(self.s1.is_scheduled())
        self.assertFalse(self.s3.is_scheduled())
        self.assertFalse(self.s2.is_scheduled())

    def test_revert_zero_is_a_no_op(self):
        """revert(0) changes nothing."""
        self.assertTrue(self.manipulator.schedule_section(
            self.s1, self.rooms[0]))
        self.optimizer.revert(0)
        self.assertTrue(self.s1.is_scheduled())
        self.assertEqual(len(self.manipulator.history), 1)
