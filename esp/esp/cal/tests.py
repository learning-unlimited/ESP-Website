"""
Tests for esp.cal.models
Source: esp/esp/cal/models.py

Tests EventType and Event models including duration, comparison operators,
and static utility methods (total_length, contiguous, collapse, group_contiguous).
"""
from datetime import datetime, timedelta

from django.contrib.auth.models import Group

from esp.cal.models import Event, EventType, install
from esp.tests.util import CacheFlushTestCase as TestCase


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class EventTypeTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        install()

    def test_str(self):
        et = EventType.objects.get(description='Class Time Block')
        self.assertEqual(str(et), 'Class Time Block')

    def test_get_from_desc(self):
        et = EventType.get_from_desc('Teacher Interview')
        self.assertEqual(et.description, 'Teacher Interview')

    def test_teacher_event_types(self):
        result = EventType.teacher_event_types()
        self.assertIn('interview', result)
        self.assertIn('training', result)
        self.assertEqual(result['interview'].description, 'Teacher Interview')

    def test_install_idempotent(self):
        count_before = EventType.objects.count()
        install()
        count_after = EventType.objects.count()
        self.assertEqual(count_before, count_after)


class EventTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        install()
        self.event_type = EventType.objects.get(description='Class Time Block')
        self.start = datetime(2025, 6, 15, 9, 0)
        self.end = datetime(2025, 6, 15, 10, 30)
        self.event = Event.objects.create(
            start=self.start,
            end=self.end,
            short_description='Test class',
            description='A test class event',
            name='Test Event',
            event_type=self.event_type,
        )

    def test_title(self):
        self.assertEqual(self.event.title(), 'Test Event')

    def test_duration(self):
        dur = self.event.duration()
        self.assertEqual(dur, timedelta(hours=1.5))

    def test_start_w_buffer(self):
        buffered = self.event.start_w_buffer()
        self.assertEqual(buffered, self.start - timedelta(minutes=15))

    def test_end_w_buffer(self):
        buffered = self.event.end_w_buffer()
        self.assertEqual(buffered, self.end + timedelta(minutes=15))

    def test_start_w_custom_buffer(self):
        buffered = self.event.start_w_buffer(buffer=timedelta(minutes=30))
        self.assertEqual(buffered, self.start - timedelta(minutes=30))

    def test_duration_str(self):
        result = self.event.duration_str()
        self.assertEqual(result, '1 hr 30 min')

    def test_str(self):
        result = str(self.event)
        self.assertIn('Sun', result)  # June 15, 2025 is a Sunday

    def test_short_time(self):
        result = self.event.short_time()
        self.assertIn('9', result)
        self.assertIn('AM', result)

    def test_pretty_time(self):
        result = self.event.pretty_time()
        self.assertIn('Sun', result)

    def test_pretty_time_with_date(self):
        result = self.event.pretty_time_with_date()
        self.assertIn('Jun', result)

    def test_pretty_date(self):
        result = self.event.pretty_date()
        self.assertIn('Sunday', result)
        self.assertIn('June', result)

    def test_pretty_start_time(self):
        result = self.event.pretty_start_time()
        self.assertIn('Sun', result)

    def test_parent_program_none(self):
        self.assertIsNone(self.event.parent_program())


class EventComparisonTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        install()
        self.event_type = EventType.objects.get(description='Class Time Block')
        self.early = Event.objects.create(
            start=datetime(2025, 6, 15, 9, 0),
            end=datetime(2025, 6, 15, 10, 0),
            short_description='Early',
            description='',
            name='Early',
            event_type=self.event_type,
        )
        self.late = Event.objects.create(
            start=datetime(2025, 6, 15, 11, 0),
            end=datetime(2025, 6, 15, 12, 0),
            short_description='Late',
            description='',
            name='Late',
            event_type=self.event_type,
        )

    def test_lt(self):
        self.assertTrue(self.early < self.late)

    def test_gt(self):
        self.assertTrue(self.late > self.early)

    def test_eq_same_start(self):
        same = Event.objects.create(
            start=self.early.start,
            end=datetime(2025, 6, 15, 10, 30),
            short_description='Same start',
            description='',
            name='Same',
            event_type=self.event_type,
        )
        self.assertEqual(self.early, same)

    def test_ne(self):
        self.assertNotEqual(self.early, self.late)

    def test_le(self):
        self.assertTrue(self.early <= self.late)

    def test_ge(self):
        self.assertTrue(self.late >= self.early)

    def test_hash(self):
        self.assertEqual(hash(self.early), hash(self.early.start))


class EventStaticMethodsTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        install()
        self.event_type = EventType.objects.get(description='Class Time Block')
        self.events = []
        for hour in [9, 10, 11, 14]:
            ev = Event.objects.create(
                start=datetime(2025, 6, 15, hour, 0),
                end=datetime(2025, 6, 15, hour, 50),
                short_description='',
                description='',
                name='Event %d' % hour,
                event_type=self.event_type,
            )
            self.events.append(ev)

    def test_total_length(self):
        length = Event.total_length(self.events)
        # From 9:00 to 14:50 = 5hr 50min
        # However, it calculates total duration directly from event durations.
        # dur.total_seconds() = 21000. 21000 / 3600 = 5.8333...
        # hrs = round(5.8333) = 5.83 hours
        expected = timedelta(hours=5.83)
        self.assertEqual(length, expected)

    def test_total_length_empty(self):
        self.assertEqual(Event.total_length([]), timedelta(seconds=0))

    def test_contiguous(self):
        # events[0] ends at 9:50, events[1] starts at 10:00 => 10 min gap < 20 min tol
        self.assertTrue(Event.contiguous(self.events[0], self.events[1]))

    def test_not_contiguous(self):
        # events[2] ends at 11:50, events[3] starts at 14:00 => 130 min gap > 20 min tol
        self.assertFalse(Event.contiguous(self.events[2], self.events[3]))

    def test_group_contiguous(self):
        groups = Event.group_contiguous(self.events)
        # First 3 events are contiguous (gaps < 20 min), 4th is separate (gap > 20 min)
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(groups[0]), 3)
        self.assertEqual(len(groups[1]), 1)

    def test_collapse(self):
        # Create two overlapping events
        e1 = Event(start=datetime(2025, 6, 15, 9, 0), end=datetime(2025, 6, 15, 10, 0),
                   event_type=self.event_type)
        e2 = Event(start=datetime(2025, 6, 15, 10, 0), end=datetime(2025, 6, 15, 11, 0),
                   event_type=self.event_type)
        collapsed = Event.collapse([e1, e2])
        self.assertEqual(len(collapsed), 1)
        self.assertEqual(collapsed[0].start, e1.start)
        self.assertEqual(collapsed[0].end, e2.end)

    def test_collapse_non_overlapping(self):
        e1 = Event(start=datetime(2025, 6, 15, 9, 0), end=datetime(2025, 6, 15, 10, 0),
                   event_type=self.event_type)
        e2 = Event(start=datetime(2025, 6, 15, 14, 0), end=datetime(2025, 6, 15, 15, 0),
                   event_type=self.event_type)
        collapsed = Event.collapse([e1, e2])
        self.assertEqual(len(collapsed), 2)
