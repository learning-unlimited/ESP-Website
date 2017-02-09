import unittest
import traceback
import datetime

from esp.program.controllers.autoscheduler import \
        consistency_checks, testutils, models
from esp.program.controllers.autoscheduler.exceptions import ConsistencyError


class ConsistencyCheckerTest(unittest.TestCase):
    def test_good_schedule(self):
        checker = consistency_checks.ConsistencyChecker()
        sched = testutils.create_test_schedule_1()
        try:
            checker.run_all_consistency_checks(sched)
        except ConsistencyError:
            self.fail("Unexpectedly failed consistency check with error: \n{}"
                      .format(traceback.format_exc()))

        sched = testutils.create_test_schedule_2()
        try:
            checker.run_all_consistency_checks(sched)
        except ConsistencyError:
            self.fail("Unexpectedly failed consistency check with error: \n{}"
                      .format(traceback.format_exc()))

    def test_timeslot_inconsistency(self):
        checker = consistency_checks.ConsistencyChecker()
        sched = testutils.create_test_schedule_1()
        try:
            checker.check_timeslot_consistency(sched)
        except ConsistencyError:
            self.fail(
                    "Unexpectedly failed timeslot consistency with error: \n{}"
                    .format(traceback.format_exc()))

        sched.timeslots.reverse()
        with self.assertRaises(ConsistencyError):
            # Not sorted
            checker.check_timeslot_consistency(sched)

        sched.timeslots.reverse()
        sched.timeslots.append(sched.timeslots[-1])

        with self.assertRaises(ConsistencyError):
            # Duplicate timeslot
            checker.check_timeslot_consistency(sched)

        sched.timeslots = sched.timeslots[:-1]

        sched.timeslots[-1].start = sched.timeslots[-2].start

        with self.assertRaises(ConsistencyError):
            # overlapping timeslots
            checker.check_timeslot_consistency(sched)

    def test_timeslot_list_dict_consistency(self):
        checker = consistency_checks.ConsistencyChecker()
        sched = testutils.create_test_schedule_1()
        try:
            checker.check_timeslots_list_and_dict_consistency(sched)
        except ConsistencyError:
            self.fail(
                    "Unexpectedly failed timeslot list/dict consistency " +
                    "with error: \n{}"
                    .format(traceback.format_exc()))

        last_timeslot = sched.timeslots[-1]
        timeslot_key = (last_timeslot.start, last_timeslot.end)
        sched.timeslots = sched.timeslots[:-1]

        with self.assertRaises(ConsistencyError):
            # List missing an item
            checker.check_timeslots_list_and_dict_consistency(sched)

        sched.timeslots.append(last_timeslot)
        del sched.timeslot_dict[timeslot_key]

        with self.assertRaises(ConsistencyError):
            # Dict missing an item
            checker.check_timeslots_list_and_dict_consistency(sched)

        sched.timeslot_dict["bad key"] = last_timeslot

    def test_sorting_consistency(self):
        checker = consistency_checks.ConsistencyChecker()
        sched = testutils.create_test_schedule_2()
        try:
            checker.check_sorting_consistency(sched)
        except ConsistencyError:
            self.fail(
                    "Unexpectedly failed sorting consistency with error: \n{}"
                    .format(traceback.format_exc()))

        sched.class_sections[2].assigned_roomslots.reverse()
        with self.assertRaises(ConsistencyError):
            # Section roomslots are out of order
            checker.check_sorting_consistency(sched)
        sched.class_sections[2].assigned_roomslots.reverse()

        sched.classrooms["26-100"].availability.reverse()
        with self.assertRaises(ConsistencyError):
            # Classroom roomslots are out of order
            checker.check_sorting_consistency(sched)
        sched.classrooms["26-100"].availability.reverse()

        sched.teachers[1].availability.reverse()
        with self.assertRaises(ConsistencyError):
            # Classroom roomslots are out of order
            checker.check_sorting_consistency(sched)
        sched.teachers[1].availability.reverse()

    def test_roomslots_consistency(self):
        checker = consistency_checks.ConsistencyChecker()
        sched = testutils.create_test_schedule_2()
        try:
            checker.check_roomslots_consistency(sched)
        except ConsistencyError:
            self.fail(
                "Unexpectedly failed roomslots consistency with error: \n{}"
                .format(traceback.format_exc()))

        sched.classrooms["10-250"].availability.insert(
            0, sched.classrooms["26-100"].availability[2])
        with self.assertRaises(ConsistencyError):
            # Room and roomslot were inconsistent
            checker.check_roomslots_consistency(sched)
        sched.classrooms["10-250"].availability.remove(
            sched.classrooms["26-100"].availability[2])

        sched.class_sections[1].assigned_roomslots.append(
            sched.class_sections[2].assigned_roomslots[0])
        with self.assertRaises(ConsistencyError):
            # Section and roomslot were inconsistent
            checker.check_roomslots_consistency(sched)
        sched.class_sections[1].assigned_roomslots = []

        roomslot = list(sched.timeslots[0].associated_roomslots)[0]
        sched.timeslots[1].associated_roomslots.add(roomslot)
        with self.assertRaises(ConsistencyError):
            # Timeslot and roomslot were inconsistent
            checker.check_roomslots_consistency(sched)
        sched.timeslots[1].associated_roomslots.remove(roomslot)

        new_timeslot = models.AS_Timeslot(
                datetime.datetime(2017, 02, 02, 16, 05),
                datetime.datetime(2017, 02, 02, 16, 55),
                7)
        new_roomslot = models.AS_RoomSlot(new_timeslot, None)
        # This should be okay, because we made a "rogue" roomslot but it's
        # orphaned.
        try:
            checker.check_roomslots_consistency(sched)
        except ConsistencyError:
            self.fail(
                "Unexpectedly failed roomslots consistency with error: \n{}"
                .format(traceback.format_exc()))

        sched.class_sections[1].assigned_roomslots.append(new_roomslot)
        new_roomslot.assigned_section = sched.class_sections[1]
        with self.assertRaises(ConsistencyError):
            # Rogue section assigned to a timeslot
            checker.check_roomslots_consistency(sched)
        sched.class_sections[1].assigned_roomslots = []
        new_roomslot.assigned_section = None

        # But if it's actually assigned to stuff that's bad.
        new_roomslot.room = sched.classrooms["10-250"]
        sched.classrooms["10-250"].availability.append(new_roomslot)
        with self.assertRaises(ConsistencyError):
            # Timeslot is not registered
            checker.check_roomslots_consistency(sched)

        new_roomslot.timeslot = sched.timeslots[2]
        with self.assertRaises(ConsistencyError):
            # Timeslot doesn't have roomslot in associated roomslots
            checker.check_roomslots_consistency(sched)

        sched.timeslots[2].associated_roomslots.add(new_roomslot)
        new_classroom = models.AS_Classroom("1-190", [])
        new_roomslot.room = new_classroom
        new_classroom.availability.append(new_roomslot)
        sched.classrooms["10-250"].availability.remove(new_roomslot)
        with self.assertRaises(ConsistencyError):
            # Classroom isn't registered
            checker.check_roomslots_consistency(sched)

        new_roomslot.room = sched.classrooms["10-250"]
        with self.assertRaises(ConsistencyError):
            # Classroom doesn't have roomslot in availability
            checker.check_roomslots_consistency(sched)

        sched.classrooms["10-250"].availability.append(new_roomslot)
        new_section = models.AS_ClassSection(
                [sched.teachers[1]], 0.83, 20, 0, [new_roomslot], 3)
        new_roomslot.assigned_section = new_section
        with self.assertRaises(ConsistencyError):
            # Section isn't registered
            checker.check_roomslots_consistency(sched)

        new_roomslot.assigned_section = sched.class_sections[1]
        with self.assertRaises(ConsistencyError):
            # Section doesn't have roomslot assigned
            checker.check_roomslots_consistency(sched)

        sched.class_sections[1].assigned_roomslots.append(new_roomslot)
        # By a very circuitous route, we scheduled the first class in 10-250 at
        # a new available time.
        try:
            checker.check_roomslots_consistency(sched)
        except ConsistencyError:
            self.fail(
                "Unexpectedly failed roomslots consistency with error: \n{}"
                .format(traceback.format_exc()))


if __name__ == "__main__":
    unittest.main()
