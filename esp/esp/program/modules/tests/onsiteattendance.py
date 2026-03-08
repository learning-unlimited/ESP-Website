from esp.program.modules.handlers.onsiteattendance import OnSiteAttendance
from esp.program.tests import ProgramFrameworkTest
import datetime

class OnSiteAttendanceTest(ProgramFrameworkTest):

    def test_times_attending_class_empty(self):
        module = OnSiteAttendance()

        result = module.times_attending_class(self.program)

        self.assertEqual(result, {})

    def test_times_attending_class_structure(self):
        module = OnSiteAttendance()

        result = module.times_attending_class(self.program)

        self.assertIsInstance(result, dict)
        for key in result:
            self.assertIsInstance(key, datetime.datetime)

    def test_times_checked_in_structure(self):
        module = OnSiteAttendance()

        result = module.times_checked_in(self.program)

        self.assertIsInstance(result, list)

        for item in result:
            self.assertIsInstance(item, datetime.datetime)

    def test_times_attending_class_counts_students(self):
        module = OnSiteAttendance()

        result = module.times_attending_class(self.program)

        # If attendance exists, values should be lists of users
        for users in result.values():
            self.assertIsInstance(users, list)
            for u in users:
                self.assertTrue(hasattr(u, "username"))
                
