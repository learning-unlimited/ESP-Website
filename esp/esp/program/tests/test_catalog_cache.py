"""Tests for the scoping of catalog_cached invalidation.

Rebuilding a large catalog is expensive, so a write to one program must not
throw away another program's cached catalog.  These tests pin that, and pin the
invalidations that must still happen.
"""

from datetime import datetime, timedelta

from esp.cal.models import Event
from esp.program.models import ClassSubject
from esp.program.tests import ProgramFrameworkTest
from esp.tests.factories import make_class, make_program


class CatalogCacheScopeTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp(num_students=0, num_teachers=2, classes_per_teacher=1,
                      sections_per_class=1)
        #   A second, independent program.  Writes to one must not disturb the
        #   other's cached catalog.
        self.other_program = make_program(
            instance_name='2223_Summer', instance_label='Summer 2223',
            categories=self.categories, admins=self.admins,
            modules=self.settings['modules'],
        )
        self.other_class = make_class(program=self.other_program,
                                      teacher=self.teachers[0],
                                      title='Other program class',
                                      category=self.categories[0],
                                      sections=1, accept=True)

    def cached_catalog(self, program):
        """The cached catalog for `program`, or None if it is not cached."""
        return ClassSubject.objects.catalog_cached(
            program, None, False, None, cache_only=True, order_args_override=None)

    def warm_both(self):
        ClassSubject.objects.catalog(self.program)
        ClassSubject.objects.catalog(self.other_program)
        self.assertIsNotNone(self.cached_catalog(self.program))
        self.assertIsNotNone(self.cached_catalog(self.other_program))

    def a_class_in(self, program):
        return ClassSubject.objects.filter(parent_program=program).first()

    # --- the point of the change -------------------------------------------

    def test_editing_a_class_spares_the_other_program(self):
        self.warm_both()

        cls = self.a_class_in(self.program)
        cls.title = 'Retitled'
        cls.save()

        self.assertIsNone(self.cached_catalog(self.program),
                          "the edited program's catalog should be invalidated")
        self.assertIsNotNone(self.cached_catalog(self.other_program),
                             "an unrelated program's catalog should survive")

    def test_editing_a_section_spares_the_other_program(self):
        self.warm_both()

        sec = self.a_class_in(self.program).sections.first()
        sec.max_class_capacity = (sec.max_class_capacity or 0) + 1
        sec.save()

        self.assertIsNone(self.cached_catalog(self.program))
        self.assertIsNotNone(self.cached_catalog(self.other_program))

    def test_rescheduling_spares_the_other_program(self):
        self.warm_both()

        sec = self.a_class_in(self.program).sections.first()
        sec.meeting_times.add(self.timeslots[0])

        self.assertIsNone(self.cached_catalog(self.program))
        self.assertIsNotNone(self.cached_catalog(self.other_program))

    # --- invalidations that must still happen ------------------------------

    def test_rescheduling_invalidates_at_all(self):
        """Catalog ordering uses earliest_start, which comes from meeting_times.

        m2m edits do not fire post_save on ClassSection, so this relies on the
        depend_on_m2m hook rather than the row dependency.
        """
        event = Event.objects.create(
            program=self.program, event_type=self.event_type,
            start=datetime(2222, 7, 8, 9, 0),
            end=datetime(2222, 7, 8, 9, 0) + timedelta(hours=1),
            name='extra slot', short_description='extra',
            description='extra slot for reschedule test')

        self.warm_both()
        self.a_class_in(self.program).sections.first().meeting_times.add(event)
        self.assertIsNone(self.cached_catalog(self.program),
                          "rescheduling must invalidate the catalog")

    def test_adding_a_teacher_invalidates_at_all(self):
        """The catalog materialises each class's teacher list, so a teacher
        change must invalidate it.  Adding a teacher is an m2m edit, which does
        not fire post_save on ClassSubject."""
        self.warm_both()
        self.a_class_in(self.program).makeTeacher(self.teachers[1])
        self.assertIsNone(self.cached_catalog(self.program),
                          "adding a teacher must invalidate the catalog")

    def test_removing_a_teacher_invalidates_at_all(self):
        cls = self.a_class_in(self.program)
        cls.makeTeacher(self.teachers[1])
        self.warm_both()
        cls.removeTeacher(self.teachers[1])
        self.assertIsNone(self.cached_catalog(self.program),
                          "removing a teacher must invalidate the catalog")

    def test_adding_a_teacher_spares_the_other_program(self):
        self.warm_both()
        self.a_class_in(self.program).makeTeacher(self.teachers[1])
        self.assertIsNotNone(self.cached_catalog(self.other_program))

    def test_catalog_serves_the_updated_teacher_list(self):
        """The user-visible symptom: get_teachers() on a catalog entry returns
        the cached _teachers list, so a stale cache shows a stale roster."""
        cls = self.a_class_in(self.program)
        self.warm_both()

        before = {t.id for c in ClassSubject.objects.catalog(self.program)
                  if c.id == cls.id for t in c.get_teachers()}
        self.assertNotIn(self.teachers[1].id, before)

        cls.makeTeacher(self.teachers[1])

        after = {t.id for c in ClassSubject.objects.catalog(self.program)
                 if c.id == cls.id for t in c.get_teachers()}
        self.assertIn(self.teachers[1].id, after,
                      "catalog served a stale teacher list")

    def test_new_class_invalidates_its_own_program(self):
        self.warm_both()
        make_class(program=self.program, teacher=self.teachers[0],
                   title='Brand new class', category=self.categories[0],
                   sections=1, accept=True)
        self.assertIsNone(self.cached_catalog(self.program))
        self.assertIsNotNone(self.cached_catalog(self.other_program))

    def test_deleting_a_class_invalidates_its_own_program(self):
        self.warm_both()
        self.a_class_in(self.program).delete()
        self.assertIsNone(self.cached_catalog(self.program))
        self.assertIsNotNone(self.cached_catalog(self.other_program))
    def test_catalog_contents_are_still_correct_after_invalidation(self):
        """Scoping must not cause a stale catalog to be served."""
        self.warm_both()

        titles_before = {c.title for c in ClassSubject.objects.catalog(self.program)}
        cls = self.a_class_in(self.program)
        cls.title = 'Definitely Renamed'
        cls.save()

        titles_after = {c.title for c in ClassSubject.objects.catalog(self.program)}
        self.assertNotEqual(titles_before, titles_after)
        self.assertIn('Definitely Renamed', titles_after)

    def test_the_other_program_catalog_is_still_correct(self):
        """A surviving cache entry must hold the right data, not just exist."""
        self.warm_both()

        cls = self.a_class_in(self.program)
        cls.title = 'Renamed again'
        cls.save()

        other_titles = {c.title for c in ClassSubject.objects.catalog(self.other_program)}
        self.assertIn('Other program class', other_titles)
        self.assertNotIn('Renamed again', other_titles)
