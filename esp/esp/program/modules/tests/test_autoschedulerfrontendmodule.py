"""Tests for esp.program.modules.handlers.autoschedulerfrontendmodule"""

import json
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from esp.program.controllers.autoscheduler.exceptions import SchedulingError
from esp.program.models import Program, ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.program.modules.handlers.autoschedulerfrontendmodule import (
    AutoschedulerFrontendModule,
)
from esp.users.models import ESPUser


class AutoschedulerFrontendModuleTestCase(TestCase):
    """Unit tests for AutoschedulerFrontendModule."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.admin_user = ESPUser.objects.create_user(
            username="sched_admin",
            password="password",
            email="admin@test.com",
            first_name="Admin",
            last_name="User",
        )
        if hasattr(self.admin_user, "makeAdmin"):
            self.admin_user.makeAdmin()
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()

        self.prog = Program.objects.create(
            name="Test Program",
            url="testprogram",
            grade_min=7,
            grade_max=12,
        )

        self.pm = ProgramModule.objects.create(
            admin_title="Autoscheduler Frontend",
            link_title="Use the automatic scheduling tool",
            module_type="manage",
            handler="AutoschedulerFrontendModule",
            seq=50,
            choosable=2,
        )
        self.prog.program_modules.add(self.pm)
        self.prog.save()

        self.module = ProgramModuleObj.getFromProgModule(self.prog, self.pm)

    def _get_request(self, path="/", get_params=None):
        """Helper to create a GET request with authenticated user and session."""
        request = self.factory.get(path, get_params or {})
        request.user = self.admin_user
        request.session = {}
        return request

    def _post_request(self, path="/", post_data=None):
        """Helper to create a POST request with authenticated user and session."""
        request = self.factory.post(path, post_data or {})
        request.user = self.admin_user
        request.session = {}
        return request

    def test_module_properties(self):
        """Test module_properties returns expected configuration dictionary."""
        props = AutoschedulerFrontendModule.module_properties()
        self.assertEqual(props.get("admin_title"), "Autoscheduler Frontend")
        self.assertEqual(props.get("link_title"), "Use the automatic scheduling tool")
        self.assertEqual(props.get("module_type"), "manage")
        self.assertEqual(props.get("seq"), 50)
        self.assertEqual(props.get("choosable"), 2)

    def test_is_step(self):
        """Test isStep returns False."""
        self.assertFalse(self.module.isStep())

    def test_is_float(self):
        """Test is_float helper for various inputs."""
        self.assertTrue(self.module.is_float("1.23"))
        self.assertTrue(self.module.is_float("0"))
        self.assertTrue(self.module.is_float("-4.5"))
        self.assertFalse(self.module.is_float("abc"))
        self.assertFalse(self.module.is_float("True"))
        self.assertFalse(self.module.is_float(""))

    @patch("esp.program.modules.handlers.autoschedulerfrontendmodule.render_to_response")
    @patch("esp.program.modules.handlers.autoschedulerfrontendmodule.AutoschedulerController")
    def test_autoscheduler_main_call_success(self, mock_controller, mock_render):
        """Test autoscheduler view renders main page with correct context."""
        mock_controller.constraint_options.return_value = ["c1"]
        mock_controller.scorer_options.return_value = ["s1"]
        mock_controller.resource_options.return_value = ["r1"]
        mock_controller.search_options.return_value = ["search1"]
        mock_render.return_value = "rendered_page"

        request = self._get_request("/", {"section": "42"})

        response = self.module.autoscheduler(
            request, None, None, None, self.module, None, self.prog
        )

        self.assertEqual(response, "rendered_page")
        mock_controller.search_options.assert_called_once_with(self.prog, section="42")
        self.assertTrue(mock_render.called)
        _, kwargs_or_args = mock_render.call_args[0], mock_render.call_args[0]
        context = kwargs_or_args[2]
        self.assertEqual(context["constraints"], ["c1"])
        self.assertEqual(context["scorers"], ["s1"])
        self.assertEqual(context["resources"], ["r1"])
        self.assertEqual(context["search"], ["search1"])
        self.assertEqual(context["program"], self.prog)

    @patch("esp.program.modules.handlers.autoschedulerfrontendmodule.render_to_response")
    @patch("esp.program.modules.handlers.autoschedulerfrontendmodule.AutoschedulerController")
    def test_autoscheduler_main_call_scheduling_error(self, mock_controller, mock_render):
        """Test autoscheduler view handles SchedulingError gracefully."""
        mock_controller.constraint_options.side_effect = SchedulingError("Failed setup")
        mock_render.return_value = "rendered_error_page"

        request = self._get_request("/")

        response = self.module.autoscheduler(
            request, None, None, None, self.module, None, self.prog
        )

        self.assertEqual(response, "rendered_error_page")
        self.assertTrue(mock_render.called)
        context = mock_render.call_args[0][2]
        self.assertEqual(context["program"], self.prog)
        self.assertEqual(context["err_msg"], "Failed setup")

    @patch("esp.program.modules.handlers.autoschedulerfrontendmodule.AutoschedulerController")
    def test_autoscheduler_execute_success(self, mock_controller_cls):
        """Test autoscheduler_execute parses option types and returns assignment data."""
        mock_instance = MagicMock()
        mock_controller_cls.return_value = mock_instance
        mock_instance.get_scheduling_info.return_value = {"info_key": "info_val"}
        mock_instance.export_assignments.return_value = {"assignment": 1}

        post_data = {
            "autoscheduler_flag_bool_true": "True",
            "autoscheduler_flag_bool_false": "False",
            "autoscheduler_flag_none": "None",
            "autoscheduler_weight": "1.5",
            "autoscheduler_name": "custom_schedule",
            "irrelevant_key": "irrelevant_val",
        }
        request = self._post_request("/execute", post_data)

        response = self.module.autoscheduler_execute(
            request, None, None, None, self.module, None, self.prog
        )

        mock_controller_cls.assert_called_once_with(
            self.prog,
            flag_bool_true=True,
            flag_bool_false=False,
            flag_none=None,
            weight=1.5,
            name="custom_schedule",
        )
        mock_instance.compute_assignments.assert_called_once()
        res_data = json.loads(response.content.decode("utf-8"))
        self.assertIn("response", res_data)
        self.assertEqual(
            res_data["response"][0]["info"],
            {"info_key": "info_val"},
        )
        self.assertEqual(
            json.loads(res_data["response"][0]["autoscheduler_data"]),
            {"assignment": 1},
        )

    @patch("esp.program.modules.handlers.autoschedulerfrontendmodule.AutoschedulerController")
    def test_autoscheduler_execute_scheduling_error(self, mock_controller_cls):
        """Test autoscheduler_execute handles SchedulingError."""
        mock_instance = MagicMock()
        mock_controller_cls.return_value = mock_instance
        mock_instance.compute_assignments.side_effect = SchedulingError("Infeasible constraints")

        request = self._post_request("/execute", {"autoscheduler_test": "True"})

        response = self.module.autoscheduler_execute(
            request, None, None, None, self.module, None, self.prog
        )

        res_data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(
            res_data["response"],
            [{"error_msg": "Infeasible constraints"}],
        )

    @patch("esp.program.modules.handlers.autoschedulerfrontendmodule.AutoschedulerController")
    def test_autoscheduler_execute_value_error(self, mock_controller_cls):
        """Test autoscheduler_execute handles ValueError."""
        mock_instance = MagicMock()
        mock_controller_cls.return_value = mock_instance
        mock_instance.compute_assignments.side_effect = ValueError("Invalid parameter value")

        request = self._post_request("/execute", {"autoscheduler_val": "invalid"})

        response = self.module.autoscheduler_execute(
            request, None, None, None, self.module, None, self.prog
        )

        res_data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(
            res_data["response"],
            [{"error_msg": "Invalid parameter value"}],
        )

    def test_autoscheduler_save_missing_post_field(self):
        """Test autoscheduler_save returns error if autoscheduler_data key is missing."""
        request = self._post_request("/save", {})

        response = self.module.autoscheduler_save(
            request, None, None, None, self.module, None, self.prog
        )

        res_data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(
            res_data["response"],
            [{"error_msg": "missing autoscheduler_data POST field"}],
        )

    @patch("esp.program.modules.handlers.autoschedulerfrontendmodule.AutoschedulerController")
    def test_autoscheduler_save_success(self, mock_controller_cls):
        """Test autoscheduler_save imports and saves assignments."""
        mock_instance = MagicMock()
        mock_controller_cls.return_value = mock_instance

        payload = json.dumps([{"slot_1": "class_a"}, {"opt": True}])
        request = self._post_request("/save", {"autoscheduler_data": payload})

        response = self.module.autoscheduler_save(
            request, None, None, None, self.module, None, self.prog
        )

        mock_controller_cls.assert_called_once_with(self.prog, opt=True)
        mock_instance.import_assignments.assert_called_once_with({"slot_1": "class_a"})
        mock_instance.save_assignments.assert_called_once()
        res_data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(res_data["response"], [{"success": "yes"}])

    @patch("esp.program.modules.handlers.autoschedulerfrontendmodule.AutoschedulerController")
    def test_autoscheduler_save_scheduling_error(self, mock_controller_cls):
        """Test autoscheduler_save handles SchedulingError while saving."""
        mock_instance = MagicMock()
        mock_controller_cls.return_value = mock_instance
        mock_instance.save_assignments.side_effect = SchedulingError("DB save failed")

        payload = json.dumps([{"slot_1": "class_a"}, {}])
        request = self._post_request("/save", {"autoscheduler_data": payload})

        response = self.module.autoscheduler_save(
            request, None, None, None, self.module, None, self.prog
        )

        res_data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(
            res_data["response"],
            [{"error_msg": "DB save failed"}],
        )

    def test_autoscheduler_clear(self):
        """Test autoscheduler_clear returns success."""
        request = self._post_request("/clear", {})

        response = self.module.autoscheduler_clear(
            request, None, None, None, self.module, None, self.prog
        )

        res_data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(res_data["response"], [{"success": "yes"}])
