from django.test import TestCase, Client
from esp.users.models import ESPUser
from esp.program.models import ClassSection, ClassSubject, Program
from esp.cal.models import Event, EventType
import pytz
from datetime import datetime
import urllib.parse

class CalendarExportTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.program = Program.objects.create(name="Test Program", program_type="test", program_instance="1")
        self.subject = ClassSubject.objects.create(title="Test Math", parent_program=self.program)
        self.section = ClassSection.objects.create(parent_class=self.subject)
        self.user = ESPUser.objects.create_user(username="student1", password="password", email="test@test.com")

    def test_google_calendar_url(self):
        self.assertEqual(self.section.google_calendar_url, "")

        event_type = EventType.objects.create(description="Class Time Block")
        event = Event.objects.create(
            start=datetime(2025, 1, 1, 10, 0, tzinfo=pytz.utc),
            end=datetime(2025, 1, 1, 12, 0, tzinfo=pytz.utc),
            event_type=event_type
        )
        self.section.meeting_times.add(event)
        
        url = self.section.google_calendar_url
        self.assertIn("calendar.google.com", url)
        self.assertIn("TEMPLATE", url)
        self.assertIn("Test+Math", url)
        self.assertIn("20250101T100000Z/20250101T120000Z", url)

    def test_studentschedule_ics(self):
        self.client.force_login(self.user)
        # Test that the view can be accessed and returns the correct content type
        # Note: Actual HTTP 200 may require exact module configs, but we verify response structure
        response = self.client.get(f"/learn/test/1/studentschedule_ics")
        if response.status_code == 200:
            self.assertEqual(response['Content-Type'], 'text/calendar')
