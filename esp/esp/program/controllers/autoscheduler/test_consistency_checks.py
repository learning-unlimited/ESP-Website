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


if __name__ == "__main__":
    unittest.main()
