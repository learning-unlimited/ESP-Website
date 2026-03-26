from django.test import TestCase, RequestFactory
from unittest.mock import patch, MagicMock
from esp.program.modules.handlers.autoschedulerfrontendmodule import AutoschedulerFrontendModule
from esp.program.controllers.autoscheduler.exceptions import SchedulingError
import json

class TestAutoschedulerFrontendModule(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.module = AutoschedulerFrontendModule()
        self.prog = MagicMock()

    @patch('esp.program.modules.handlers.autoschedulerfrontendmodule.AutoschedulerController')
    def test_autoscheduler_execute_parsing(self, MockController):
        # Setup mock controller
        mock_instance = MockController.return_value
        mock_instance.get_scheduling_info.return_value = {}
        mock_instance.export_assignments.return_value = [{}, {}]
        
        # Simulate request with floating-point configs and string-based booleans
        request = self.factory.post('/execute', {
            'autoscheduler_use_heuristics': 'True',
            'autoscheduler_allow_overrides': 'False',
            'autoscheduler_null_value': 'None',
            'autoscheduler_alpha_weight': '0.75',
            'autoscheduler_beta_weight': '1.5',
            'autoscheduler_random_string': 'hello'
        })
        
        # Bypass @needs_admin and @json_response decorators to test only parsing logic
        undecorated_execute = AutoschedulerFrontendModule.autoscheduler_execute.__wrapped__
        response = undecorated_execute(self.module, request, 'manage', 'one', 'two', 'module', 'extra', self.prog)
        
        # Verify AutoschedulerController was called with appropriately cast types
        MockController.assert_called_once_with(self.prog, 
            use_heuristics=True,
            allow_overrides=False,
            null_value=None,
            alpha_weight=0.75,
            beta_weight=1.5,
            random_string='hello'
        )
        self.assertIn('response', response)

    def test_autoscheduler_save_malformed_json(self):
        # Simulate request with malformed autoscheduler_data payload
        request = self.factory.post('/save', {
            'autoscheduler_data': '{"malformed": json'
        })
        
        undecorated_save = AutoschedulerFrontendModule.autoscheduler_save.__wrapped__
        response = undecorated_save(self.module, request, 'manage', 'one', 'two', 'module', 'extra', self.prog)
        
        self.assertIn('response', response)
        self.assertEqual(len(response['response']), 1)
        self.assertIn('error_msg', response['response'][0])

    @patch('esp.program.modules.handlers.autoschedulerfrontendmodule.AutoschedulerController')
    def test_autoscheduler_save_scheduling_error(self, MockController):
        # Simulate scheduler throwing a SchedulingError
        MockController.side_effect = SchedulingError("Graceful constraint failure")
        
        request = self.factory.post('/save', {
            'autoscheduler_data': json.dumps([{}, {}])
        })
        
        undecorated_save = AutoschedulerFrontendModule.autoscheduler_save.__wrapped__
        response = undecorated_save(self.module, request, 'manage', 'one', 'two', 'module', 'extra', self.prog)
        
        self.assertEqual(response['response'][0]['error_msg'], "Graceful constraint failure")
