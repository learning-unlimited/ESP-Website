from __future__ import absolute_import

from django.http import HttpResponse
from django.test import TestCase, RequestFactory

from esp.middleware.fixiemiddleware import FixIEMiddleware


class FixIEMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = FixIEMiddleware()

    def test_ie_user_agent_does_not_crash_for_default_html(self):
        request = self.factory.get("/", HTTP_USER_AGENT="Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1)")
        response = HttpResponse("ok")

        result = self.middleware.process_response(request, response)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.content, b"ok")

    def test_ie_user_agent_strips_vary_for_unsafe_content_type(self):
        request = self.factory.get("/", HTTP_USER_AGENT="Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1)")
        response = HttpResponse("ok", content_type="application/json; charset=utf-8")
        response["Vary"] = "User-Agent"

        result = self.middleware.process_response(request, response)

        self.assertEqual(result.status_code, 200)
        self.assertNotIn("Vary", result)
        self.assertEqual(result["Pragma"], "no-cache")
        self.assertEqual(result["Cache-Control"], "no-cache, must-revalidate")

