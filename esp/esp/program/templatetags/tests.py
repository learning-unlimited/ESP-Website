import datetime

from django.test import TestCase

from esp.cal.models import Event, EventType
from esp.program.templatetags.schedule import classes_by_day
from esp.program.tests import ProgramFrameworkTest


class ClassesByDayTagTest(ProgramFrameworkTest):
    """Unit tests for the classes_by_day template tag."""

    def setUp(self):
        super().setUp()
        # All sections start with no meeting_times
        for sec in self.program.sections():
            sec.meeting_times.clear()

    def _make_event_on_date(self, year, month, day, hour_start, hour_end):
        event, _ = Event.objects.get_or_create(
            program=self.program,
            event_type=self.event_type,
            start=datetime.datetime(year, month, day, hour_start, 0),
            end=datetime.datetime(year, month, day, hour_end, 0),
            short_description=f'{year}-{month:02d}-{day:02d} {hour_start}h',
            description=f'{year}-{month:02d}-{day:02d} {hour_start}h',
        )
        return event

    def test_single_date_section_yields_one_row(self):
        """Section with all timeslots on one date → single row, is_repeating=False."""
        section = list(self.program.sections())[0]
        ts = self.timeslots[0]
        section.meeting_times.set([ts])

        result = classes_by_day([section])

        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]['is_repeating'])
        self.assertEqual(result[0]['cls'], section)
        self.assertEqual(result[0]['event'], ts)

    def test_multi_date_section_yields_one_row_per_date(self):
        """Section with timeslots on two distinct dates → two rows, is_repeating=True."""
        section = list(self.program.sections())[0]
        ts1 = self._make_event_on_date(2222, 7, 7, 9, 10)
        ts2 = self._make_event_on_date(2222, 7, 14, 9, 10)
        section.meeting_times.set([ts1, ts2])

        result = classes_by_day([section])

        self.assertEqual(len(result), 2)
        self.assertTrue(all(r['is_repeating'] for r in result))
        self.assertEqual(result[0]['cls'], section)
        self.assertEqual(result[1]['cls'], section)
        self.assertLess(result[0]['event'].start, result[1]['event'].start)

    def test_compulsory_event_passthrough(self):
        """An Event passed directly is wrapped as-is with is_repeating=False."""
        ts = self.timeslots[0]

        result = classes_by_day([ts])

        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]['is_repeating'])
        self.assertIs(result[0]['cls'], ts)
        self.assertIs(result[0]['event'], ts)

    def test_section_with_no_meeting_times(self):
        """Section with no timeslots → one row with empty day_time and None event."""
        section = list(self.program.sections())[0]

        result = classes_by_day([section])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['day_time'], '')
        self.assertIsNone(result[0]['event'])
        self.assertFalse(result[0]['is_repeating'])

    def test_rows_sorted_by_start_ascending(self):
        """Rows from multiple sections are sorted by event.start ascending."""
        sections = list(self.program.sections())[:2]
        ts_early = self._make_event_on_date(2222, 7, 7, 8, 9)
        ts_late = self._make_event_on_date(2222, 7, 7, 11, 12)
        sections[0].meeting_times.set([ts_late])
        sections[1].meeting_times.set([ts_early])

        # Pass sections in reverse chronological order
        result = classes_by_day([sections[0], sections[1]])

        self.assertEqual(len(result), 2)
        self.assertLessEqual(result[0]['event'].start, result[1]['event'].start)

    def test_no_event_rows_sort_last(self):
        """Sections with no meeting_times sort after sections that have events."""
        sections = list(self.program.sections())[:2]
        ts = self.timeslots[0]
        sections[0].meeting_times.clear()   # no event
        sections[1].meeting_times.set([ts])  # has event

        result = classes_by_day([sections[0], sections[1]])

        self.assertEqual(len(result), 2)
        self.assertIsNotNone(result[0]['event'])
        self.assertIsNone(result[1]['event'])
