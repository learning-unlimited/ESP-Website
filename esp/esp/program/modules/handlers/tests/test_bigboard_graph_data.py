"""Tests for BigBoardModule.make_graph_data's trimming of time series.

The trim counts and the minimum series length are program tags, so admins can
set combinations that would leave a series with nothing in it.
"""
import datetime

from django.test import SimpleTestCase, TestCase

from esp.program.models import Program
from esp.program.modules.handlers.bigboardmodule import BigBoardModule
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag


def series(name, count, cumulative=True):
    base = datetime.datetime.now() - datetime.timedelta(days=count)
    return (name, [(1, base + datetime.timedelta(days=i)) for i in range(count)], cumulative)


class MakeGraphDataTrimTest(SimpleTestCase):
    def test_defaults_keep_a_long_enough_series(self):
        graph_data, start = BigBoardModule.make_graph_data([series('enrolled', 10)], 4, 0, 5)
        self.assertEqual(len(graph_data), 1)
        self.assertIsNotNone(start)

    def test_series_shorter_than_the_cutoff_is_dropped(self):
        graph_data, start = BigBoardModule.make_graph_data([series('enrolled', 3)], 0, 0, 5)
        self.assertEqual(graph_data, [])
        self.assertIsNone(start)

    def test_trimming_away_the_whole_series_does_not_raise(self):
        # Each of these leaves nothing after trimming; before, the empty slice
        # was indexed at [0] and took down the whole big board page
        for drop_beg, drop_end in [(5, 0), (0, 5), (3, 2), (10, 10)]:
            with self.subTest(drop_beg=drop_beg, drop_end=drop_end):
                graph_data, start = BigBoardModule.make_graph_data(
                    [series('enrolled', 5)], drop_beg, drop_end, 5)
                self.assertEqual(graph_data, [])
                self.assertIsNone(start)

    def test_undated_points_are_ignored(self):
        """Registration timestamps are nullable; an undated point has no place
        on a time axis and must not take down the page."""
        name, times, cumulative = series('enrolled', 6)
        with_gap = [(1, None)] + times + [(1, None)]
        graph_data, start = BigBoardModule.make_graph_data([(name, with_gap, cumulative)], 0, 0, 5)
        self.assertEqual(len(graph_data), 1)
        self.assertIsNotNone(start)

    def test_series_of_only_undated_points_is_dropped(self):
        graph_data, start = BigBoardModule.make_graph_data(
            [('enrolled', [(1, None)] * 8, True)], 0, 0, 5)
        self.assertEqual(graph_data, [])
        self.assertIsNone(start)

    def test_surviving_series_is_still_plotted(self):
        graph_data, start = BigBoardModule.make_graph_data(
            [series('short', 5), series('long', 20)], 6, 0, 5)
        self.assertEqual([d['description'] for d in graph_data], ['long'])
        self.assertIsNotNone(start)


class GraphSettingTest(TestCase):
    """The Tag admin accepts free text, so a stray value must not 500 the page."""

    def setUp(self):
        Tag._getTag.delete_all()
        self.addCleanup(Tag._getTag.delete_all)
        self.program = Program.objects.create(name='Graph Tags', grade_min=7, grade_max=12)

    def test_defaults_when_unset(self):
        self.assertEqual(
            [BigBoardModule.graph_setting(k, self.program) for k in
             ('bigboard_graph_drop_beg', 'bigboard_graph_drop_end', 'bigboard_graph_min_points')],
            [4, 0, 5])

    def test_configured_value_is_used(self):
        Tag.setTag('bigboard_graph_drop_beg', target=self.program, value='7')
        self.assertEqual(BigBoardModule.graph_setting('bigboard_graph_drop_beg', self.program), 7)

    def test_unusable_values_fall_back_to_the_default(self):
        for value in ('', '   ', 'four', '3.5'):
            with self.subTest(value=value):
                Tag.setTag('bigboard_graph_drop_beg', target=self.program, value=value)
                self.assertEqual(
                    BigBoardModule.graph_setting('bigboard_graph_drop_beg', self.program), 4)

    def test_negative_values_are_clamped(self):
        Tag.setTag('bigboard_graph_drop_end', target=self.program, value='-5')
        self.assertEqual(BigBoardModule.graph_setting('bigboard_graph_drop_end', self.program), 0)


class TimesLotteryUndatedTest(ProgramFrameworkTest):
    """times_lottery sorts before make_graph_data sees anything, so an undated
    record has to be excluded by the query itself."""

    def setUp(self):
        super().setUp(num_timeslots=2, num_teachers=1, classes_per_teacher=1,
                      sections_per_class=1, num_rooms=1, num_students=2)
        self._flush_cache()

    def test_undated_lottery_records_do_not_raise(self):
        from esp.program.models import (
            RegistrationType, StudentRegistration, StudentSubjectInterest)
        priority, _ = RegistrationType.objects.get_or_create(
            name='Priority/1', defaults={'category': 'student'})
        section = self.program.classes()[0].sections.first()
        module = [m for m in self.program.getModules()
                  if m.__class__.__name__ == 'BigBoardModule'][0]

        dated = StudentRegistration.objects.create(
            user=self.students[0], section=section, relationship=priority)
        dated.start_date = datetime.datetime.now() - datetime.timedelta(days=1)
        dated.save()

        undated = StudentRegistration.objects.create(
            user=self.students[1], section=section, relationship=priority)
        undated.start_date = None
        undated.save()

        # times_lottery merges two querysets; cover the interest side too, so
        # dropping either exclude() is caught
        undated_interest = StudentSubjectInterest.objects.create(
            user=self.students[1], subject=self.program.classes()[0])
        undated_interest.start_date = None
        undated_interest.save()

        self._flush_cache()
        times = module.times_lottery(self.program)   # raised TypeError before
        self.assertEqual(len(times), 1)
        self.assertTrue(all(t is not None for t in times))
