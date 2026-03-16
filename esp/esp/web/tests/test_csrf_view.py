from unittest.mock import patch

from django.http import HttpResponse, HttpResponseForbidden
from django.middleware.csrf import REASON_NO_REFERER
from django.test import RequestFactory

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.web.views import csrf as csrf_view


class DummyAdminUser:
    def isAdministrator(self):
        return True


class CsrfFailureViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_csrf_failure_renders_custom_template(self):
        request = self.factory.get("/learn/TestProgram/2024/")
        request.user = DummyAdminUser()

        captured = {}

        def fake_render(template_name, req, context):
            captured["template"] = template_name
            captured["context"] = context
            return HttpResponse("csrf body", content_type="text/html")

        with patch("esp.utils.web.render_to_response", side_effect=fake_render):
            response = csrf_view.csrf_failure(request, reason=REASON_NO_REFERER)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, b"csrf body")
        self.assertIn("text/html", response["Content-Type"])
        self.assertEqual(captured["template"], "403_csrf_failure.html")
        self.assertEqual(captured["context"]["reason"], REASON_NO_REFERER)
        self.assertTrue(captured["context"]["no_referer"])

    def test_csrf_failure_falls_back_to_django_view_on_exception(self):
        request = self.factory.get("/learn/TestProgram/2024/")
        request.user = DummyAdminUser()

        fallback_response = HttpResponseForbidden("fallback")

        with patch("esp.utils.web.render_to_response", side_effect=Exception("boom")):
            with patch(
                "esp.web.views.csrf.django_csrf_failure",
                return_value=fallback_response,
            ) as fallback:
                response = csrf_view.csrf_failure(request, reason="bad token")

        fallback.assert_called_once_with(request, reason="bad token")
        self.assertIs(response, fallback_response)
