import unittest
import traceback

from esp.program.controllers.autoscheduler import consistency_checks, testutils
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

    # def test_sorting_consistency(self):
    #     checker = consistency_checks.ConsistencyChecker()
    #     sched = testutils.create_test_schedule_1()
    #     try:
    #         checker.check_sorting_consistency(sched)
    #     except ConsistencyError:
    #         self.fail(
    #                 "Unexpectedly failed sortingconsistency with error: \n{}"
    #                 .format(traceback.format_exc()))


if __name__ == "__main__":
    unittest.main()
