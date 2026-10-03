from unittest.mock import patch

from django.http import HttpResponse

from esp.program.modules.handlers.checkavailabilitymodule import CheckAvailabilityModule
from esp.program.modules.handlers.availabilitymodule import AvailabilityModule
from esp.program.modules.admin_search import (
    AdminSearchEntry,
    SEARCH_CATEGORY_PARTICIPANTS,
)
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser


class CheckAvailabilityModuleTest(ModuleHandlerTestMixin, ProgramFrameworkTest):
    """Tests for the CheckAvailabilityModule handler and its admin functionality."""

    def test_is_step_returns_false(self):
        """Verify that this module is not treated as a program step."""
        module = CheckAvailabilityModule()
        self.assertFalse(module.isStep())

    def test_module_properties(self):
        """Verify the module's registered properties and admin-facing titles."""
        properties = CheckAvailabilityModule.module_properties()
        self.assertEqual(len(properties), 1)
        self.assertEqual(properties[0]["admin_title"], "Teacher Availability Checker")
        self.assertEqual(properties[0]["link_title"], "Check Teacher Availability")
        self.assertEqual(properties[0]["module_type"], "manage")
        self.assertEqual(properties[0]["seq"], 0)
        self.assertEqual(properties[0]["choosable"], 1)

    def test_get_admin_search_entry_for_edit_availability(self):
        """Verify that edit_availability appears in the admin search results."""
        entry = CheckAvailabilityModule.get_admin_search_entry(
            self.program, "manage", "edit_availability", None,
        )
        self.assertIsInstance(entry, AdminSearchEntry)
        self.assertEqual(entry.title, "Check Teacher Availability")
        self.assertEqual(entry.category, SEARCH_CATEGORY_PARTICIPANTS)

    def test_get_admin_search_entry_for_other_view(self):
        """Verify that unrelated views do not create an admin search entry."""
        entry = CheckAvailabilityModule.get_admin_search_entry(
            self.program, "manage", "some_other_view", None,
        )
        self.assertIsNone(entry)

    def test_edit_availability_without_user_renders_search_form(self):
        """Verify that the admin sees a teacher search form when no user is specified."""
        self.login_as("admin")
        url = self.get_module_url("manage", "edit_availability")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "program/modules/availabilitymodule/availability_form.html",
        )
        self.assertIn("search_form", response.context)

    def test_admin_can_access_edit_availability_form(self):
        """Verify that an admin can access the availability search form."""
        self.login_as("admin")
        url = self.get_module_url("manage", "edit_availability")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "program/modules/availabilitymodule/availability_form.html",
        )
        self.assertIn("search_form", response.context)

    def test_teacher_is_redirected_from_edit_availability(self):
        """Verify that a teacher cannot access the admin-only availability page."""
        self.login_as("teacher")
        url = self.get_module_url("manage", "edit_availability")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # The admin permission decorator renders an error template with HTTP 200.
        self.assertTemplateUsed(response, "errors/program/notanadmin.html")

    def test_teacher_cannot_post_to_edit_availability(self):
        """Verify that a teacher cannot submit a POST request to the admin-only page."""
        self.login_as("teacher")
        url = self.get_module_url("manage", "edit_availability")
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "errors/program/notanadmin.html")

    @patch.object(AvailabilityModule, "availabilityForm")
    def test_edit_availability_lookup_by_user_id(self, mock_availability_form):
        """Verify that a teacher found by ID is passed to the availability form."""
        self.login_as("admin")
        teacher = self.teachers[0]
        url = self.get_module_url("manage", "edit_availability")
        mock_availability_form.return_value = HttpResponse("OK")

        self.client.get(url, {"user": teacher.id})

        mock_availability_form.assert_called_once()
        self.assertEqual(mock_availability_form.call_args.args[5], teacher)

    def test_edit_availability_unknown_user_shows_error(self):
        """Verify that an unknown user produces the expected ESP error response."""
        self.login_as("admin")
        url = self.get_module_url("manage", "edit_availability")
        response = self.client.get(url, {"user": "not-a-real-user-xyz"})

        self.assertEqual(response.status_code, 500)
        self.assertTemplateUsed(response, "error.html")
        self.assertEqual(response.context["error_type"], "ESPError_NoLog")
        self.assertIn(
            "The user with id/username=not-a-real-user-xyz does not appear to exist!",
            str(response.context["error"]),
        )

    @patch.object(AvailabilityModule, "availabilityForm")
    def test_edit_availability_delegates_to_availability_form(self, mock_availability_form):
        """Verify that the handler passes the request and teacher to AvailabilityModule."""
        self.login_as("admin")
        teacher = self.teachers[0]
        url = self.get_module_url("manage", "edit_availability")
        mock_availability_form.return_value = HttpResponse("OK")

        response = self.client.get(url, {"user": teacher.id})

        self.assertEqual(response.status_code, 200)
        mock_availability_form.assert_called_once()
        args = mock_availability_form.call_args.args
        self.assertEqual(len(args), 7)
        self.assertEqual(args[0].method, "GET")
        self.assertEqual(args[0].GET["user"], str(teacher.id))
        self.assertEqual(args[1], "manage")
        self.assertEqual(args[4], self.program)
        self.assertEqual(args[5], teacher)
        self.assertIs(args[6], True)

    @patch.object(AvailabilityModule, "availabilityForm")
    def test_edit_availability_lookup_by_username(self, mock_availability_form):
        """Verify that username lookup works when the initial ID lookup fails."""
        self.login_as("admin")
        teacher = self.teachers[0]
        url = self.get_module_url("manage", "edit_availability")
        mock_availability_form.return_value = HttpResponse("OK")

        self.client.get(url, {"user": teacher.username})

        mock_availability_form.assert_called_once()
        self.assertEqual(mock_availability_form.call_args.args[5], teacher)

    @patch.object(AvailabilityModule, "availabilityForm")
    def test_edit_availability_post_target_user(self, mock_availability_form):
        """Verify that POST submission resolves target_user and passes the teacher."""
        self.login_as("admin")
        teacher = self.teachers[0]
        url = self.get_module_url("manage", "edit_availability")
        mock_availability_form.return_value = HttpResponse("OK")

        response = self.client.post(url, {"target_user": teacher.id})

        self.assertEqual(response.status_code, 200)
        mock_availability_form.assert_called_once()
        args = mock_availability_form.call_args.args
        self.assertEqual(args[0].method, "POST")
        self.assertEqual(args[0].POST["target_user"], str(teacher.id))
        self.assertEqual(args[5], teacher)
