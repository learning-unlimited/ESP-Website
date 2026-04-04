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