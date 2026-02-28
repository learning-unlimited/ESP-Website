import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from django.http import HttpResponseForbidden
from django.test import RequestFactory, TestCase, override_settings

class TestCsrfFailureReturnType(TestCase):
    #always return HttpResponseForbidden.

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
class TestCsrfFailureAuthGuard(TestCase):
    #user authentication

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


