from django.db import connection
from django.test.utils import CaptureQueriesContext

from esp.program.models import ClassSubject
from esp.program.models.app_ import StudentAppQuestion
from esp.program.tests import ProgramFrameworkTest


class CatalogInvalidationTest(ProgramFrameworkTest):
    """What does and does not evict the cached catalog."""

    def setUp(self):
        super().setUp(
            num_timeslots=2,
            num_rooms=4,
            num_teachers=3,
            classes_per_teacher=2,
            num_students=0,
        )
        self.schedule_randomly()

    def _catalog(self):
        return ClassSubject.objects.catalog(self.program)

    def _queries_to_reload(self):
        """Queries issued by a catalog() call; 0 means it came from cache."""
        with CaptureQueriesContext(connection) as ctx:
            self._catalog()
        return len(ctx)

    def test_editing_a_meeting_time_refreshes_the_catalog(self):
        """prefetch_catalog_data stores Event objects, so an edit to one has
        to evict the catalog holding them.  The meeting_times m2m dependency
        only fires when the set of times changes, not when a time is edited.
        """
        scheduled = [sec for cls in self._catalog()
                     for sec in cls.get_sections() if sec.get_meeting_times()]
        self.assertTrue(scheduled, "fixture produced no scheduled sections")
        section = scheduled[0]
        event = section._events[0]
        original_start = event.start

        new_start = original_start.replace(year=original_start.year + 1)
        event.start = new_start
        event.end = event.end.replace(year=event.end.year + 1)
        event.save()

        reloaded = {sec.id: sec for cls in self._catalog()
                    for sec in cls.get_sections()}
        starts = [e.start for e in reloaded[section.id]._events]
        self.assertIn(new_start, starts,
                      "catalog still holds the pre-edit event time")

    def test_program_level_app_question_does_not_evict_the_catalog(self):
        """A question with no subject is not counted by the catalog, so saving
        one must not evict it (the selector used to raise and evict globally).
        """
        self._catalog()
        self.assertEqual(self._queries_to_reload(), 0,
                         "catalog should be cached before the question is saved")

        StudentAppQuestion.objects.create(program=self.program, subject=None,
                                          question='Why do you want to attend?')

        self.assertEqual(
            self._queries_to_reload(), 0,
            "a program-level application question evicted the cached catalog")

    def test_class_level_app_question_does_evict_the_catalog(self):
        """The counterpart: a question attached to a class does affect the
        catalog's question count, so it must still evict."""
        self._catalog()
        self.assertEqual(self._queries_to_reload(), 0,
                         "catalog should be cached before the question is saved")

        subject = self.program.classes().first()
        StudentAppQuestion.objects.create(program=self.program, subject=subject,
                                          question='What is your experience?')

        self.assertGreater(
            self._queries_to_reload(), 0,
            "a class-level application question should have evicted the catalog")
