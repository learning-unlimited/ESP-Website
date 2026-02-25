from unittest import TestCase
from unittest.mock import MagicMock, patch
from esp.users.controllers.usersearch import UserSearchController
from esp.program.modules.handlers.listgenmodule import ListGenModule
from esp.middleware import ESPError

class UserSearchErrorHandlingTest(TestCase):
    def setUp(self):
        self.controller = UserSearchController()
        self.program = MagicMock()
        self.request = MagicMock()

    @patch('esp.users.controllers.usersearch.render_to_response')
    @patch('esp.program.modules.handlers.listgenmodule.ListGenModule.processPost')
    @patch.object(UserSearchController, 'filter_from_postdata')
    def test_create_filter_catches_esperror(self, mock_filter, mock_process_post, mock_render):
        # Setup
        self.request.method = 'POST'
        mock_process_post.return_value = {'base_list': 'test', 'recipient_type': 'Student'}
        mock_filter.side_effect = ESPError("Invalid user ID", log=False)
        mock_render.return_value = "rendered_response"
        # Execute
        add_to_context = {}
        response, found = self.controller.create_filter(
            self.request, self.program, add_to_context=add_to_context
        )
        # Verify
        self.assertFalse(found)
        self.assertEqual(add_to_context['error'], "Invalid user ID")
        mock_render.assert_called()

    @patch('esp.program.modules.handlers.listgenmodule.render_to_response')
    @patch('esp.program.modules.handlers.listgenmodule.ListGenModule.processPost')
    @patch.object(UserSearchController, 'filter_from_postdata')
    @patch.object(UserSearchController, 'prepare_context')
    def test_listgen_selectlist_catches_esperror(self, mock_prepare, mock_filter, mock_process_post, mock_render):
        # Setup
        module = ListGenModule(self.program, None)
        self.request.method = 'POST'
        mock_process_post.return_value = {'some': 'data'}
        mock_filter.side_effect = ESPError("Calculation error", log=False)
        mock_prepare.return_value = {'prepared': 'context'}
        mock_render.return_value = "rendered_error_page"
        # Execute
        response = module.selectList(self.request, None, None, None, None, None, self.program)
        # Verify
        mock_render.assert_called()
        args, kwargs = mock_render.call_args
        context = args[2]
        self.assertEqual(context['error'], "Calculation error")
        self.assertEqual(response, "rendered_error_page")
