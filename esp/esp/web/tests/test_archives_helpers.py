from esp.tests.util import CacheFlushTestCase as TestCase
from esp.web.views.archives import (
    ArchiveFilter,
    compute_range,
    extract_criteria,
    filter_archive,
    title_heading,
)


class ArchivesHelpersTest(TestCase):
    """Unit tests for helper functions in archive view logic."""

    class RecordingQuerySet:
        def __init__(self):
            self.calls = []

        def filter(self, **kwargs):
            self.calls.append(kwargs)
            return self

    def test_compute_range_defaults(self):
        result = compute_range({}, 50)
        self.assertEqual(result, {"start": 0, "end": 10})

    def test_compute_range_explicit_bounds(self):
        result = compute_range({"results_start": "15", "results_end": "30"}, 50)
        self.assertEqual(result, {"start": 15, "end": 30})

    def test_compute_range_show_all(self):
        result = compute_range({"max_num_results": "Show all"}, 23)
        self.assertEqual(result, {"start": 0, "end": 23})

    def test_compute_range_custom_size(self):
        result = compute_range({"results_start": "5", "max_num_results": "25"}, 100)
        self.assertEqual(result, {"start": 5, "end": 30})

    def test_extract_criteria(self):
        postvars = {
            "filter_year": "2024",
            "filter_program": "Splash",
            "filter_teacher": "",
            "not_a_filter": "x",
        }
        criteria = extract_criteria(postvars)
        self.assertEqual(len(criteria), 2)
        self.assertEqual((criteria[0].category, criteria[0].options), ("year", "2024"))
        self.assertEqual((criteria[1].category, criteria[1].options), ("program", "Splash"))

    def test_title_heading(self):
        self.assertEqual(title_heading("Algebra"), "A")
        self.assertEqual(title_heading(""), "[No Title]")

    def test_filter_archive_applies_all_criteria(self):
        qs = self.RecordingQuerySet()
        criteria = [
            ArchiveFilter("year", "2024"),
            ArchiveFilter("program", "Splash"),
            ArchiveFilter("title", "A"),
            ArchiveFilter("category", "Math"),
            ArchiveFilter("teacher", "Smith"),
            ArchiveFilter("description", "fun"),
        ]
        result = filter_archive(qs, criteria)

        self.assertIs(result, qs)
        self.assertEqual(
            qs.calls,
            [
                {"year": "2024"},
                {"program__iexact": "Splash"},
                {"title__istartswith": "A"},
                {"category__istartswith": "Math"},
                {"teacher__icontains": "Smith"},
                {"description__icontains": "fun"},
            ],
        )
