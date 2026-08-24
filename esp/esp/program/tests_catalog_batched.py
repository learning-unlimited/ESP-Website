"""Tests for the batched catalog attribute lookups (issue #1716).

``ClassManager.catalog_cached`` used to compute ``media_count``, ``_index_qsd``
and ``_studentapps_count`` with one correlated SQL subquery per catalog row.
Those are now filled in from three batched queries keyed by class id; these
tests pin down the resulting values so the replacement can't silently drift.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache

from esp.program.models import ClassSubject
from esp.program.models.app_ import StudentAppQuestion
from esp.program.tests import ProgramFrameworkTest
from esp.qsd.models import QuasiStaticData
from esp.qsdmedia.models import Media
from esp.tagdict.models import Tag
from esp.web.models import NavBarCategory


class CatalogBatchedAttributesTest(ProgramFrameworkTest):
    """The catalog should prepopulate media/app-question/index-QSD attributes."""

    def setUp(self):
        super().setUp(
            num_students=0,
            num_teachers=2,
            classes_per_teacher=1,
            num_categories=1,
        )
        #   The catalog is cached in-process; LocMemCache survives the
        #   per-test transaction rollback, so start from a clean slate.
        cache.clear()
        self.classes = list(self.program.classes())
        self.assertTrue(len(self.classes) >= 2,
                        "This test needs at least two classes in the program")

    def _catalog_by_id(self):
        """Return {class id: catalog instance} for the program's catalog."""
        return {c.id: c for c in ClassSubject.objects.catalog(self.program)}

    def _make_index_qsd(self, cls):
        """Create the class index QSD that got_index_qsd() looks for."""
        nav_category, _ = NavBarCategory.objects.get_or_create(
            name='learn', long_explanation='', include_auto_links=False)
        return QuasiStaticData.objects.create(
            url='learn/%s/index' % cls.url(),
            name='learn:index',
            title=cls.title,
            content='Index page for %s' % cls.emailcode(),
            author=self.admins[0],
            nav_category=nav_category,
        )

    def test_media_count(self):
        """media_count should match the number of Media objects owned by the class."""
        target, other = self.classes[0], self.classes[1]
        Media.objects.create(friendly_name='Doc 1', owner=target)
        Media.objects.create(friendly_name='Doc 2', owner=target)

        catalog = self._catalog_by_id()
        self.assertEqual(catalog[target.id].media_count, 2)
        self.assertEqual(catalog[other.id].media_count, 0)

    def test_media_count_ignores_other_content_types(self):
        """Media owned by a non-ClassSubject with a colliding id shouldn't count."""
        target = self.classes[0]
        program_ct = ContentType.objects.get_for_model(self.program)
        #   Same owner_id as the class, but a different owner_type.
        Media.objects.create(friendly_name='Program doc',
                             owner_type=program_ct, owner_id=target.id)

        catalog = self._catalog_by_id()
        self.assertEqual(catalog[target.id].media_count, 0)

    def test_studentapps_count(self):
        """numStudentAppQuestions() should be prepopulated from the catalog."""
        target, other = self.classes[0], self.classes[1]
        StudentAppQuestion.objects.create(subject=target, question='Why?')
        StudentAppQuestion.objects.create(subject=target, question='How?')
        #   A program-level question has no subject and must not be counted.
        StudentAppQuestion.objects.create(program=self.program, question='Who?')

        catalog = self._catalog_by_id()
        self.assertEqual(catalog[target.id]._studentapps_count, 2)
        self.assertEqual(catalog[target.id].numStudentAppQuestions(), 2)
        self.assertEqual(catalog[other.id]._studentapps_count, 0)
        self.assertEqual(catalog[other.id].numStudentAppQuestions(), 0)

    def test_index_qsd_detection(self):
        """got_index_qsd() should be True only for classes with an index QSD."""
        target, other = self.classes[0], self.classes[1]
        self._make_index_qsd(target)

        catalog = self._catalog_by_id()
        self.assertTrue(catalog[target.id].got_index_qsd(),
                        "Class with an index QSD should report got_index_qsd()")
        self.assertFalse(catalog[other.id].got_index_qsd(),
                         "Class without an index QSD should not report got_index_qsd()")
        #   Matches the uncached fallback in ClassSubject.got_index_qsd().
        for cls in (target, other):
            self.assertEqual(catalog[cls.id].got_index_qsd(),
                             ClassSubject.objects.get(id=cls.id).got_index_qsd())

    def test_index_qsd_lowercase_category_symbol(self):
        """Lower-case category symbols are allowed and must still be detected.

        The old SQL pattern only matched '[A-Z]' before the class id, so these
        classes were silently reported as having no index QSD.
        """
        target = self.classes[0]
        target.category.symbol = 'q'
        target.category.save()
        #   Re-fetch so emailcode()/url() pick up the new symbol.
        target = ClassSubject.objects.get(id=target.id)
        self._make_index_qsd(target)

        catalog = self._catalog_by_id()
        self.assertTrue(catalog[target.id].got_index_qsd())

    def test_program_index_qsd_is_not_a_class_index_qsd(self):
        """The program's own index page must not mark any class as documented."""
        nav_category, _ = NavBarCategory.objects.get_or_create(
            name='learn', long_explanation='', include_auto_links=False)
        QuasiStaticData.objects.create(
            url='learn/%s/index' % self.program.url,
            name='learn:index',
            title=self.program.niceName(),
            content='Welcome!',
            author=self.admins[0],
            nav_category=nav_category,
        )

        catalog = self._catalog_by_id()
        for cls in self.classes:
            self.assertFalse(catalog[cls.id].got_index_qsd(),
                             "Program index QSD should not count for class %s" % cls.emailcode())

    def test_index_qsd_of_another_program_is_ignored(self):
        """A class index QSD under a different program shouldn't leak in."""
        target = self.classes[0]
        nav_category, _ = NavBarCategory.objects.get_or_create(
            name='learn', long_explanation='', include_auto_links=False)
        QuasiStaticData.objects.create(
            url='learn/Other/2222_Summer/Classes/%s/index' % target.emailcode(),
            name='learn:index',
            title=target.title,
            content='Wrong program',
            author=self.admins[0],
            nav_category=nav_category,
        )

        catalog = self._catalog_by_id()
        self.assertFalse(catalog[target.id].got_index_qsd())

    def test_attributes_present_for_every_class(self):
        """Every catalog entry gets all three attributes, even with no related rows."""
        catalog = ClassSubject.objects.catalog(self.program)
        self.assertTrue(len(catalog) > 0)
        for cls in catalog:
            self.assertEqual(cls.media_count, 0)
            self.assertEqual(cls._studentapps_count, 0)
            self.assertEqual(cls._index_qsd, 0)


class CatalogSortFieldTagTest(ProgramFrameworkTest):
    """catalog_sort_fields parsing: whitespace, legacy names, removed fields."""

    def setUp(self):
        super().setUp(num_students=0, num_teachers=2, classes_per_teacher=1)
        cache.clear()

    def _catalog(self):
        return ClassSubject.objects.catalog(self.program)

    def test_legacy_sort_field_with_spaces(self):
        """Legacy field names and spaces after commas should both be handled."""
        Tag.setTag('catalog_sort_fields', target=self.program,
                   value='category__symbol, sections__meeting_times__start, id')

        catalog = self._catalog()
        self.assertTrue(len(catalog) > 0)
        #   The legacy name was translated, so the annotation is applied.
        self.assertTrue(hasattr(catalog[0], 'earliest_start'))
        class_ids = [cls.id for cls in catalog]
        self.assertEqual(len(class_ids), len(set(class_ids)),
                         "Translated ordering should not duplicate rows")

    def test_descending_legacy_sort_field(self):
        """'-sections__meeting_times__start' should translate too."""
        Tag.setTag('catalog_sort_fields', target=self.program,
                   value='-sections__meeting_times__start, id')

        catalog = self._catalog()
        self.assertTrue(len(catalog) > 0)
        self.assertTrue(hasattr(catalog[0], 'earliest_start'))

    def test_removed_sort_fields_are_ignored(self):
        """Fields that are no longer DB columns shouldn't take the catalog down."""
        Tag.setTag('catalog_sort_fields', target=self.program,
                   value='media_count, category__symbol, id')

        catalog = self._catalog()
        self.assertTrue(len(catalog) > 0)
        #   The remaining fields still sort the catalog.
        symbols_and_ids = [(cls.category.symbol, cls.id) for cls in catalog]
        self.assertEqual(symbols_and_ids, sorted(symbols_and_ids))

    def test_only_removed_sort_fields_falls_back_to_id(self):
        """If every configured field is unusable, fall back to ordering by id."""
        Tag.setTag('catalog_sort_fields', target=self.program,
                   value='media_count, _studentapps_count')

        catalog = self._catalog()
        self.assertTrue(len(catalog) > 0)
        class_ids = [cls.id for cls in catalog]
        self.assertEqual(class_ids, sorted(class_ids))
