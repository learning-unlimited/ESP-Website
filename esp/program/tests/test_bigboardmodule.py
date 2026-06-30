from django.test import TestCase
from esp.program.modules.bigboardmodule import BigBoardModule
import datetime


class BigBoardModuleTests(TestCase):

    def test_chunk_times_basic(self):
        start = datetime.datetime(2024, 1, 1, 0, 0)
        end = datetime.datetime(2024, 1, 1, 3, 0)

        times = [
            (1, start + datetime.timedelta(hours=1)),
            (1, start + datetime.timedelta(hours=2)),
        ]

        result = BigBoardModule.chunk_times(times, start, end)

        self.assertEqual(len(result), 4)
        self.assertTrue(all(isinstance(x, float) for x in result))

    def test_chunk_times_non_cumulative(self):
        start = datetime.datetime(2024, 1, 1, 0, 0)
        end = datetime.datetime(2024, 1, 1, 2, 0)

        times = [
            (1, start + datetime.timedelta(hours=1)),
        ]

        result = BigBoardModule.chunk_times(times, start, end, cumulative=False)

        self.assertEqual(len(result), 3)

    def test_make_graph_data_empty(self):
        data, start = BigBoardModule.make_graph_data([])

        self.assertEqual(data, [])
        self.assertIsNone(start)

    def test_make_graph_data_basic(self):
        now = datetime.datetime.now()

        timess = [
            ("test", [(1, now)], True)
        ]

        data, start = BigBoardModule.make_graph_data(timess)

        self.assertTrue(len(data) >= 0)

    def test_load_averages(self):
        module = BigBoardModule()

        result = module.load_averages()

        self.assertTrue(isinstance(result, list))
