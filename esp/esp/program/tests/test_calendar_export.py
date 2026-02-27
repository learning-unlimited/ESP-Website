from django.test import TestCase, Client
from esp.users.models import ESPUser
from esp.program.models import ClassSection, ClassSubject, Program
from esp.cal.models import Event, EventType
import pytz
from datetime import datetime
from unittest.mock import patch
import urllib.parse

class CalendarExportTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.program = Program.objects.create(name="Test Program", url="test/1", grade_min=7, grade_max=12)
        from esp.program.models.class_ import ClassCategories
        self.category = ClassCategories.objects.create(category="Math", symbol="M")
        self.subject = ClassSubject.objects.create(title="Test Math", parent_program=self.program, category=self.category, grade_min=7, grade_max=12)
        self.section = ClassSection.objects.create(parent_class=self.subject)
        self.user = ESPUser.objects.create_user(username="student1", password="password", email="test@test.com")

    def test_google_calendar_url(self):
        with patch.object(self.section, 'get_meeting_times', return_value=[]):
            self.assertEqual(self.section.google_calendar_url, "")

        event_type = EventType.objects.create(description="Class Time Block")
        event = Event.objects.create(
            start=datetime(2025, 1, 1, 10, 0, tzinfo=pytz.utc),
            end=datetime(2025, 1, 1, 12, 0, tzinfo=pytz.utc),
            event_type=event_type
        )
        
        with patch.object(self.section, 'get_meeting_times', return_value=[event]):
            url = self.section.google_calendar_url
            self.assertIn("calendar.google.com", url)
            self.assertIn("TEMPLATE", url)
            self.assertIn("Test+Math", url)
            self.assertIn("20250101T100000Z%2F20250101T120000Z", url)

    def test_studentschedule_ics(self):
        from esp.program.modules.handlers.studentclassregmodule import StudentClassRegModule
        module = StudentClassRegModule()
        module.program = self.program
        
        # Test direct call to avoid complicated url/auth setup of ESP framework
        from django.http import HttpRequest
        request = HttpRequest()
        request.user = self.user
        
        response = module.studentschedule_ics(request, None, None, None, module, None, self.program)
        self.assertEqual(response['Content-Type'], 'text/calendar')
        self.assertIn(b'BEGIN:VCALENDAR', response.content)
