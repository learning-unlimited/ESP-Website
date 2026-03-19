
import json

from unittest.mock import patch, MagicMock

from esp.program.models import ProgramModule
from esp.program.modules.handlers.autoschedulerfrontendmodule import \
    AutoschedulerFrontendModule
from esp.program.controllers.autoscheduler.exceptions import SchedulingError
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser


class AutoschedulerFrontendModuleTest(ProgramFrameworkTest):
    """Tests for AutoschedulerFrontendModule (issue #4904)."""

    def setUp(self):
        super().setUp(modules=ProgramModule.objects.all())
        # Create an admin and log in
        self.adminUser, created = ESPUser.objects.get_or_create(
            username='sched_admin', first_name='Sched', last_name='Admin')
        self.adminUser.set_password('password')
        self.adminUser.save()
        self.adminUser.makeAdmin()
        self.client.login(username='sched_admin', password='password')
        self.url_base = self.program.getUrlBase()

    # ── Helper / meta tests ──────────────────────────────────────────

    def test_module_properties(self):
        props = AutoschedulerFrontendModule.module_properties()
        self.assertEqual(props['admin_title'], 'Autoscheduler Frontend')
        self.assertEqual(props['link_title'],
                         'Use the automatic scheduling tool')
        self.assertEqual(props['module_type'], 'manage')
        self.assertEqual(props['seq'], 50)
        self.assertEqual(props['choosable'], 2)

    def test_is_step_returns_false(self):
        module = AutoschedulerFrontendModule()
        self.assertFalse(module.isStep())

    def test_is_float(self):
        module = AutoschedulerFrontendModule()
        self.assertTrue(module.is_float('3.14'))
        self.assertTrue(module.is_float('0'))
        self.assertTrue(module.is_float('-1.5'))
        self.assertFalse(module.is_float('abc'))
        self.assertFalse(module.is_float(''))

    # ── autoscheduler (main_call) ────────────────────────────────────

    @patch('esp.program.modules.handlers.autoschedulerfrontendmodule'
           '.AutoschedulerController')
    def test_autoscheduler_main_call(self, MockController):
        MockController.constraint_options.return_value = {'c1': (True, 'desc')}
        MockController.scorer_options.return_value = {'s1': (1.0, 'desc')}
        MockController.resource_options.return_value = {'r1': (-1, 'spec')}
        MockController.search_options.return_value = {
            'depth': (1, 'Depth'), 'timeout': (10.0, 'Timeout')}

        url = '/manage/%s/autoscheduler' % self.url_base
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        MockController.constraint_options.assert_called_once_with(
            self.program)
        MockController.scorer_options.assert_called_once_with(self.program)
        MockController.resource_options.assert_called_once_with(self.program)
        MockController.search_options.assert_called_once_with(
            self.program, section=None)

    @patch('esp.program.modules.handlers.autoschedulerfrontendmodule'
           '.AutoschedulerController')
    def test_autoscheduler_scheduling_error(self, MockController):
        MockController.constraint_options.side_effect = \
            SchedulingError('No timeslots')

        url = '/manage/%s/autoscheduler' % self.url_base
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No timeslots', response.content)

    # ── autoscheduler_execute (aux_call) ─────────────────────────────

    @patch('esp.program.modules.handlers.autoschedulerfrontendmodule'
           '.AutoschedulerController')
    def test_autoscheduler_execute_success(self, MockController):
        mock_instance = MagicMock()
        MockController.return_value = mock_instance
        mock_instance.get_scheduling_info.return_value = [['info_row']]
        mock_instance.export_assignments.return_value = [
            [{'history': 'data'}, {}], {}]

        url = '/manage/%s/autoscheduler_execute' % self.url_base
        post_data = {
            'autoscheduler_constraints_lunch': 'True',
            'autoscheduler_scorers_happy': '2.5',
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('response', data)
        self.assertIn('info', data['response'][0])
        self.assertIn('autoscheduler_data', data['response'][0])

        # Verify the controller was instantiated with parsed options
        call_kwargs = MockController.call_args[1]
        self.assertIs(call_kwargs['constraints_lunch'], True)
        self.assertEqual(call_kwargs['scorers_happy'], 2.5)
        mock_instance.compute_assignments.assert_called_once()

    @patch('esp.program.modules.handlers.autoschedulerfrontendmodule'
           '.AutoschedulerController')
    def test_autoscheduler_execute_post_parsing(self, MockController):
        """Verify POST value coercion: True/False/None/float/string."""
        mock_instance = MagicMock()
        MockController.return_value = mock_instance
        mock_instance.get_scheduling_info.return_value = []
        mock_instance.export_assignments.return_value = [[], {}]

        url = '/manage/%s/autoscheduler_execute' % self.url_base
        post_data = {
            'autoscheduler_key_true': 'True',
            'autoscheduler_key_false': 'False',
            'autoscheduler_key_none': 'None',
            'autoscheduler_key_float': '3.14',
            'autoscheduler_key_str': 'hello',
            'non_prefixed_key': 'ignored',
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)

        call_kwargs = MockController.call_args[1]
        self.assertIs(call_kwargs['key_true'], True)
        self.assertIs(call_kwargs['key_false'], False)
        self.assertIsNone(call_kwargs['key_none'])
        self.assertEqual(call_kwargs['key_float'], 3.14)
        self.assertEqual(call_kwargs['key_str'], 'hello')
        self.assertNotIn('non_prefixed_key', call_kwargs)

    @patch('esp.program.modules.handlers.autoschedulerfrontendmodule'
           '.AutoschedulerController')
    def test_autoscheduler_execute_scheduling_error(self, MockController):
        MockController.side_effect = SchedulingError('bad schedule')

        url = '/manage/%s/autoscheduler_execute' % self.url_base
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['response'][0]['error_msg'], 'bad schedule')

    @patch('esp.program.modules.handlers.autoschedulerfrontendmodule'
           '.AutoschedulerController')
    def test_autoscheduler_execute_value_error(self, MockController):
        MockController.side_effect = ValueError('invalid param')

        url = '/manage/%s/autoscheduler_execute' % self.url_base
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['response'][0]['error_msg'], 'invalid param')

    # ── autoscheduler_save (aux_call) ────────────────────────────────

    @patch('esp.program.modules.handlers.autoschedulerfrontendmodule'
           '.AutoschedulerController')
    def test_autoscheduler_save_success(self, MockController):
        mock_instance = MagicMock()
        MockController.return_value = mock_instance

        payload = json.dumps([[{'history': 'data'}, {}], {'opt': 'val'}])
        url = '/manage/%s/autoscheduler_save' % self.url_base
        response = self.client.post(url, {'autoscheduler_data': payload})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['response'][0]['success'], 'yes')

        MockController.assert_called_once()
        mock_instance.import_assignments.assert_called_once()
        mock_instance.save_assignments.assert_called_once()

    def test_autoscheduler_save_missing_data(self):
        url = '/manage/%s/autoscheduler_save' % self.url_base
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('error_msg', data['response'][0])
        self.assertIn('missing', data['response'][0]['error_msg'])

    @patch('esp.program.modules.handlers.autoschedulerfrontendmodule'
           '.AutoschedulerController')
    def test_autoscheduler_save_scheduling_error(self, MockController):
        mock_instance = MagicMock()
        MockController.return_value = mock_instance
        mock_instance.save_assignments.side_effect = \
            SchedulingError('section moved')

        payload = json.dumps([[{}, {}], {}])
        url = '/manage/%s/autoscheduler_save' % self.url_base
        response = self.client.post(url, {'autoscheduler_data': payload})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['response'][0]['error_msg'], 'section moved')

    # ── autoscheduler_clear (aux_call) ───────────────────────────────

    def test_autoscheduler_clear(self):
        url = '/manage/%s/autoscheduler_clear' % self.url_base
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['response'][0]['success'], 'yes')
