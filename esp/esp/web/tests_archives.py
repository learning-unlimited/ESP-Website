"""
Unit tests for esp/web/views/archives.py

Covers:
  - ArchiveFilter class
  - compute_range()
  - extract_criteria()
  - filter_archive()
  - title_heading()
  - archive_classes() view
  - archive_teachers() view
  - archive_programs() view

PR 4/6 — esp/web module coverage improvement
"""

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from esp.tests.util import CacheFlushTestCase as TestCase

from esp.web.views.archives import (
    ArchiveFilter,
    compute_range,
    extract_criteria,
    filter_archive,
    title_heading,
    archive_classes,
    archive_teachers,
    archive_programs,
)
from esp.program.models import ArchiveClass


# ---------------------------------------------------------------------------
# ArchiveFilter
# ---------------------------------------------------------------------------

class ArchiveFilterTest(TestCase):

    def test_default_values(self):
        f = ArchiveFilter()
        self.assertEqual(f.category, '')
        self.assertEqual(f.options, '')

    def test_custom_values(self):
        f = ArchiveFilter(category='year', options='2023')
        self.assertEqual(f.category, 'year')
        self.assertEqual(f.options, '2023')

    def test_str_representation(self):
        f = ArchiveFilter(category='program', options='Splash')
        self.assertEqual(str(f), 'program, Splash')

    def test_values_cast_to_str(self):
        f = ArchiveFilter(category=2024, options=10)
        self.assertEqual(f.category, '2024')
        self.assertEqual(f.options, '10')


# ---------------------------------------------------------------------------
# compute_range()
# ---------------------------------------------------------------------------

class ComputeRangeTest(TestCase):

    def test_fewer_records_than_default_returns_none_end(self):
        result = compute_range({}, 5)
        self.assertEqual(result['start'], 0)
        self.assertIsNone(result['end'])

    def test_more_records_defaults_to_10(self):
        result = compute_range({}, 50)
        self.assertEqual(result['start'], 0)
        self.assertEqual(result['end'], 10)

    def test_show_all(self):
        result = compute_range({'max_num_results': 'Show all'}, 50)
        self.assertEqual(result['end'], 50)

    def test_explicit_max_num_results(self):
        result = compute_range({'max_num_results': '25'}, 100)
        self.assertEqual(result['start'], 0)
        self.assertEqual(result['end'], 25)

    def test_explicit_results_start(self):
        result = compute_range({'results_start': '20', 'max_num_results': '10'}, 100)
        self.assertEqual(result['start'], 20)
        self.assertEqual(result['end'], 30)

    def test_explicit_results_end(self):
        result = compute_range({'results_end': '40'}, 100)
        self.assertEqual(result['end'], 40)

    def test_results_start_and_end_explicit(self):
        result = compute_range({'results_start': '10', 'results_end': '20'}, 100)
        self.assertEqual(result['start'], 10)
        self.assertEqual(result['end'], 20)

    def test_exactly_default_num_records_no_end(self):
        # exactly 10 records → not > default, so end is None
        result = compute_range({}, 10)
        self.assertIsNone(result['end'])


# ---------------------------------------------------------------------------
# extract_criteria()
# ---------------------------------------------------------------------------

class ExtractCriteriaTest(TestCase):

    def test_filter_key_extracted(self):
        postvars = {'filter_year': '2023'}
        criteria = extract_criteria(postvars)
        self.assertEqual(len(criteria), 1)
        self.assertEqual(criteria[0].category, 'year')
        self.assertEqual(criteria[0].options, '2023')

    def test_multiple_filter_keys(self):
        postvars = {'filter_year': '2022', 'filter_program': 'Splash'}
        criteria = extract_criteria(postvars)
        categories = {c.category for c in criteria}
        self.assertEqual(categories, {'year', 'program'})

    def test_non_filter_keys_ignored(self):
        postvars = {'max_num_results': '10', 'filter_year': '2023'}
        criteria = extract_criteria(postvars)
        self.assertEqual(len(criteria), 1)
        self.assertEqual(criteria[0].category, 'year')

    def test_empty_value_excluded(self):
        postvars = {'filter_year': ''}
        criteria = extract_criteria(postvars)
        self.assertEqual(len(criteria), 0)

    def test_empty_postvars_returns_empty(self):
        criteria = extract_criteria({})
        self.assertEqual(criteria, [])

    def test_filter_prefix_alone_ignored(self):
        # key is exactly 'filter_' — len(key) == 7, not > 7
        postvars = {'filter_': 'value'}
        criteria = extract_criteria(postvars)
        self.assertEqual(len(criteria), 0)


# ---------------------------------------------------------------------------
# filter_archive()
# ---------------------------------------------------------------------------

class FilterArchiveTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        ArchiveClass.objects.create(
            year='2022', program='Splash', title='Algebra',
            category='M', teacher='Alice', description='Math class',
            teacher_ids='',
        )
        ArchiveClass.objects.create(
            year='2023', program='HSSP', title='Biology',
            category='S', teacher='Bob', description='Science class',
            teacher_ids='',
        )
        ArchiveClass.objects.create(
            year='2022', program='Splash', title='Chemistry',
            category='S', teacher='Carol', description='Chemistry intro',
            teacher_ids='',
        )

    def test_no_criteria_returns_all(self):
        result = filter_archive(ArchiveClass.objects.all(), [])
        self.assertEqual(result.count(), 3)

    def test_filter_by_year(self):
        criteria = [ArchiveFilter(category='year', options='2022')]
        result = filter_archive(ArchiveClass.objects.all(), criteria)
        self.assertEqual(result.count(), 2)

    def test_filter_by_program(self):
        criteria = [ArchiveFilter(category='program', options='HSSP')]
        result = filter_archive(ArchiveClass.objects.all(), criteria)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().title, 'Biology')

    def test_filter_by_title_startswith(self):
        criteria = [ArchiveFilter(category='title', options='A')]
        result = filter_archive(ArchiveClass.objects.all(), criteria)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().title, 'Algebra')

    def test_filter_by_category(self):
        criteria = [ArchiveFilter(category='category', options='S')]
        result = filter_archive(ArchiveClass.objects.all(), criteria)
        self.assertEqual(result.count(), 2)

    def test_filter_by_teacher(self):
        criteria = [ArchiveFilter(category='teacher', options='Alice')]
        result = filter_archive(ArchiveClass.objects.all(), criteria)
        self.assertEqual(result.count(), 1)

    def test_filter_by_description(self):
        criteria = [ArchiveFilter(category='description', options='Science')]
        result = filter_archive(ArchiveClass.objects.all(), criteria)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().teacher, 'Bob')

    def test_multiple_criteria_combined(self):
        criteria = [
            ArchiveFilter(category='year', options='2022'),
            ArchiveFilter(category='program', options='Splash'),
        ]
        result = filter_archive(ArchiveClass.objects.all(), criteria)
        self.assertEqual(result.count(), 2)

    def test_no_match_returns_empty(self):
        criteria = [ArchiveFilter(category='year', options='1990')]
        result = filter_archive(ArchiveClass.objects.all(), criteria)
        self.assertEqual(result.count(), 0)


# ---------------------------------------------------------------------------
# title_heading()
# ---------------------------------------------------------------------------

class TitleHeadingTest(TestCase):

    def test_non_empty_returns_first_char(self):
        self.assertEqual(title_heading('Algebra'), 'A')

    def test_empty_returns_no_title(self):
        self.assertEqual(title_heading(''), '[No Title]')

    def test_lowercase_first_char(self):
        self.assertEqual(title_heading('biology'), 'b')

    def test_single_char(self):
        self.assertEqual(title_heading('X'), 'X')


# ---------------------------------------------------------------------------
# archive_classes() view
# ---------------------------------------------------------------------------

class ArchiveClassesViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        ArchiveClass.objects.create(
            year='2023', program='Splash', title='Robotics',
            category='E', teacher='Dave', description='Build robots',
            teacher_ids='',
        )

    def test_get_returns_200(self):
        request = self.factory.get('/archives/classes/')
        request.user = AnonymousUser()
        response = archive_classes(request, None, None)
        self.assertEqual(response.status_code, 200)

    def test_get_with_category_and_options(self):
        request = self.factory.get('/archives/classes/year/2023/')
        request.user = AnonymousUser()
        response = archive_classes(request, 'year', '2023')
        self.assertEqual(response.status_code, 200)

    def test_post_with_filter_returns_200(self):
        request = self.factory.post('/archives/classes/', {
            'filter_year': '2023',
            'newparam': 'year',
        })
        request.user = AnonymousUser()
        response = archive_classes(request, None, None)
        self.assertEqual(response.status_code, 200)

    def test_no_results_still_200(self):
        request = self.factory.get('/archives/classes/')
        request.user = AnonymousUser()
        ArchiveClass.objects.all().delete()
        response = archive_classes(request, None, None)
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# archive_teachers() view
# ---------------------------------------------------------------------------

class ArchiveTeachersViewTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_200(self):
        request = self.factory.get('/archives/teachers/')
        request.user = AnonymousUser()
        response = archive_teachers(request, None, None)
        self.assertEqual(response.status_code, 200)

    def test_with_category_options(self):
        request = self.factory.get('/archives/teachers/year/2023/')
        request.user = AnonymousUser()
        response = archive_teachers(request, 'year', '2023')
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# archive_programs() view
# ---------------------------------------------------------------------------

class ArchiveProgramsViewTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_200(self):
        request = self.factory.get('/archives/programs/')
        request.user = AnonymousUser()
        response = archive_programs(request, None, None)
        self.assertEqual(response.status_code, 200)

    def test_with_category_options(self):
        request = self.factory.get('/archives/programs/year/2022/')
        request.user = AnonymousUser()
        response = archive_programs(request, 'year', '2022')
        self.assertEqual(response.status_code, 200)
