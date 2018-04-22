import datetime
import traceback
import unittest

from esp.program.controllers.autoscheduler import \
        consistency_checks, testutils, data_model
from esp.program.controllers.autoscheduler.consistency_checks import \
        ConsistencyError


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

        sched = testutils.create_test_schedule_3()
        try:
            checker.run_all_consistency_checks(sched)
        except ConsistencyError:
            self.fail("Unexpectedly failed consistency check with error: \n{}"
                      .format(traceback.format_exc()))

    def test_availability_dict_consistency(self):
        checker = consistency_checks.ConsistencyChecker()
        sched = testutils.create_test_schedule_1()
        try:
            checker.check_availability_dict_consistency(sched)
        except ConsistencyError:
            self.fail((
                "Unexpectedly failed availability dict consistency "
                "with error: \n{}").format(traceback.format_exc()))

        room = sched.classrooms["10-250"]
        roomslot = room.availability[0]
        timeslot = roomslot.timeslot
        del room.availability_dict[
                (timeslot.start, timeslot.end)]
        with self.assertRaises(ConsistencyError):
            # Extra value in availability list
            checker.check_availability_dict_consistency(sched)

        room.availability_dict[(timeslot.end, timeslot.start)] = \
            roomslot
        with self.assertRaises(ConsistencyError):
            # Key mismatch
            checker.check_availability_dict_consistency(sched)

        del room.availability_dict[
                (timeslot.end, timeslot.start)]
        room.availability_dict[(timeslot.start, timeslot.end)] = \
            roomslot

        try:
            checker.check_availability_dict_consistency(sched)
        except ConsistencyError:
            self.fail((
                "Unexpectedly failed availability dict consistency "
                "with error: \n{}").format(traceback.format_exc()))

        room.availability.pop()
        with self.assertRaises(ConsistencyError):
            # Missing item in availability list
            checker.check_availability_dict_consistency(sched)

    def test_lunch_consistency(self):
        checker = consistency_checks.ConsistencyChecker()
        sched = testutils.create_test_schedule_3()
        try:
            checker.check_lunch_consistency(sched)
        except ConsistencyError:
            self.fail((
                "Unexpectedly failed lunch consistency "
                "with error: \n{}").format(traceback.format_exc()))

        day = next(sched.lunch_timeslots.iterkeys())
        sched.lunch_timeslots[day].reverse()
        with self.assertRaises(ConsistencyError):
            # Lunch timeslots our of order
            checker.check_lunch_consistency(sched)
        sched.lunch_timeslots[day].reverse()

        sched.lunch_timeslots[day].append(sched.lunch_timeslots[day][-1])
        with self.assertRaises(ConsistencyError):
            # Duplicate
            checker.check_lunch_consistency(sched)
        sched.lunch_timeslots[day].pop()

        sched.lunch_timeslots[day].append(data_model.AS_Timeslot(
            datetime.datetime(2017, 2, 2, 14, 5),
            datetime.datetime(2017, 2, 2, 14, 55),
            event_id=5))
        with self.assertRaises(ConsistencyError):
            # Unregistered timeslot
            checker.check_lunch_consistency(sched)
        sched.lunch_timeslots[day].pop()

        sched.lunch_timeslots[(2017, 2, 4)] = sched.lunch_timeslots[day]
        with self.assertRaises(ConsistencyError):
            # Wrong day
            checker.check_lunch_consistency(sched)

    def test_resource_dict_consistency(self):
        checker = consistency_checks.ConsistencyChecker()
        sched = testutils.create_test_schedule_1()
        try:
            checker.check_resource_dict_consistency(sched)
        except ConsistencyError:
            self.fail((
                "Unexpectedly failed resource dict consistency "
                "with error: \n{}").format(traceback.format_exc()))

        requests = sched.class_sections[1].resource_requests
        requests["Foo"] = requests["Projector"]
        with self.assertRaises(ConsistencyError):
            # Wrong key
            checker.check_resource_dict_consistency(sched)
        del requests["Foo"]

        furnishings = sched.classrooms["10-250"].furnishings
        furnishings["Foo"] = furnishings["Projector"]
        with self.assertRaises(ConsistencyError):
            # Wrong key
            checker.check_resource_dict_consistency(sched)

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

        new_timeslot = data_model.AS_Timeslot(
                datetime.datetime(2017, 2, 2, 16, 5),
                datetime.datetime(2017, 2, 2, 16, 55),
                7)
        new_roomslot = data_model.AS_RoomSlot(new_timeslot, None)
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
        new_classroom = data_model.AS_Classroom("1-190", 20, [])
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
        new_section = data_model.AS_ClassSection(
                [sched.teachers[1]], 0.83, 20, 0, [new_roomslot], 3, 0)
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

    def test_roomslot_next_and_index_consistency(self):
        checker = consistency_checks.ConsistencyChecker()
        sched = testutils.create_test_schedule_1()
        room = sched.classrooms["10-250"]
        room.load_roomslot_caches()
        try:
            checker.check_roomslot_next_and_index_consistency(sched)
        except ConsistencyError:
            self.fail((
                        "Unexpectedly failed roomslot next/index "
                        "consistency with error: \n{}"
                    ).format(traceback.format_exc()))

        room.load_roomslot_caches()
        last_roomslot = room.availability.pop()
        with self.assertRaises(ConsistencyError):
            # Last roomslot now points at nonexistent roomslot
            checker.check_roomslot_next_and_index_consistency(sched)
        room.availability.append(last_roomslot)

        new_roomslot = data_model.AS_RoomSlot(last_roomslot.timeslot, room)
        room.load_roomslot_caches()
        room.availability.append(new_roomslot)
        with self.assertRaises(ConsistencyError):
            # Penultimate roomslot doesn't point at last roomslot.
            checker.check_roomslot_next_and_index_consistency(sched)

        # The schedule isn't actually consistent, but the indices and next
        # roomslots should be.
        room.flush_roomslot_caches()
        try:
            checker.check_roomslot_next_and_index_consistency(sched)
        except ConsistencyError:
            self.fail((
                        "Unexpectedly failed roomslot next/index "
                        "consistency with error: \n{}"
                    ).format(traceback.format_exc()))

        room.availability.pop()
        room.flush_roomslot_caches()
        room.load_roomslot_caches()
        room.availability.insert(0, new_roomslot)
        new_roomslot.flush_cache()
        with self.assertRaises(ConsistencyError):
            # Indices for everything but the first roomslot are wrong.
            checker.check_roomslot_next_and_index_consistency(sched)

    def test_schedule_dicts_consistency(self):
        checker = consistency_checks.ConsistencyChecker()
        sched = testutils.create_test_schedule_1()
        try:
            checker.check_schedule_dicts_consistency(sched)
        except ConsistencyError:
            self.fail(
                    "Unexpectedly failed schedule dicts consistency with "
                    "error: \n{}"
                    .format(traceback.format_exc()))

        sec = sched.class_sections[1]
        del sched.class_sections[1]
        sched.class_sections[0] = sec
        with self.assertRaises(ConsistencyError):
            # Section key mismatcch
            checker.check_schedule_dicts_consistency(sched)
        del sched.class_sections[0]
        sched.class_sections[1] = sec

        teacher = sched.teachers[1]
        del sched.teachers[1]
        sched.teachers[0] = teacher
        with self.assertRaises(ConsistencyError):
            # Teacher key mismatch
            checker.check_schedule_dicts_consistency(sched)
        del sched.teachers[0]
        sched.teachers[1] = teacher

        room = sched.classrooms["10-250"]
        del sched.classrooms["10-250"]
        sched.classrooms["54-100"] = room
        with self.assertRaises(ConsistencyError):
            # Room key mismatch
            checker.check_schedule_dicts_consistency(sched)
        del sched.classrooms["54-100"]
        sched.classrooms["10-250"] = room

        try:
            checker.check_schedule_dicts_consistency(sched)
        except ConsistencyError:
            self.fail(
                    "Unexpectedly failed schedule dicts consistency with "
                    "error: \n{}"
                    .format(traceback.format_exc()))

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

    def test_teacher_taught_sections_consistency(self):
        checker = consistency_checks.ConsistencyChecker()
        sched = testutils.create_test_schedule_1()
        try:
            checker.check_teacher_taught_sections_consistency(sched)
        except ConsistencyError:
            self.fail(
                    "Unexpectedly failed taught sections consistency with "
                    "error: \n{}"
                    .format(traceback.format_exc()))

        teacher = sched.teachers[1]
        sec = teacher.taught_sections[1]
        del teacher.taught_sections[1]
        teacher.taught_sections[2] = sec
        with self.assertRaises(ConsistencyError):
            # Wrong key
            checker.check_teacher_taught_sections_consistency(sched)
        del teacher.taught_sections[2]
        teacher.taught_sections[1] = sec

        teacher.taught_sections[2] = sched.class_sections[2]
        with self.assertRaises(ConsistencyError):
            # Teacher isn't teaching listed section
            checker.check_teacher_taught_sections_consistency(sched)
        del teacher.taught_sections[2]

        sec.teachers.append(sched.teachers[2])
        with self.assertRaises(ConsistencyError):
            # Teacher doesn't know they're teaching
            checker.check_teacher_taught_sections_consistency(sched)
        sec.teachers.pop()

        try:
            checker.check_teacher_taught_sections_consistency(sched)
        except ConsistencyError:
            self.fail(
                    "Unexpectedly failed taught sections consistency with "
                    "error: \n{}"
                    .format(traceback.format_exc()))

    def test_timeslot_consistency(self):
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

    def test_timeslot_duration_consistency(self):
        checker = consistency_checks.ConsistencyChecker()
        sched = testutils.create_test_schedule_1()
        try:
            checker.check_timeslot_duration_consistency(sched)
        except ConsistencyError:
            self.fail(
                    "Unexpectedly failed timeslot duration consistency "
                    "with error: \n{}"
                    .format(traceback.format_exc()))

        sched.timeslots[0].duration = 0
        with self.assertRaises(ConsistencyError):
            # Wrong duration
            checker.check_timeslot_duration_consistency(sched)

    def test_timeslot_span_consistency(self):
        checker = consistency_checks.ConsistencyChecker()
        sched = testutils.create_test_schedule_1()
        try:
            checker.check_timeslot_span_consistency(sched)
        except ConsistencyError:
            self.fail(
                    "Unexpectedly failed timeslot span consistency "
                    "with error: \n{}"
                    .format(traceback.format_exc()))

        sched.timeslots.append(data_model.AS_Timeslot(
            datetime.datetime(2017, 2, 2, 23, 30),
            datetime.datetime(2017, 2, 3, 0, 30),
            event_id=7))
        sched.timeslot_dict = sched.build_timeslot_dict()
        with self.assertRaises(ConsistencyError):
            checker.check_timeslot_span_consistency(sched)

    def test_timeslot_list_and_dict_consistency(self):
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


if __name__ == "__main__":
    unittest.main()
