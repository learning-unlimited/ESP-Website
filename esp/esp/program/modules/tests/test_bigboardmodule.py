from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.handlers.bigboardmodule import BigBoardModule
from esp.program.models import ProgramModule
import datetime

class BigBoardModuleTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        # Create a ProgramModule instance for BigBoardModule
        self.module_model, _ = ProgramModule.objects.get_or_create(
            handler='BigBoardModule',
            defaults={
                'link_title': 'Big Board',
                'admin_title': 'Big Board Admin',
                'module_type': 'manage',
                'seq': 10
            }
        )
        # Create the specific BigBoardModule handler instance
        self.bb_module = BigBoardModule.objects.create(
            program=self.program,
            module=self.module_model,
            seq=10
        )

    def test_chunk_times_basic(self):
        """Test the basic time-chunking logic used for graphs."""
        start = datetime.datetime(2026, 3, 1, 10, 0)
        end = datetime.datetime(2026, 3, 1, 13, 0)
        
        # Mock data: (metric, timestamp)
        times = [
            (1, datetime.datetime(2026, 3, 1, 10, 5)), # Hour 10
            (1, datetime.datetime(2026, 3, 1, 10, 15)), # Hour 10
            (1, datetime.datetime(2026, 3, 1, 11, 30)), # Hour 11
            (1, datetime.datetime(2026, 3, 1, 12, 45)), # Hour 12
        ]
        
        # Test non-cumulative
        result = self.bb_module.chunk_times(times, start, end, cumulative=False)
        # Expected: [0, 2, 1, 1] 
        # 10:00 -> 0 (nothing before start)
        # 11:00 -> 2 (10:05, 10:15)
        # 12:00 -> 1 (11:30)
        # 13:00 -> 1 (12:45)
        self.assertEqual(result, [0.0, 2.0, 1.0, 1.0])

        # Test cumulative
        result_cum = self.bb_module.chunk_times(times, start, end, cumulative=True)
        # Expected: [0, 2, 3, 4]
        self.assertEqual(result_cum, [0.0, 2.0, 3.0, 4.0])

    def test_num_active_users(self):
        """Test the active user count logic."""
        # This relies on Record objects. 
        # We can add some Record objects to our program and check the count.
        # Since this is a lightweight test, we'll verify it doesn't crash first.
        count = self.bb_module.num_active_users(self.program)
        self.assertIsInstance(count, int)
