from __future__ import absolute_import
import json
from unittest.mock import patch, MagicMock

from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser


class LotteryFrontendModuleTest(ProgramFrameworkTest):
    """Tests for LotteryFrontendModule admin HTTP interface (issue #4953).

    The underlying LotteryAssignmentController algorithm is already tested by
    LSRAssignmentTest in esp/esp/program/tests.py.  These tests focus on the
    HTTP views that connect the admin UI to that controller.
    """

    def setUp(self, *args, **kwargs):
        super(LotteryFrontendModuleTest, self).setUp(*args, **kwargs)
        self.admin, _ = ESPUser.objects.get_or_create(
            username='lottery_admin_test',
            defaults={'first_name': 'Lottery', 'last_name': 'Admin',
                      'email': 'lottery_admin@test.learningu.org'},
        )
        self.admin.set_password('password')
        self.admin.makeAdmin()
        self.admin.save()

    def _manage_url(self, action):
        return '/manage/{}/{}'.format(self.program.url, action)

    # ------------------------------------------------------------------
    # lottery (main_call)
    # ------------------------------------------------------------------

    def test_lottery_page_loads(self):
        """The lottery management page returns 200 for admins."""
        self.client.login(username='lottery_admin_test', password='password')
        response = self.client.get(self._manage_url('lottery'))
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # lottery_execute (aux_call)
    # ------------------------------------------------------------------

    @patch('esp.program.modules.handlers.lotteryfrontendmodule.LotteryAssignmentController')
    def test_lottery_execute_success(self, MockLAC):
        """lottery_execute returns stats and lottery_data on success."""
        mock_instance = MockLAC.return_value
        mock_instance.compute_stats.return_value = {}
        mock_instance.extract_stats.return_value = {'num_enrolled': 5}
        mock_instance.export_assignments.return_value = {'assignments': []}

        self.client.login(username='lottery_admin_test', password='password')
        response = self.client.post(
            self._manage_url('lottery_execute'),
            {'lottery_num_iterations': '100', 'lottery_fillrate': '0.9'},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('response', data)
        result = data['response'][0]
        self.assertIn('stats', result)
        self.assertIn('lottery_data', result)

    @patch('esp.program.modules.handlers.lotteryfrontendmodule.LotteryAssignmentController')
    def test_lottery_execute_lottery_exception(self, MockLAC):
        """lottery_execute returns error_msg JSON when LotteryException is raised."""
        from esp.program.controllers.lottery import LotteryException
        mock_instance = MockLAC.return_value
        mock_instance.compute_assignments.side_effect = LotteryException(
            'test lottery failure'
        )

        self.client.login(username='lottery_admin_test', password='password')
        response = self.client.post(
            self._manage_url('lottery_execute'),
            {},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('response', data)
        self.assertIn('error_msg', data['response'][0])
        self.assertIn('test lottery failure', data['response'][0]['error_msg'])

    @patch('esp.program.modules.handlers.lotteryfrontendmodule.LotteryAssignmentController')
    def test_lottery_execute_bool_option_coercion(self, MockLAC):
        """lottery_execute correctly coerces 'True'/'False' POST strings to booleans."""
        mock_instance = MockLAC.return_value
        mock_instance.compute_stats.return_value = {}
        mock_instance.extract_stats.return_value = {}
        mock_instance.export_assignments.return_value = {}

        self.client.login(username='lottery_admin_test', password='password')
        self.client.post(
            self._manage_url('lottery_execute'),
            {'lottery_use_priority': 'True', 'lottery_check_sat': 'False'},
        )
        # Verify controller was instantiated with properly-typed kwargs
        call_kwargs = MockLAC.call_args[1]
        self.assertIs(call_kwargs.get('use_priority'), True)
        self.assertIs(call_kwargs.get('check_sat'), False)

    # ------------------------------------------------------------------
    # lottery_save (aux_call)
    # ------------------------------------------------------------------

    def test_lottery_save_missing_lottery_data(self):
        """lottery_save returns error JSON when lottery_data is absent from POST."""
        self.client.login(username='lottery_admin_test', password='password')
        response = self.client.post(self._manage_url('lottery_save'), {})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('response', data)
        self.assertIn('error', data['response'][0])
        self.assertNotEqual(data['response'][0]['error'], '')

    @patch('esp.program.modules.handlers.lotteryfrontendmodule.LotteryAssignmentController')
    def test_lottery_save_success(self, MockLAC):
        """lottery_save calls import_assignments + save_assignments and returns success."""
        mock_instance = MockLAC.return_value

        self.client.login(username='lottery_admin_test', password='password')
        response = self.client.post(
            self._manage_url('lottery_save'),
            {'lottery_data': json.dumps({'assignments': []})},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('response', data)
        self.assertEqual(data['response'][0].get('success'), 'yes')
        mock_instance.import_assignments.assert_called_once()
        mock_instance.save_assignments.assert_called_once()
