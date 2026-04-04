# from django.test import TestCase
# from django.utils import timezone
# from esp.users.models import ESPUser, Record, RecordType
# from esp.utils.models import PrintRequest, Printer
# from esp.program.models import Program
# from esp.program.modules.handlers.onsiteprintschedules import OnsitePrintSchedules

# class OnsitePrintSchedulesTest(TestCase):
#     def setUp(self):
#         # 1. Create a Student
#         self.user = ESPUser.objects.create(username='test_student')
        
#         # 2. Create a Program (with required grade fields)
#         self.program = Program.objects.create(
#             name='Test Program', 
#             grade_min=1, 
#             grade_max=12
#         )
        
#         # 3. Create the 'attended' Type (Use get_or_create to avoid duplicates)
#         self.rt_attended, _ = RecordType.objects.get_or_create(
#             name='attended', 
#             defaults={'description': 'Attended'}
#         )
        
#         # 4. Create a Printer
#         self.printer = Printer.objects.create(name='TestPrinter')
        
#         # 5. Initialize the Module
#         self.module = OnsitePrintSchedules()

#     def test_checkin_logic_creates_record(self):
#         """
#         Verify that when a request is processed, an attendance record is made.
#         """
#         # Create a pending print request
#         req = PrintRequest.objects.create(
#             user=self.user,
#             printer=self.printer,
#             time_requested=timezone.now(),
#             time_executed=None
#         )

#         # SIMULATE THE MODULE LOGIC DIRECTLY
#         # Instead of calling the whole web view, let's test the database logic
#         # this is the exact code inside your printschedules method
#         requests = PrintRequest.objects.filter(time_executed__isnull=True, printer__name='TestPrinter')
        
#         if requests.exists():
#             r = requests[0]
#             r.time_executed = timezone.now()
#             r.save()
            
#             # This is your new logic!
#             rt = RecordType.objects.get(name="attended")
#             Record.objects.get_or_create(
#                 user=r.user, 
#                 event=rt, 
#                 program=self.program
#             )

#         # VERIFY
#         exists = Record.objects.filter(
#             user=self.user, 
#             event__name="attended", 
#             program=self.program
#         ).exists()
        
#         self.assertTrue(exists, "The Attendance Record was NOT created.")
from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.contrib.sessions.middleware import SessionMiddleware

from esp.users.models import ESPUser, Record, RecordType
from esp.utils.models import PrintRequest, Printer
from esp.program.models import Program
from esp.program.modules.handlers.onsiteprintschedules import OnsitePrintSchedules


class OnsitePrintSchedulesTest(TestCase):
    def setUp(self):
        # Users
        self.student = ESPUser.objects.create(username='student_1')
        self.staff = ESPUser.objects.create(username='staff_1', is_staff=True)

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
        self.factory = RequestFactory()

    def _get_request(self):
        request = self.factory.get('/?gen_img=json')
        request.user = self.staff

        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()

        # Required for @needs_onsite
        request.session['onsite'] = True

        return request

    def test_print_request_creates_attendance_record(self):
        """
        End-to-end test: pending request → attendance record created
        """
        self.module.program = self.program
        # Create pending request (NO program field here!)
        PrintRequest.objects.create(
            user=self.student,
            printer=self.printer,
            time_requested=timezone.now(),
            time_executed=None
        )

        request = self._get_request()

        # Execute
        self.module.printschedules(
            request,
            None, None, None, None,
            'TestPrinter',   # matches printer__name filter
            self.program
        )

        # Verify Record created
        exists = Record.objects.filter(
            user=self.student,
            event__name="attended",
            program=self.program
        ).exists()

        self.assertTrue(exists, "Attendance record was NOT created")

    def test_print_request_marks_executed(self):
        """
        Ensure PrintRequest gets executed
        """
        self.module.program = self.program
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