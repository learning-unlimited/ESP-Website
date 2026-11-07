"""Tests for ScheduleManipulator: scheduling actions, undo, and the
(de)serialisation used to save and replay a scheduling history."""

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
    """The standard test schedule plus section 3, which has the same
    duration as section 1 (so the two can be swapped) and its own teacher.

    26-100 is available in all 6 timeslots (ids 1-6). Section 1 and 3 each
    need one roomslot; section 2 needs two. Teacher 2 is only available in
    timeslots 1-3 and teacher 3 in timeslots 2-6, so section 2 can only start
    in 26-100 at index 1 (timeslots 2 and 3)."""
    schedule = testutils.create_test_schedule_1()
    teacher = data_model.AS_Teacher(list(schedule.timeslots), 4)
    schedule.teachers[4] = teacher
    schedule.class_sections[3] = data_model.AS_ClassSection(
        [teacher], 0.83, 20, 0, [], 3, 0)
    return schedule


def placement(section):
    """(room name, timeslot ids) a section is currently assigned to."""
    slots = section.assigned_roomslots
    if not slots:
        return None
    return (slots[0].room.name, [r.timeslot.id for r in slots])


class ManipulatorTestCase(unittest.TestCase):
    """Base class: a schedule, a manipulator and shortcuts to sections and roomslots."""
    def setUp(self):
        """Create a schedule, a manipulator and section/roomslot shortcuts."""
        self.schedule = make_schedule()
        self.manipulator = ScheduleManipulator(
            self.schedule, constraint_names=[],
            scorer_names_and_weights=SCORER_WEIGHTS)
        self.rooms = self.schedule.classrooms["26-100"].availability
        self.s1 = self.schedule.class_sections[1]
        self.s2 = self.schedule.class_sections[2]
        self.s3 = self.schedule.class_sections[3]

    def actions(self):
        """Names of the actions in the manipulator's history."""
        return [a["action"] for a in self.manipulator.history]

    def state(self):
        """Placement of every section in the schedule."""
        return {i: placement(s)
                for i, s in self.schedule.class_sections.items()}


class NoConstraints:
    """Stands in for the constraints, so a test can exercise the checks that
    the manipulator makes itself. (PreconditionConstraint repeats most of
    them, so they are otherwise hidden.)"""
    def check_schedule_section(self, *args):
        """Report no constraint violations."""
        return None

    check_move_section = check_unschedule_section = \
        check_swap_sections = check_schedule_section


class ManipulatorPreconditionTest(ManipulatorTestCase):
    """The checks ScheduleManipulator makes itself, without constraints."""
    def setUp(self):
        """Replace the constraints so only the manipulator's own checks run."""
        super().setUp()
        self.manipulator.constraints = NoConstraints()

    def test_scheduled_section_cannot_be_scheduled_again(self):
        """A scheduled section is rejected and left where it was."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.assertFalse(self.manipulator.schedule_section(
            self.s1, self.rooms[1]))
        self.assertEqual(placement(self.s1), ("26-100", [1]))
        self.assertEqual(self.actions(), ["schedule"])

    def test_unscheduled_section_cannot_be_moved(self):
        """An unscheduled section can't be moved."""
        self.assertFalse(self.manipulator.move_section(
            self.s1, self.rooms[0]))
        self.assertEqual(self.manipulator.history, [])

    def test_unscheduled_section_cannot_be_unscheduled(self):
        """An unscheduled section can't be unscheduled."""
        self.assertFalse(self.manipulator.unschedule_section(self.s1))
        self.assertEqual(self.manipulator.history, [])

    def test_unscheduled_section_cannot_be_swapped(self):
        """A swap needs both sections to be scheduled."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.assertFalse(self.manipulator.swap_sections(self.s1, self.s3))
        self.assertFalse(self.manipulator.swap_sections(self.s3, self.s1))
        self.assertEqual(self.actions(), ["schedule"])

    def test_sections_of_different_duration_cannot_be_swapped(self):
        """A swap needs both sections to have the same duration."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.schedule_section(self.s2, self.rooms[1])
        before = self.state()
        self.assertFalse(self.manipulator.swap_sections(self.s1, self.s2))
        self.assertEqual(self.state(), before)
        self.assertEqual(self.actions(), ["schedule", "schedule"])


class ScheduleSectionTest(ManipulatorTestCase):
    """ScheduleManipulator.schedule_section."""
    def test_schedules_section_and_records_history(self):
        """Scheduling assigns the roomslot and records a schedule action."""
        self.assertTrue(self.manipulator.schedule_section(
            self.s1, self.rooms[0]))
        self.assertEqual(placement(self.s1), ("26-100", [1]))
        self.assertEqual(self.manipulator.history, [{
            "action": "schedule",
            "section": self.s1,
            "start_roomslot": self.rooms[0],
        }])

    def test_multi_hour_section_uses_consecutive_roomslots(self):
        """A two-hour section takes two consecutive roomslots."""
        self.assertTrue(self.manipulator.schedule_section(
            self.s2, self.rooms[1]))
        self.assertEqual(placement(self.s2), ("26-100", [2, 3]))

    def test_already_scheduled_section_is_rejected(self):
        """Scheduling an already scheduled section fails without changes."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.assertFalse(self.manipulator.schedule_section(
            self.s1, self.rooms[1]))
        self.assertEqual(placement(self.s1), ("26-100", [1]))
        self.assertEqual(len(self.manipulator.history), 1)

    def test_occupied_roomslot_is_rejected(self):
        """Scheduling into an occupied roomslot fails without changes."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.assertFalse(self.manipulator.schedule_section(
            self.s3, self.rooms[0]))
        self.assertFalse(self.s3.is_scheduled())
        self.assertEqual(self.actions(), ["schedule"])

    def test_unavailable_teacher_is_rejected(self):
        """Scheduling at a time when the teacher is unavailable fails."""
        # Teacher 2 is not available in timeslot 4, which this would use.
        self.assertFalse(self.manipulator.schedule_section(
            self.s2, self.rooms[2]))
        self.assertFalse(self.s2.is_scheduled())
        self.assertEqual(self.manipulator.history, [])

    def test_force_skips_constraint_checks(self):
        """force=True schedules despite constraint violations."""
        self.assertTrue(self.manipulator.schedule_section(
            self.s2, self.rooms[2], force=True))
        self.assertEqual(placement(self.s2), ("26-100", [3, 4]))
        self.assertEqual(self.actions(), ["schedule"])


class MoveSectionTest(ManipulatorTestCase):
    """ScheduleManipulator.move_section."""
    def test_moves_section_and_records_previous_roomslot(self):
        """Moving frees the old roomslot and records the previous one."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.assertTrue(self.manipulator.move_section(
            self.s1, self.rooms[5]))
        self.assertEqual(placement(self.s1), ("26-100", [6]))
        self.assertIsNone(self.rooms[0].assigned_section)
        self.assertIs(self.rooms[5].assigned_section, self.s1)
        self.assertEqual(self.manipulator.history[-1], {
            "action": "move",
            "section": self.s1,
            "start_roomslot": self.rooms[5],
            "prev_start_roomslot": self.rooms[0],
        })

    def test_unscheduled_section_cannot_be_moved(self):
        """An unscheduled section can't be moved."""
        self.assertFalse(self.manipulator.move_section(
            self.s1, self.rooms[0]))
        self.assertFalse(self.s1.is_scheduled())
        self.assertEqual(self.manipulator.history, [])

    def test_move_into_occupied_roomslot_is_rejected(self):
        """Moving into an occupied roomslot fails without changes."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.schedule_section(self.s3, self.rooms[1])
        self.assertFalse(self.manipulator.move_section(
            self.s1, self.rooms[1]))
        self.assertEqual(placement(self.s1), ("26-100", [1]))
        self.assertEqual(placement(self.s3), ("26-100", [2]))
        self.assertEqual(self.actions(), ["schedule", "schedule"])


class UnscheduleSectionTest(ManipulatorTestCase):
    """ScheduleManipulator.unschedule_section."""
    def test_unschedules_section_and_frees_roomslot(self):
        """Unscheduling frees the roomslot and records a history item."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.assertTrue(self.manipulator.unschedule_section(self.s1))
        self.assertFalse(self.s1.is_scheduled())
        self.assertIsNone(self.rooms[0].assigned_section)
        self.assertEqual(self.manipulator.history[-1], {
            "action": "unschedule",
            "section": self.s1,
            "prev_start_roomslot": self.rooms[0],
        })

    def test_unscheduled_section_cannot_be_unscheduled(self):
        """An unscheduled section can't be unscheduled."""
        self.assertFalse(self.manipulator.unschedule_section(self.s1))
        self.assertEqual(self.manipulator.history, [])


class UndoTest(ManipulatorTestCase):
    """ScheduleManipulator.undo."""
    def test_nothing_to_undo(self):
        """Undo returns False when the history is empty."""
        self.assertFalse(self.manipulator.undo())
        self.assertEqual(self.manipulator.history, [])

    def test_undo_schedule(self):
        """Undoing a schedule unschedules the section."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.assertTrue(self.manipulator.undo())
        self.assertFalse(self.s1.is_scheduled())
        self.assertEqual(self.manipulator.history, [])

    def test_undo_move(self):
        """Undoing a move puts the section back."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.move_section(self.s1, self.rooms[4])
        self.assertTrue(self.manipulator.undo())
        self.assertEqual(placement(self.s1), ("26-100", [1]))
        self.assertEqual(self.actions(), ["schedule"])

    def test_undo_unschedule(self):
        """Undoing an unschedule puts the section back."""
        self.manipulator.schedule_section(self.s2, self.rooms[1])
        self.manipulator.unschedule_section(self.s2)
        self.assertTrue(self.manipulator.undo())
        self.assertEqual(placement(self.s2), ("26-100", [2, 3]))
        self.assertEqual(self.actions(), ["schedule"])

    def test_undo_walks_back_through_history(self):
        """Repeated undo returns to the initial state, one step at a time."""
        initial = self.state()
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.schedule_section(self.s3, self.rooms[1])
        self.manipulator.move_section(self.s1, self.rooms[4])
        self.manipulator.unschedule_section(self.s3)
        self.assertEqual(len(self.manipulator.history), 4)
        for remaining in (3, 2, 1, 0):
            self.assertTrue(self.manipulator.undo())
            self.assertEqual(len(self.manipulator.history), remaining)
        self.assertFalse(self.manipulator.undo())
        self.assertEqual(self.state(), initial)

    def test_undo_restores_scores(self):
        """Undoing every action restores the original scores."""
        initial = self.manipulator.scorer.get_all_score_schedule()
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.schedule_section(self.s3, self.rooms[1])
        scheduled = self.manipulator.scorer.get_all_score_schedule()
        self.assertNotEqual(scheduled, initial)
        self.manipulator.move_section(self.s1, self.rooms[4])
        self.manipulator.unschedule_section(self.s3)
        while self.manipulator.undo():
            pass
        self.assertEqual(
            self.manipulator.scorer.get_all_score_schedule(), initial)


class RejectEverything:
    """Stands in for the constraints and reports a violation for every
    action."""
    def check_schedule_section(self, *args):
        """Report a violation."""
        return "violation"

    check_move_section = check_unschedule_section = \
        check_swap_sections = check_schedule_section


class ForceTest(ManipulatorTestCase):
    """force=True skips the constraint checks of every action."""

    def setUp(self):
        """Schedule two sections, then make the constraints reject all."""
        super().setUp()
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.schedule_section(self.s3, self.rooms[1])
        self.manipulator.constraints = RejectEverything()

    def test_move_section(self):
        """A violating move fails, but succeeds with force=True."""
        self.assertFalse(self.manipulator.move_section(
            self.s1, self.rooms[4]))
        self.assertEqual(placement(self.s1), ("26-100", [1]))
        self.assertTrue(self.manipulator.move_section(
            self.s1, self.rooms[4], force=True))
        self.assertEqual(placement(self.s1), ("26-100", [5]))
        self.assertEqual(self.actions(), ["schedule", "schedule", "move"])

    def test_unschedule_section(self):
        """A violating unschedule fails, but succeeds with force=True."""
        self.assertFalse(self.manipulator.unschedule_section(self.s1))
        self.assertTrue(self.s1.is_scheduled())
        self.assertTrue(self.manipulator.unschedule_section(
            self.s1, force=True))
        self.assertFalse(self.s1.is_scheduled())
        self.assertEqual(
            self.actions(), ["schedule", "schedule", "unschedule"])

    def test_swap_sections(self):
        """A violating swap fails, but succeeds with force=True."""
        self.assertFalse(self.manipulator.swap_sections(self.s1, self.s3))
        self.assertEqual(placement(self.s1), ("26-100", [1]))
        self.assertTrue(self.manipulator.swap_sections(
            self.s1, self.s3, force=True))
        self.assertEqual(placement(self.s1), ("26-100", [2]))
        self.assertEqual(placement(self.s3), ("26-100", [1]))
        self.assertEqual(self.actions(), ["schedule", "schedule", "swap"])


class PerformActionTest(ManipulatorTestCase):
    """ScheduleManipulator.perform_action."""
    def test_dispatches_each_action_type(self):
        """perform_action handles schedule, move and unschedule records."""
        self.assertTrue(self.manipulator.perform_action({
            "action": "schedule", "section": self.s1,
            "start_roomslot": self.rooms[0]}))
        self.assertTrue(self.manipulator.perform_action({
            "action": "move", "section": self.s1,
            "start_roomslot": self.rooms[3]}))
        self.assertEqual(placement(self.s1), ("26-100", [4]))
        self.assertTrue(self.manipulator.perform_action({
            "action": "unschedule", "section": self.s1}))
        self.assertFalse(self.s1.is_scheduled())
        self.assertEqual(self.actions(), ["schedule", "move", "unschedule"])

    def test_returns_false_when_action_is_not_allowed(self):
        """perform_action reports a disallowed action."""
        self.assertFalse(self.manipulator.perform_action({
            "action": "move", "section": self.s1,
            "start_roomslot": self.rooms[0]}))
        self.assertEqual(self.manipulator.history, [])


class JsonifyActionTest(ManipulatorTestCase):
    """Turning history records into JSON-like dicts and back."""
    def setUp(self):
        """Build a history with each action type, plus a swap record."""
        super().setUp()
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.schedule_section(self.s3, self.rooms[1])
        self.manipulator.move_section(self.s1, self.rooms[4])
        self.manipulator.unschedule_section(self.s3)
        self.swap = {
            "action": "swap",
            "sections": (self.s1, self.s3),
            "original_roomslots": (self.rooms[4], self.rooms[1]),
        }

    @staticmethod
    def times(timeslot_id):
        """The JSON form of timeslot start and end times."""
        # Timeslot i runs 10+(i-1):05 to 10+(i-1):55 on 2017-02-02.
        hour = 9 + timeslot_id
        return [[2017, 2, 2, hour, 5, 0], [2017, 2, 2, hour, 55, 0]]

    def test_schedule_action_format(self):
        """Format of a jsonified schedule action."""
        result = self.manipulator.jsonify_action(self.manipulator.history[0])
        self.assertEqual(result, {
            "action": "schedule",
            "section": 1,
            "start_roomslot": [self.times(1), "26-100"],
        })

    def test_move_action_format(self):
        """Format of a jsonified move action."""
        result = self.manipulator.jsonify_action(self.manipulator.history[2])
        self.assertEqual(result, {
            "action": "move",
            "section": 1,
            "start_roomslot": [self.times(5), "26-100"],
            "prev_start_roomslot": [self.times(1), "26-100"],
        })

    def test_unschedule_action_format(self):
        """Format of a jsonified unschedule action."""
        result = self.manipulator.jsonify_action(self.manipulator.history[3])
        self.assertEqual(result, {
            "action": "unschedule",
            "section": 3,
            "prev_start_roomslot": [self.times(2), "26-100"],
        })

    def test_swap_action_format(self):
        """Format of a jsonified swap action."""
        result = self.manipulator.jsonify_action(self.swap)
        self.assertEqual(result, {
            "action": "swap",
            "sections": [1, 3],
            "original_roomslots": [[self.times(5), "26-100"],
                                   [self.times(2), "26-100"]],
        })

    def test_every_action_survives_a_json_round_trip(self):
        """Each action type is restored by dumping to JSON and loading it."""
        for action in self.manipulator.history + [self.swap]:
            with self.subTest(action=action["action"]):
                stored = json.loads(json.dumps(
                    self.manipulator.jsonify_action(action)))
                restored = self.manipulator.dejsonify_action(stored)
                self.assertEqual(restored["action"], action["action"])
                for key in ("section", "start_roomslot",
                            "prev_start_roomslot"):
                    self.assertIs(restored.get(key), action.get(key))
                for key in ("sections", "original_roomslots"):
                    if key in action:
                        self.assertEqual(list(restored[key]),
                                         list(action[key]))
                    else:
                        self.assertNotIn(key, restored)

    def test_jsonify_history_covers_whole_history(self):
        """jsonify_history converts every record in the history."""
        result = self.manipulator.jsonify_history()
        self.assertEqual([a["action"] for a in result],
                         ["schedule", "schedule", "move", "unschedule"])


class LoadHistoryTest(ManipulatorTestCase):
    """Replaying a saved history with ScheduleManipulator.load_history."""
    def fresh_manipulator(self):
        """A new schedule and manipulator, to replay a history on."""
        schedule = make_schedule()
        return schedule, ScheduleManipulator(
            schedule, constraint_names=[],
            scorer_names_and_weights=SCORER_WEIGHTS)

    def test_replaying_saved_history_reproduces_the_schedule(self):
        """Replaying a saved history gives the same schedule and scores."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        self.manipulator.schedule_section(self.s3, self.rooms[3])
        self.manipulator.move_section(self.s1, self.rooms[4])
        self.manipulator.schedule_section(self.s2, self.rooms[1])
        self.manipulator.unschedule_section(self.s3)
        # History is stored as JSON, so go through a real dump/load.
        saved = json.loads(json.dumps(self.manipulator.jsonify_history()))

        schedule, replay = self.fresh_manipulator()
        self.assertTrue(replay.load_history(saved))

        self.assertEqual(
            {i: placement(s) for i, s in schedule.class_sections.items()},
            self.state())
        self.assertEqual(
            [a["action"] for a in replay.history],
            ["schedule", "schedule", "move", "schedule", "unschedule"])
        self.assertEqual(replay.scorer.get_all_score_schedule(),
                         self.manipulator.scorer.get_all_score_schedule())

    def test_empty_history_is_a_no_op(self):
        """An empty history loads successfully and changes nothing."""
        schedule, replay = self.fresh_manipulator()
        self.assertTrue(replay.load_history([]))
        self.assertEqual(replay.history, [])

    def test_stops_at_first_action_that_cannot_be_performed(self):
        """load_history returns False and stops at a disallowed action."""
        self.manipulator.schedule_section(self.s1, self.rooms[0])
        saved = self.manipulator.jsonify_history()
        # Moving a section that has not been scheduled is not allowed.
        bad_move = {"action": "move", "section": 3,
                    "start_roomslot": saved[0]["start_roomslot"],
                    "prev_start_roomslot": saved[0]["start_roomslot"]}

        schedule, replay = self.fresh_manipulator()
        self.assertFalse(replay.load_history([bad_move] + saved))
        self.assertFalse(schedule.class_sections[1].is_scheduled())
        self.assertEqual(replay.history, [])


if __name__ == "__main__":
    unittest.main()
