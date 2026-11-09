from django.db import connection
from django.test.utils import CaptureQueriesContext

from esp.program.models import ClassSubject
from esp.program.models.app_ import StudentAppQuestion
from esp.program.tests import ProgramFrameworkTest
from esp.tests.factories import make_program


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

    def test_room_capacity_change_is_not_served_from_the_cached_catalog(self):
        """prefetch_capacity_data() stashes classroom data on each section.
        The catalog has no dependency on resources, so if that stash survived
        into the cached catalog, a later room-capacity change would be
        recomputed from stale numbers and cached as the new capacity.
        """
        warmed = [sec for cls in self._catalog()
                  for sec in cls.get_sections() if sec.classrooms()]
        self.assertTrue(warmed, "fixture produced no sections with a classroom")
        section = warmed[0]
        self.assertGreater(section.capacity, 3,
                           "fixture capacity is already at the post-change value")

        room = section.classrooms()[0]
        room.num_students = 3
        room.save()

        #   Read through the cached catalog first: it is the read that would
        #   store a wrong value, so reading a fresh section before it would
        #   hide the bug.
        cached = {sec.id: sec for cls in self._catalog()
                  for sec in cls.get_sections()}[section.id]
        self.assertEqual(cached.capacity, 3,
                         "capacity came from the catalog's stale room data")

    def test_detaching_an_app_question_evicts_the_former_class_catalog(self):
        """post_save only sees where a row now points, so detaching a question
        from its class has to evict the catalog that still counts it."""
        subject = self.program.classes().first()
        question = StudentAppQuestion.objects.create(
            program=self.program, subject=subject,
            question='What is your experience?')
        self._catalog()
        self.assertEqual(self._queries_to_reload(), 0,
                         "catalog should be cached before the question moves")

        question.subject = None
        question.save()

        self.assertGreater(
            self._queries_to_reload(), 0,
            "detaching the question left the catalog counting it")

    def test_editing_an_event_owned_by_another_program_refreshes_the_catalog(self):
        """Event.program need not match the program of the sections meeting at
        it, so the selector keys off the referencing sections as well."""
        other = make_program(
            instance_name='2223_Summer', instance_label='Summer 2223',
            categories=self.categories, admins=self.admins,
            modules=self.settings['modules'],
        )
        scheduled = [sec for cls in self._catalog()
                     for sec in cls.get_sections() if sec.get_meeting_times()]
        self.assertTrue(scheduled, "fixture produced no scheduled sections")
        section = scheduled[0]
        event = section._events[0]

        event.program = other
        event.save()
        self._catalog()
        self.assertEqual(self._queries_to_reload(), 0,
                         "catalog should be cached before the event is edited")

        new_start = event.start.replace(year=event.start.year + 1)
        event.start = new_start
        event.end = event.end.replace(year=event.end.year + 1)
        event.save()

        reloaded = {sec.id: sec for cls in self._catalog()
                    for sec in cls.get_sections()}
        starts = [e.start for e in reloaded[section.id]._events]
        self.assertIn(new_start, starts,
                      "catalog still holds the pre-edit time of an event "
                      "owned by another program")

    def test_detached_app_question_evicts_the_former_scope_after_commit(self):
        """ATOMIC_REQUESTS keeps the pre-move row visible to everyone else
        until commit, so a catalog rebuilt after the pre_save eviction but
        before that commit re-caches the old question count.  The post_save
        selector cannot drop it -- a detached question has no scope -- so the
        former scope is evicted again on commit.
        """
        subject = self.program.classes().first()
        question = StudentAppQuestion.objects.create(
            program=self.program, subject=subject,
            question='What is your experience?')
        self._catalog()
        self.assertEqual(self._queries_to_reload(), 0,
                         "catalog should be cached before the question moves")

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            question.subject = None
            question.save()
            #   Stands in for a concurrent request rebuilding the catalog
            #   while the detachment is still uncommitted.
            self._catalog()

        self.assertEqual(
            self._queries_to_reload(), 0,
            "the simulated racing rebuild should have re-cached the catalog")

        for callback in callbacks:
            callback()

        self.assertGreater(
            self._queries_to_reload(), 0,
            "the former program's catalog survived the committed detachment")
