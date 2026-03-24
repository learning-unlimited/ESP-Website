import datetime
from django.test import TestCase
from esp.program.modules.handlers.bigboardmodule import BigBoardModule

class BigBoardModuleTests(TestCase):
    
    def test_module_properties(self):
        """Test that the static properties are correctly defined."""
        props = BigBoardModule.module_properties()
        self.assertEqual(props["admin_title"], "Student Registration Big Board")
        self.assertEqual(props["module_type"], "manage")
        self.assertEqual(props["seq"], 10)
        self.assertEqual(props["choosable"], 1)

    def test_isStep(self):
        """Test that the module is not considered a sequential step."""
        module = BigBoardModule()
        self.assertFalse(module.isStep())

    def test_load_averages_failure(self):
        """Test that load_averages returns an empty list if the system call fails."""
        # The easiest way to test the failure state without mocking the OS 
        # is to verify it handles the exception gracefully if run in a restricted environment
        module = BigBoardModule()
        try:
            result = module.load_averages()
            # It might succeed on your local machine, or fail in Docker. 
            # We just want to ensure it returns a list either way.
            self.assertIsInstance(result, list)
        except Exception as e:
            self.fail(f"load_averages raised an exception instead of catching it: {e}")

    def test_chunk_times_cumulative(self):
        """Test the data bucketing logic with cumulative counting."""
        # Create a timeline starting at noon today
        start = datetime.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        end = start + datetime.timedelta(hours=3)
        delta = datetime.timedelta(hours=1)
        
        # 1 user at 12:30, 2 users at 1:30, 0 users at 2:30
        times = [
            (1, start + datetime.timedelta(minutes=30)),
            (2, start + datetime.timedelta(minutes=90)),
        ]
        
        chunks = BigBoardModule.chunk_times(times, start, end, delta, cumulative=True)
        
        # Expected: 
        # Hour 1 (12:00): 0 users before this
        # Hour 2 (1:00): 1 user before this
        # Hour 3 (2:00): 3 users before this (1 + 2)
        # Hour 4 (3:00): 3 users before this
        self.assertEqual(chunks, [0.0, 1.0, 3.0, 3.0])

    def test_chunk_times_non_cumulative(self):
        """Test the data bucketing logic with per-hour counting."""
        start = datetime.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        end = start + datetime.timedelta(hours=3)
        delta = datetime.timedelta(hours=1)
        
        # 1 user at 12:30, 2 users at 1:30, 0 users at 2:30
        times = [
            (1, start + datetime.timedelta(minutes=30)),
            (2, start + datetime.timedelta(minutes=90)),
        ]
        
        chunks = BigBoardModule.chunk_times(times, start, end, delta, cumulative=False)
        
        # Expected:
        # Hour 1 (12:00): 0 users
        # Hour 2 (1:00): 1 user during the last hour
        # Hour 3 (2:00): 2 users during the last hour
        # Hour 4 (3:00): 0 users during the last hour
        self.assertEqual(chunks, [0.0, 1.0, 2.0, 0.0])

    def test_make_graph_data_filtering_and_formatting(self):
        """Test that make_graph_data correctly filters short series and formats output."""
        # Create a base time for today at noon
        base_time = datetime.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        
        # Series 1: Has 3 data points
        times1 = [
            (1, base_time + datetime.timedelta(hours=1)),
            (1, base_time + datetime.timedelta(hours=2)),
            (1, base_time + datetime.timedelta(hours=3)),
        ]
        
        # Series 2: Has only 1 data point
        times2 = [
            (1, base_time + datetime.timedelta(hours=1)),
        ]
        
        # Format: (description, times, cumulative)
        timess = [
            ("Valid Series", times1, True),
            ("Short Series", times2, True),
        ]
        
        # Run graph generation with a cutoff of 2. 
        # "Short Series" only has 1 item, so it should be completely removed.
        graph_data, graph_start = BigBoardModule.make_graph_data(
            timess, drop_beg=0, drop_end=0, cutoff=2
        )
        
        # 1. Verify filtering worked (only 1 series should remain)
        self.assertEqual(len(graph_data), 1)
        self.assertEqual(graph_data[0]["description"], "Valid Series")
        
        # 2. Verify the start time was rounded down to midnight of that day
        expected_midnight = base_time.replace(hour=0, minute=0, second=0, microsecond=0)
        self.assertEqual(graph_start, expected_midnight)
        
        # 3. Verify the data array exists and has elements
        self.assertTrue(len(graph_data[0]["data"]) > 0)

    def test_make_graph_data_empty(self):
        """Test graph generation handles completely empty data safely."""
        graph_data, graph_start = BigBoardModule.make_graph_data([])
        self.assertEqual(graph_data, [])
        self.assertIsNone(graph_start)