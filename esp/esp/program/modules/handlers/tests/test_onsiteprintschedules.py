from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.contrib.sessions.middleware import SessionMiddleware
from unittest.mock import patch

from esp.users.models import ESPUser, Record, RecordType
from esp.utils.models import PrintRequest, Printer
from esp.program.models import Program
from esp.program.modules.handlers.onsiteprintschedules import OnsitePrintSchedules


class OnsitePrintSchedulesTest(TestCase):
    def setUp(self):
        # Users
        self.student = ESPUser.objects.create(username='student_1')
        self.staff = ESPUser.objects.create(username='staff_1', is_staff=True)
        self.staff.isOnsite = lambda prog: True
        self.staff.isAdmin = lambda prog: True

        # Program
        self.program = Program.objects.create(
            name='Test Program',
            grade_min=1,
            grade_max=12
        )

        # RecordType
        self.rt_attended, _ = RecordType.objects.get_or_create(
            name='attended',
            defaults={'description': 'Attended'}
        )

        # Printer
        self.printer = Printer.objects.create(name='TestPrinter')

        # Module
        self.module = OnsitePrintSchedules()
        self.module.program = self.program

        self.factory = RequestFactory()

    def _get_request(self):
        request = self.factory.get('/?gen_img=json')
        request.user = self.staff

        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()

        request.session['onsite'] = True  # required

        return request

    @patch("esp.program.modules.handlers.onsiteprintschedules.ProgramPrintables.get_student_schedules")
    def test_print_request_creates_attendance_record(self, mock_print):
        """
        End-to-end test: pending request → attendance record created
        """
        mock_print.return_value = type("obj", (), {"content": b"fake_image"})

        PrintRequest.objects.create(
            user=self.student,
            printer=self.printer,
            time_requested=timezone.now(),
            time_executed=None
        )

        request = self._get_request()

        self.module.printschedules(
            request,
            None, None, None, None,
            'TestPrinter',
            self.program
        )

        exists = Record.objects.filter(
            user=self.student,
            event__name="attended",
            program=self.program
        ).exists()

        self.assertTrue(exists, "Attendance record was NOT created")

    @patch("esp.program.modules.handlers.onsiteprintschedules.ProgramPrintables.get_student_schedules")
    def test_print_request_marks_executed(self, mock_print):
        """
        Ensure PrintRequest gets executed
        """

        mock_print.return_value = type("obj", (), {"content": b"fake_image"})

        req = PrintRequest.objects.create(
            user=self.student,
            printer=self.printer,
            time_requested=timezone.now(),
            time_executed=None
        )

        request = self._get_request()

        self.module.printschedules(
            request,
            None, None, None, None,
            'TestPrinter',
            self.program
        )

        req.refresh_from_db()

        self.assertIsNotNone(req.time_executed, "PrintRequest was not marked executed")

    @patch("esp.program.modules.handlers.onsiteprintschedules.ProgramPrintables.get_student_schedules")
    def test_print_failure_rolls_back_attendance_record(self, mock_print):
        """
        If schedule generation fails, the attendance record should NOT be created.
        """
        # 1. Force the print function to raise an error
        mock_print.side_effect = Exception("PDF Engine Crash")

        # 2. Create the pending request
        req = PrintRequest.objects.create(
            user=self.student,
            printer=self.printer,
            time_requested=timezone.now(),
            time_executed=None
        )

        request = self._get_request()

        # 3. Call the method (it will return a 500 response due to our try/except)
        response = self.module.printschedules(
            request,
            None, None, None, None,
            'TestPrinter',
            self.program
        )

        # 4. VERIFY ROLLBACK
        # The record should NOT exist despite being called before the exception
        record_exists = Record.objects.filter(
            user=self.student,
            event__name="attended",
            program=self.program
        ).exists()

        # The PrintRequest should still be UNEXECUTED (None)
        req.refresh_from_db()

        self.assertEqual(response.status_code, 500)
        self.assertFalse(record_exists, "Database did NOT roll back the attendance record!")
        self.assertIsNone(req.time_executed, "Database did NOT roll back the PrintRequest status!")