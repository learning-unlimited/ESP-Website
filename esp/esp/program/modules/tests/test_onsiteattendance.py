from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.handlers.onsiteattendance import OnSiteAttendance
from esp.program.models import ProgramModule, StudentRegistration
import datetime

class OnSiteAttendanceTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        # Create a ProgramModule instance for OnSiteAttendance
        self.module_model, _ = ProgramModule.objects.get_or_create(
            handler='OnSiteAttendance',
            defaults={
                'link_title': 'OnSite Attendance',
                'admin_title': 'OnSite Attendance Admin',
                'module_type': 'onsite',
                'seq': 20
            }
        )
        # Create the specific OnSiteAttendance handler instance
        self.os_module = OnSiteAttendance.objects.create(
            program=self.program,
            module=self.module_model,
            seq=20
        )

    def test_times_checked_in_empty(self):
        """Test with no check-ins."""
        result = self.os_module.times_checked_in(self.program)
        self.assertEqual(len(result), 0)

    def test_times_checked_in_basic(self):
        """Test with student check-ins."""
        # Enroll a student
        student = self.students[0]
        # Get a section from our scheduled program
        section = self.program.sections().first()
        # Create a registration with a check-in timestamp
        reg = StudentRegistration.objects.create(
            user=student,
            section=section,
            checkin_timestamp=datetime.datetime(2026, 3, 1, 12, 0)
        )
        
        result = self.os_module.times_checked_in(self.program)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], datetime.datetime(2026, 3, 1, 12, 0))

    def test_times_attending_class(self):
        """Test attendance tracking for a specific class."""
        # Use existing program setup to check if the logic handles class associations.
        result = self.os_module.times_attending_class(self.program)
        # Should be a list (possibly empty if no registrations with checkins exist)
        self.assertIsInstance(result, list)
