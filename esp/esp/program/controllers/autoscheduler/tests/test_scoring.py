import unittest
from esp.program.controllers.autoscheduler import \
        scoring, testutils


class ScoringTest(unittest.TestCase):
    def setUp(self):
        self.schedule = testutils.create_test_schedule_2()
        scorer_names_and_weights = {
            "AdminDistributionScorer": 70.0,
            "CategoryBalanceScorer": 10.0,
            "LunchStudentClassHoursScorer": 20.0,
            "HungryTeacherScorer": 70.0,
            "NumSectionsScorer": 100.0,
            "NumSubjectsScorer": 60.0,
            "NumTeachersScorer": 50.0,
            "ResourceCriteriaScorer": 40.0,
            "ResourceMatchingScorer": 20.0,
            "ResourceValueMatchingScorer": 20.0,
            "RoomConsecutivityScorer": 10.0,
            "RoomSizeMismatchScorer": 30.0,
            "StudentClassHoursScorer": 50.0,
            "TeachersWhoLikeRunningScorer": 10.0
        }
        self.scorer = scoring.CompositeScorer(
            scorer_names_and_weights, self.schedule)

    def test_schedule_unschedule(self):
        """Scheduling and unscheduling should do nothing."""
        scores = self.scorer.get_all_score_schedule()

        section = self.schedule.class_sections[1]
        roomslot = self.schedule.classrooms["26-100"].availability[0]
        self.scorer.update_schedule_section(section, roomslot)
        self.schedule_section(section, roomslot)
        self.scorer.update_unschedule_section(section)
        self.unschedule_section(section)
        self.assertEqual(self.scorer.get_all_score_schedule(), scores)

        section = self.schedule.class_sections[2]
        roomslot = section.assigned_roomslots[0]
        self.scorer.update_unschedule_section(section)
        self.unschedule_section(section)
        self.scorer.update_schedule_section(section, roomslot)
        self.unschedule_section(section)
        self.assertEqual(self.scorer.get_all_score_schedule(), scores)

    def test_schedule_move(self):
        """Scheduling and moving should do the same as scheduling."""

        section = self.schedule.class_sections[1]
        roomslot = self.schedule.classrooms["26-100"].availability[0]
        self.scorer.update_schedule_section(section, roomslot)
        self.schedule_section(section, roomslot)
        scores = self.scorer.get_all_score_schedule()
        self.scorer.update_unschedule_section(section)
        self.unschedule_section(section)

        roomslot2 = self.schedule.classrooms["10-250"].availability[0]
        self.scorer.update_schedule_section(section, roomslot2)
        self.schedule_section(section, roomslot2)
        self.scorer.update_move_section(section, roomslot)
        self.unschedule_section(section)
        self.schedule_section(section, roomslot)
        self.assertEqual(self.scorer.get_all_score_schedule(), scores)

    def schedule_section(self, section, start_roomslot):
        roomslots_to_use = start_roomslot.room.get_roomslots_by_duration(
                start_roomslot, section.duration)
        section.assign_roomslots(roomslots_to_use)

    def unschedule_section(self, section):
        section.clear_roomslots()


if __name__ == "__main__":
    unittest.main()
