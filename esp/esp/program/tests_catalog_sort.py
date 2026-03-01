from datetime import datetime, timedelta

from esp.program.models import ClassSubject, ClassSection, ClassCategories, ProgramModule
from esp.program.class_status import ClassStatus
from esp.cal.models import Event, EventType
from esp.program.tests import ProgramFrameworkTest


class CatalogSortTest(ProgramFrameworkTest):
    """Tests for catalog ordering using the earliest_start annotation."""

    def setUp(self):
        super().setUp(
            num_students=0,
            num_teachers=1,
            classes_per_teacher=0,
        )

    def _make_class(self, title, sections):
        """Create a ClassSubject with one or more sections.

        ``sections`` is a list of (start_datetime, status) tuples.
        Returns the created ClassSubject.
        """
        cls = ClassSubject.objects.create(
            title=title,
            category=self.categories[0],
            parent_program=self.program,
            status=ClassStatus.ACCEPTED,
            grade_min=7,
            grade_max=12,
            class_size_max=30,
        )
        cls.makeTeacher(self.teachers[0])
        for start_dt, status in sections:
            sec = cls.add_section(duration=1.0)
            sec.status = status
            sec.save()
            event = Event.objects.create(
                program=self.program,
                event_type=self.event_type,
                start=start_dt,
                end=start_dt + timedelta(hours=1),
            )
            sec.meeting_times.add(event)
        return cls

    def test_sort_by_earliest_start_ascending(self):
        """Classes should sort by their earliest non-cancelled start time."""
        cls_a = self._make_class('Class A', [
            (datetime(2026, 1, 1, 10, 0), ClassStatus.ACCEPTED),
        ])
        cls_b = self._make_class('Class B', [
            (datetime(2026, 1, 1, 11, 0), ClassStatus.ACCEPTED),
        ])

        catalog = ClassSubject.objects.catalog(
            self.program, order_args_override=['earliest_start', 'id'],
        )
        self.assertEqual(len(catalog), 2)
        self.assertEqual(catalog[0].id, cls_a.id)
        self.assertEqual(catalog[1].id, cls_b.id)

    def test_sort_by_earliest_start_descending(self):
        """Descending sort should reverse the order."""
        cls_a = self._make_class('Class A', [
            (datetime(2026, 1, 1, 10, 0), ClassStatus.ACCEPTED),
        ])
        cls_b = self._make_class('Class B', [
            (datetime(2026, 1, 1, 11, 0), ClassStatus.ACCEPTED),
        ])

        catalog = ClassSubject.objects.catalog(
            self.program, order_args_override=['-earliest_start', 'id'],
        )
        self.assertEqual(len(catalog), 2)
        self.assertEqual(catalog[0].id, cls_b.id)
        self.assertEqual(catalog[1].id, cls_a.id)

    def test_cancelled_section_excluded_from_sort(self):
        """A cancelled section with an earlier time must not affect ordering.

        Class C has an accepted section at 12pm and a cancelled section at
        8am.  Without the filter, the cancelled 8am time would sort Class C
        before Classes A (10am) and B (11am).  With the filter it should
        sort after both.
        """
        cls_a = self._make_class('Class A', [
            (datetime(2026, 1, 1, 10, 0), ClassStatus.ACCEPTED),
        ])
        cls_b = self._make_class('Class B', [
            (datetime(2026, 1, 1, 11, 0), ClassStatus.ACCEPTED),
        ])
        cls_c = self._make_class('Class C', [
            (datetime(2026, 1, 1, 12, 0), ClassStatus.ACCEPTED),
            (datetime(2026, 1, 1, 8, 0), ClassStatus.CANCELLED),
        ])

        catalog = ClassSubject.objects.catalog(
            self.program, order_args_override=['earliest_start', 'id'],
        )
        self.assertEqual(len(catalog), 3)
        self.assertEqual(catalog[0].id, cls_a.id,
                         'Class A (10am) should be first')
        self.assertEqual(catalog[1].id, cls_b.id,
                         'Class B (11am) should be second')
        self.assertEqual(catalog[2].id, cls_c.id,
                         'Class C (12pm active, 8am cancelled) should be last')

    def test_multi_section_no_duplicates(self):
        """A class with multiple active sections must appear only once."""
        cls_a = self._make_class('Class A', [
            (datetime(2026, 1, 1, 10, 0), ClassStatus.ACCEPTED),
            (datetime(2026, 1, 1, 14, 0), ClassStatus.ACCEPTED),
        ])
        cls_b = self._make_class('Class B', [
            (datetime(2026, 1, 1, 11, 0), ClassStatus.ACCEPTED),
        ])

        catalog = ClassSubject.objects.catalog(
            self.program, order_args_override=['earliest_start', 'id'],
        )
        ids = [c.id for c in catalog]
        self.assertEqual(len(ids), 2, 'Multi-section class should not produce duplicates')
        self.assertEqual(ids, [cls_a.id, cls_b.id])
