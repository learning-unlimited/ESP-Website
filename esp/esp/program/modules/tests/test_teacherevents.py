from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.handlers.teachereventsmodule import TeacherEventsModule
from esp.program.models import ProgramModule
from esp.cal.models import Event, EventType, install as install_cal
from esp.users.models import UserAvailability
from django.utils import timezone
from datetime import timedelta
import json

class TeacherEventsModuleTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        install_cal() # Ensure Teacher Interview/Training types exist
        
        # Create a ProgramModule instance for TeacherEventsModule
        self.module_model, _ = ProgramModule.objects.get_or_create(
            handler='TeacherEventsModule',
            defaults={
                'link_title': 'Teacher Events',
                'admin_title': 'Teacher Events Admin',
                'module_type': 'teach',
                'seq': 20
            }
        )
        # Create the specific handler instance
        self.te_module = TeacherEventsModule.objects.create(
            program=self.program,
            module=self.module_model,
            seq=20
        )
        
        self.teacher = self.teachers[0]
        self.event_types = EventType.teacher_event_types()

    def test_calendar_data_auth(self):
        """Test that only teachers can access the calendar data."""
        url = f'/teach/{self.program.getUrlBase()}/calendar_data'
        
        # Logged out
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302) # Redirect to login
        
        # Logged in as student
        self.client.login(username=self.students[0].username, password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # Forbidden
        
    def test_calendar_data_content(self):
        """Test the JSON structure and content of the calendar data."""
        self.client.login(username=self.teacher.username, password='password')
        
        # Create some events
        now = timezone.now()
        
        # 1. Past event
        past_event = Event.objects.create(
            name="Past Training",
            start=now - timedelta(days=1),
            end=now - timedelta(days=1, hours=-1),
            event_type=self.event_types['training'],
            program=self.program
        )
        
        # 2. Future available event
        future_event = Event.objects.create(
            name="Future Interview",
            start=now + timedelta(days=1),
            end=now + timedelta(days=1, hours=1),
            event_type=self.event_types['interview'],
            program=self.program
        )
        
        # 3. Full interview (taken by another teacher)
        other_teacher = self.teachers[1]
        full_event = Event.objects.create(
            name="Full Interview",
            start=now + timedelta(days=2),
            end=now + timedelta(days=2, hours=1),
            event_type=self.event_types['interview'],
            program=self.program
        )
        UserAvailability.objects.create(
            user=other_teacher,
            event=full_event,
            role=self.te_module.availability_role()
        )
        
        url = f'/teach/{self.program.getUrlBase()}/calendar_data'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data), 3)
        
        # Verify specific states
        for item in data:
            if item['id'] == past_event.id:
                self.assertEqual(item['extendedProps']['status'], 'past')
            elif item['id'] == future_event.id:
                self.assertEqual(item['extendedProps']['status'], 'available')
            elif item['id'] == full_event.id:
                self.assertEqual(item['extendedProps']['status'], 'full')

    def test_calendar_data_is_mine(self):
        """Test that events I am signed up for are marked as 'mine'."""
        self.client.login(username=self.teacher.username, password='password')
        
        now = timezone.now()
        my_event = Event.objects.create(
            name="My Training",
            start=now + timedelta(days=3),
            end=now + timedelta(days=3, hours=1),
            event_type=self.event_types['training'],
            program=self.program
        )
        UserAvailability.objects.create(
            user=self.teacher,
            event=my_event,
            role=self.te_module.availability_role()
        )
        
        url = f'/teach/{self.program.getUrlBase()}/calendar_data'
        response = self.client.get(url)
        data = response.json()
        
        my_item = next(item for item in data if item['id'] == my_event.id)
        self.assertEqual(my_item['extendedProps']['status'], 'mine')
        self.assertEqual(my_item['color'], '#28a745') # Success Green
