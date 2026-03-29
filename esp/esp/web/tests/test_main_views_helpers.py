from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory

from esp.middleware.esperrormiddleware import ESPError_NoLog
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.web.views import main as web_main


class MainViewsHelpersTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_archives_dispatches_to_selected_handler(self):
        request = self.factory.post(
            "/archives/classes",
            {
                "newparam": "title",
                "sortparam0": "year",
                "sortparam1": "title",
            },
        )

        captured = {}

        def fake_handler(req, category, options, sortparams):
            captured["category"] = category
            captured["options"] = options
            captured["sortparams"] = sortparams
            return HttpResponse("ok")

        with patch.dict(web_main.archive_handlers, {"classes": fake_handler}, clear=True):
            response = web_main.archives(request, "classes", "cat", "opt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["category"], "cat")
        self.assertEqual(captured["options"], "opt")
        self.assertIn("title", captured["sortparams"])
        self.assertIn("year", captured["sortparams"])
        self.assertEqual(captured["sortparams"].count("title"), 1)

    def test_archives_unknown_selection_renders_construction(self):
        request = self.factory.get("/archives/unknown")

        with patch(
            "esp.web.views.main.render_to_response",
            return_value=HttpResponse("construction"),
        ) as render_to_response:
            response = web_main.archives(request, "unknown")

        render_to_response.assert_called_once_with("users/construction", request, {})
        self.assertEqual(response.status_code, 200)

    def test_set_csrf_token_calls_get_token(self):
        request = self.factory.get("/set_csrf")

        with patch("django.middleware.csrf.get_token", return_value="token") as get_token:
            response = web_main.set_csrf_token(request)

        get_token.assert_called_once_with(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    def test_public_email_renders_single_public_message(self):
        request = self.factory.get("/public-email/1")

        email_req = object()

        class SingleResult:
            def count(self):
                return 1

            def __getitem__(self, index):
                return email_req

        with patch("esp.web.views.main.MessageRequest.objects.filter", return_value=SingleResult()):
            with patch(
                "esp.web.views.main.render_to_response",
                return_value=HttpResponse("mail"),
            ) as render_to_response:
                response = web_main.public_email(request, 1)

        render_to_response.assert_called_once_with(
            "public_email.html",
            request,
            {"email_req": email_req},
        )
        self.assertEqual(response.status_code, 200)

    def test_public_email_raises_for_invalid_email_id(self):
        request = self.factory.get("/public-email/99")

        class EmptyResult:
            def count(self):
                return 0

        with patch("esp.web.views.main.MessageRequest.objects.filter", return_value=EmptyResult()):
            with self.assertRaises(ESPError_NoLog):
                web_main.public_email(request, 99)
