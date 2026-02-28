import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from django.http import HttpResponseForbidden
from django.test import RequestFactory, TestCase, override_settings

# ─────────────────────────────────────────────
# Tests: _resolve_program
# ─────────────────────────────────────────────

class TestResolveProgram(TestCase):
    """Unit tests for the _resolve_program helper in isolation."""

    def _get_helper(self):
        from esp.web.views.csrf import _resolve_program
        return _resolve_program

    def test_returns_none_for_non_program_path(self):
        """Paths that don't match the program URL pattern return None."""
        _resolve_program = self._get_helper()
        mock_class = MagicMock()
        result = _resolve_program("/contact/", mock_class)
        self.assertIsNone(result)
        mock_class.by_prog_inst.assert_not_called()

    def test_returns_none_for_root_path(self):
        _resolve_program = self._get_helper()
        result = _resolve_program("/", MagicMock())
        self.assertIsNone(result)

    def test_returns_program_on_valid_path(self):
        """Valid program path returns Program instance."""
        _resolve_program = self._get_helper()
        mock_class = MagicMock()
        fake_prog = MagicMock()
        mock_class.by_prog_inst.return_value = fake_prog

        result = _resolve_program("learn/Spark/2024", mock_class)

        mock_class.by_prog_inst.assert_called_once_with("Spark", "2024")
        self.assertEqual(result, fake_prog)

    def test_returns_none_when_program_does_not_exist(self):
        """DoesNotExist is caught gracefully and returns None."""
        _resolve_program = self._get_helper()
        mock_class = MagicMock()
        mock_class.DoesNotExist = Exception
        mock_class.by_prog_inst.side_effect = mock_class.DoesNotExist("not found")

        result = _resolve_program("learn/Spark/2024", mock_class)

        self.assertIsNone(result)

    def test_returns_none_on_unexpected_exception(self):
        """Unexpected exceptions are caught, logged, and return None."""
        _resolve_program = self._get_helper()
        mock_class = MagicMock()
        mock_class.DoesNotExist = type("DoesNotExist", (Exception,), {})
        mock_class.by_prog_inst.side_effect = RuntimeError("db exploded")

        with self.assertLogs("esp.web.views.csrf", level="ERROR"):
            result = _resolve_program("learn/Spark/2024", mock_class)

        self.assertIsNone(result)

    def test_handles_spaces_in_program_path(self):
        """URLconf allows spaces in program segments — regex must support them."""
        _resolve_program = self._get_helper()
        mock_class = MagicMock()
        mock_class.by_prog_inst.return_value = MagicMock()

        result = _resolve_program("learn/Splash 2024/Spring Session", mock_class)

        mock_class.by_prog_inst.assert_called_once_with("Splash 2024", "Spring Session")
        self.assertIsNotNone(result)

    def test_handles_hyphens_and_underscores(self):
        """Hyphens and underscores are valid in program URL segments."""
        _resolve_program = self._get_helper()
        mock_class = MagicMock()
        mock_class.by_prog_inst.return_value = MagicMock()

        _resolve_program("manage/Spark-2024/Fall_Run", mock_class)

        mock_class.by_prog_inst.assert_called_once_with("Spark-2024", "Fall_Run")

    def test_logs_debug_on_does_not_exist(self):
        """DoesNotExist triggers a debug log."""
        _resolve_program = self._get_helper()
        mock_class = MagicMock()
        mock_class.DoesNotExist = type("DoesNotExist", (Exception,), {})
        mock_class.by_prog_inst.side_effect = mock_class.DoesNotExist

        with self.assertLogs("esp.web.views.csrf", level="DEBUG") as log:
            _resolve_program("learn/Spark/2024", mock_class)

        self.assertTrue(any("not found" in m.lower() or "Program" in m for m in log.output))


# ─────────────────────────────────────────────
# Tests: csrf_failure — fast path (production)
# ─────────────────────────────────────────────

class TestCsrfFailureFastPath(TestCase):
    """
    Tests for the production / non-admin fast path.
    All of these should return Django's default response with reason="".
    """

    @patch("esp.web.views.csrf.django_csrf_failure")
    @override_settings(DEBUG=False)
    def test_anonymous_user_gets_django_default(self, mock_django_csrf):
        """Anonymous users always hit the fast path."""
        from esp.web.views.csrf import csrf_failure
        mock_django_csrf.return_value = HttpResponseForbidden("default")
        request = make_request(authenticated=False)

        csrf_failure(request, reason="CSRF token missing")

        mock_django_csrf.assert_called_once_with(request, reason="")

    @patch("esp.web.views.csrf.django_csrf_failure")
    @override_settings(DEBUG=False)
    def test_authenticated_non_admin_gets_django_default(self, mock_django_csrf):
        """Authenticated but non-admin users hit the fast path in production."""
        from esp.web.views.csrf import csrf_failure
        mock_django_csrf.return_value = HttpResponseForbidden("default")
        request = make_request(authenticated=True, is_admin=False)

        csrf_failure(request, reason="some reason")

        mock_django_csrf.assert_called_once_with(request, reason="")

    @patch("esp.web.views.csrf.django_csrf_failure")
    @override_settings(DEBUG=True)
    def test_admin_without_debug_false_gets_django_default(self, mock_django_csrf):
        """Admin user but DEBUG=False still hits fast path."""
        from esp.web.views.csrf import csrf_failure
        mock_django_csrf.return_value = HttpResponseForbidden("default")
        request = make_request(authenticated=True, is_admin=True)

        with override_settings(DEBUG=False):
            csrf_failure(request, reason="reason")

        mock_django_csrf.assert_called_once_with(request, reason="")

    @patch("esp.web.views.csrf.django_csrf_failure")
    @override_settings(DEBUG=False)
    def test_reason_not_leaked_in_fast_path(self, mock_django_csrf):
        """Fast path always passes reason='' — internal reason never exposed."""
        from esp.web.views.csrf import csrf_failure
        mock_django_csrf.return_value = HttpResponseForbidden("default")
        request = make_request(authenticated=False)

        csrf_failure(request, reason="REASON_NO_REFERER")

        _, kwargs = mock_django_csrf.call_args
        self.assertEqual(kwargs["reason"], "")

    @patch("esp.web.views.csrf.django_csrf_failure")
    @override_settings(DEBUG=False)
    def test_always_logs_warning_on_fast_path(self, mock_django_csrf):
        """Every CSRF failure logs a warning regardless of user type."""
        from esp.web.views.csrf import csrf_failure
        mock_django_csrf.return_value = HttpResponseForbidden("default")
        request = make_request(authenticated=False, ip="192.168.1.1")

        with self.assertLogs("esp.web.views.csrf", level="WARNING") as log:
            csrf_failure(request, reason="test reason")

        self.assertTrue(any("192.168.1.1" in m for m in log.output))

    @patch("esp.web.views.csrf.django_csrf_failure")
    @override_settings(DEBUG=False)
    def test_log_contains_path_and_ip(self, mock_django_csrf):
        """Warning log includes path and IP for observability."""
        from esp.web.views.csrf import csrf_failure
        mock_django_csrf.return_value = HttpResponseForbidden("default")
        request = make_request(path="/some/program/path/", ip="10.0.0.1")

        with self.assertLogs("esp.web.views.csrf", level="WARNING") as log:
            csrf_failure(request)

        combined = " ".join(log.output)
        self.assertIn("/some/program/path/", combined)
        self.assertIn("10.0.0.1", combined)


# ─────────────────────────────────────────────
# Tests: csrf_failure — detailed path (admin + DEBUG)
# ─────────────────────────────────────────────

class TestCsrfFailureDetailedPath(TestCase):
    """
    Tests for the admin + DEBUG detailed path.
    These exercise the custom template rendering branch.
    """

    def _admin_debug_request(self, path="/learn/Spark/2024/"):
        return make_request(path=path, authenticated=True, is_admin=True)

    @patch("esp.web.views.csrf.django_csrf_failure")
    @patch("esp.web.views.csrf._resolve_program")
    @patch("esp.web.views.csrf.render_to_response")
    @override_settings(DEBUG=True)
    def test_admin_debug_renders_custom_template(
        self, mock_render, mock_resolve, mock_django_csrf
    ):
        """Admin + DEBUG renders the custom 403 template."""
        from esp.web.views.csrf import csrf_failure

        fake_response = MagicMock()
        fake_response.content = b"<h1>Custom 403</h1>"
        fake_response.get.return_value = "text/html; charset=utf-8"
        mock_render.return_value = fake_response
        mock_resolve.return_value = None

        request = self._admin_debug_request()
        response = csrf_failure(request, reason="Token missing")

        mock_render.assert_called_once_with("403_csrf_failure.html", request, {
            "DEBUG": True,
            "reason": "Token missing",
            "no_referer": False,
            "program": None,
        })
        self.assertIsInstance(response, HttpResponseForbidden)
        mock_django_csrf.assert_not_called()

    @patch("esp.web.views.csrf._resolve_program")
    @patch("esp.web.views.csrf.render_to_response")
    @override_settings(DEBUG=True)
    def test_response_content_is_bytes_directly(self, mock_render, mock_resolve):
        """Content is passed as bytes — no str() decode/encode roundtrip."""
        from esp.web.views.csrf import csrf_failure

        fake_response = MagicMock()
        fake_response.content = b"<p>Forbidden</p>"
        fake_response.get.return_value = "text/html"
        mock_render.return_value = fake_response
        mock_resolve.return_value = None

        request = self._admin_debug_request()
        response = csrf_failure(request)

        self.assertEqual(response.content, b"<p>Forbidden</p>")

    @patch("esp.web.views.csrf._resolve_program")
    @patch("esp.web.views.csrf.render_to_response")
    @override_settings(DEBUG=True)
    def test_no_referer_flag_set_correctly(self, mock_render, mock_resolve):
        """no_referer context flag is True when reason matches REASON_NO_REFERER."""
        from esp.web.views.csrf import csrf_failure
        from django.middleware.csrf import REASON_NO_REFERER

        fake_response = MagicMock()
        fake_response.content = b"403"
        fake_response.get.return_value = "text/html"
        mock_render.return_value = fake_response
        mock_resolve.return_value = None

        request = self._admin_debug_request()
        csrf_failure(request, reason=REASON_NO_REFERER)

        call_context = mock_render.call_args[0][2]
        self.assertTrue(call_context["no_referer"])

    @patch("esp.web.views.csrf._resolve_program")
    @patch("esp.web.views.csrf.render_to_response")
    @override_settings(DEBUG=True)
    def test_program_passed_into_context(self, mock_render, mock_resolve):
        """Resolved program is passed into the template context."""
        from esp.web.views.csrf import csrf_failure

        fake_prog = MagicMock()
        mock_resolve.return_value = fake_prog

        fake_response = MagicMock()
        fake_response.content = b"403"
        fake_response.get.return_value = "text/html"
        mock_render.return_value = fake_response

        request = self._admin_debug_request(path="/learn/Spark/2024/")
        csrf_failure(request)

        call_context = mock_render.call_args[0][2]
        self.assertEqual(call_context["program"], fake_prog)

    @patch("esp.web.views.csrf.django_csrf_failure")
    @patch("esp.web.views.csrf._resolve_program")
    @patch("esp.web.views.csrf.render_to_response")
    @override_settings(DEBUG=True)
    def test_falls_back_to_django_default_on_render_failure(
        self, mock_render, mock_resolve, mock_django_csrf
    ):
        """If template rendering raises, falls back to Django default with real reason."""
        from esp.web.views.csrf import csrf_failure

        mock_render.side_effect = Exception("Template missing")
        mock_resolve.return_value = None
        mock_django_csrf.return_value = HttpResponseForbidden("fallback")

        request = self._admin_debug_request()

        with self.assertLogs("esp.web.views.csrf", level="ERROR"):
            response = csrf_failure(request, reason="real reason")

        mock_django_csrf.assert_called_once_with(request, reason="real reason")

    @patch("esp.web.views.csrf.django_csrf_failure")
    @patch("esp.web.views.csrf._resolve_program")
    @patch("esp.web.views.csrf.render_to_response")
    @override_settings(DEBUG=True)
    def test_render_failure_logs_error_with_path(
        self, mock_render, mock_resolve, mock_django_csrf
    ):
        """Rendering failure logs an error including the request path."""
        from esp.web.views.csrf import csrf_failure

        mock_render.side_effect = Exception("boom")
        mock_resolve.return_value = None
        mock_django_csrf.return_value = HttpResponseForbidden("fallback")

        request = self._admin_debug_request(path="/learn/Spark/2024/")

        with self.assertLogs("esp.web.views.csrf", level="ERROR") as log:
            csrf_failure(request)

        self.assertTrue(any("/learn/Spark/2024/" in m for m in log.output))

    @patch("esp.web.views.csrf._resolve_program")
    @patch("esp.web.views.csrf.render_to_response")
    @override_settings(DEBUG=True)
    def test_content_type_fallback_when_header_missing(self, mock_render, mock_resolve):
        """Content-Type falls back to text/html if header missing on response."""
        from esp.web.views.csrf import csrf_failure

        fake_response = MagicMock()
        fake_response.content = b"403"
        fake_response.get.return_value = "text/html"  # .get() used, not []
        mock_render.return_value = fake_response
        mock_resolve.return_value = None

        request = self._admin_debug_request()
        csrf_failure(request)

        fake_response.get.assert_called_with("Content-Type", "text/html")


# ─────────────────────────────────────────────
# Tests: Auth guard edge cases
# ─────────────────────────────────────────────

class TestCsrfFailureAuthGuard(TestCase):
    """Edge cases around user authentication state."""

    @patch("esp.web.views.csrf.django_csrf_failure")
    @override_settings(DEBUG=True)
    def test_unauthenticated_user_never_reaches_detailed_path(self, mock_django_csrf):
        """Even in DEBUG mode, unauthenticated user hits fast path."""
        from esp.web.views.csrf import csrf_failure
        mock_django_csrf.return_value = HttpResponseForbidden("default")
        request = make_request(authenticated=False, is_admin=False)

        csrf_failure(request)

        mock_django_csrf.assert_called_once_with(request, reason="")

    @patch("esp.web.views.csrf.django_csrf_failure")
    @override_settings(DEBUG=True)
    def test_is_administrator_not_called_for_anonymous_user(self, mock_django_csrf):
        """isAdministrator() is short-circuited for anonymous users."""
        from esp.web.views.csrf import csrf_failure
        mock_django_csrf.return_value = HttpResponseForbidden("default")

        user = MagicMock()
        user.is_authenticated = False

        factory = RequestFactory()
        request = factory.get("/")
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        request.user = user

        csrf_failure(request)

        user.isAdministrator.assert_not_called()

    @patch("esp.web.views.csrf.django_csrf_failure")
    @override_settings(DEBUG=True)
    def test_no_reason_defaults_gracefully(self, mock_django_csrf):
        """Calling csrf_failure with no reason arg doesn't crash."""
        from esp.web.views.csrf import csrf_failure
        mock_django_csrf.return_value = HttpResponseForbidden("default")
        request = make_request(authenticated=False)

        with self.assertLogs("esp.web.views.csrf", level="WARNING"):
            response = csrf_failure(request)  # no reason kwarg

        self.assertIsNotNone(response)


# ─────────────────────────────────────────────
# Tests: Return type
# ─────────────────────────────────────────────

class TestCsrfFailureReturnType(TestCase):
    """csrf_failure must always return an HttpResponseForbidden."""

    @patch("esp.web.views.csrf.django_csrf_failure")
    @override_settings(DEBUG=False)
    def test_returns_http_response_on_fast_path(self, mock_django_csrf):
        from esp.web.views.csrf import csrf_failure
        mock_django_csrf.return_value = HttpResponseForbidden("default")
        request = make_request()

        with self.assertLogs("esp.web.views.csrf", level="WARNING"):
            response = csrf_failure(request)

        self.assertIsNotNone(response)

    @patch("esp.web.views.csrf.django_csrf_failure")
    @patch("esp.web.views.csrf._resolve_program")
    @patch("esp.web.views.csrf.render_to_response")
    @override_settings(DEBUG=True)
    def test_returns_403_on_detailed_path(self, mock_render, mock_resolve, mock_django_csrf):
        from esp.web.views.csrf import csrf_failure

        fake_response = MagicMock()
        fake_response.content = b"403"
        fake_response.get.return_value = "text/html"
        mock_render.return_value = fake_response
        mock_resolve.return_value = None

        request = make_request(authenticated=True, is_admin=True)

        with self.assertLogs("esp.web.views.csrf", level="WARNING"):
            response = csrf_failure(request)

        self.assertIsInstance(response, HttpResponseForbidden)

