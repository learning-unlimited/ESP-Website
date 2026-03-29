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
        install_cal()  # Ensure Teacher Interview/Training event types exist

        # Get or create the ProgramModule backing record
        self.module_model, _ = ProgramModule.objects.get_or_create(
            handler='TeacherEventsModule',
            defaults={
                'link_title': 'Teacher Events',
                'admin_title': 'Teacher Events Admin',
                'module_type': 'teach',
                'seq': 20
            }
        )
        # Create the concrete module instance attached to this program
        self.te_module = TeacherEventsModule.objects.create(
            program=self.program,
            module=self.module_model,
            seq=20
        )

        self.teacher = self.teachers[0]
        self.event_types = EventType.teacher_event_types()

    def _url(self):
        return '/teach/%s/calendar_data' % self.program.getUrlBase()

    def test_calendar_data_anonymous_gets_401(self):
        """Anonymous users should receive a 401 JSON error (not an HTML redirect)."""
        self.client.logout()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn('error', data)

    def test_calendar_data_student_gets_403(self):
        """Non-teacher authenticated users should receive a 403 JSON error."""
        self.client.login(username=self.students[0].username, password='password')
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('error', data)

    def test_calendar_data_content(self):
        """Test the JSON structure and event status flags."""
        self.client.login(username=self.teacher.username, password='password')

        now = timezone.now()

        # 1. Past training event
        past_event = Event.objects.create(
            name='Past Training',
            start=now - timedelta(days=1),
            end=now - timedelta(hours=23),
            short_description='Past',
            description='Past Training',
            event_type=self.event_types['training'],
            program=self.program
        )

        # 2. Future available interview slot
        future_event = Event.objects.create(
            name='Future Interview',
            start=now + timedelta(days=1),
            end=now + timedelta(days=1, hours=1),
            short_description='Future',
            description='Future Interview',
            event_type=self.event_types['interview'],
            program=self.program
        )

        # 3. Full interview slot (taken by another teacher)
        other_teacher = self.teachers[1]
        full_event = Event.objects.create(
            name='Full Interview',
            start=now + timedelta(days=2),
            end=now + timedelta(days=2, hours=1),
            short_description='Full',
            description='Full Interview',
            event_type=self.event_types['interview'],
            program=self.program
        )
        UserAvailability.objects.create(
            user=other_teacher,
            event=full_event,
            role=self.te_module.availability_role()
        )

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIsInstance(data, list)

        # Map by id for easy lookup
        items_by_id = {item['id']: item for item in data}

        self.assertIn(past_event.id, items_by_id)
        self.assertIn(future_event.id, items_by_id)
        self.assertIn(full_event.id, items_by_id)

        self.assertEqual(items_by_id[past_event.id]['extendedProps']['status'], 'past')
        self.assertEqual(items_by_id[future_event.id]['extendedProps']['status'], 'available')
        self.assertEqual(items_by_id[full_event.id]['extendedProps']['status'], 'full')

        # Check required keys are present in each event
        for item in data:
            self.assertIn('id', item)
            self.assertIn('title', item)
            self.assertIn('start', item)
            self.assertIn('end', item)
            self.assertIn('color', item)
            self.assertIn('extendedProps', item)
            self.assertIn('event_type_id', item['extendedProps'])

    def test_calendar_data_is_mine(self):
        """Events the current teacher has signed up for should be marked 'mine'."""
        self.client.login(username=self.teacher.username, password='password')

        now = timezone.now()
        my_event = Event.objects.create(
            name='My Training',
            start=now + timedelta(days=3),
            end=now + timedelta(days=3, hours=1),
            short_description='Mine',
            description='My Training',
            event_type=self.event_types['training'],
            program=self.program
        )
        UserAvailability.objects.create(
            user=self.teacher,
            event=my_event,
            role=self.te_module.availability_role()
        )

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        data = response.json()

        my_item = next((item for item in data if item['id'] == my_event.id), None)
        self.assertIsNotNone(my_item, 'Event signed up for by teacher not found in response')
        self.assertEqual(my_item['extendedProps']['status'], 'mine')
        self.assertEqual(my_item['color'], '#28a745')

    def test_calendar_data_empty(self):
        """When no teacher events exist, the response should be an empty list."""
        Event.objects.filter(
            program=self.program,
            event_type__is_teacher_type=True
        ).delete()
        self.client.login(username=self.teacher.username, password='password')
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])
