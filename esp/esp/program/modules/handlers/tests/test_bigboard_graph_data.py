"""Tests for BigBoardModule.make_graph_data's trimming of time series.

The trim counts and the minimum series length are program tags, so admins can
set combinations that would leave a series with nothing in it.
"""
import datetime

from django.test import SimpleTestCase

from esp.program.modules.handlers.bigboardmodule import BigBoardModule


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

    def test_surviving_series_is_still_plotted(self):
        graph_data, start = BigBoardModule.make_graph_data(
            [series('short', 5), series('long', 20)], 6, 0, 5)
        self.assertEqual([d['description'] for d in graph_data], ['long'])
        self.assertIsNotNone(start)
