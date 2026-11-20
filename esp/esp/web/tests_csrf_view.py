"""Tests for esp.web.views.csrf, the site's CSRF_FAILURE_VIEW.

This view replaces Django's default CSRF failure page with an ESP-themed one.
It is wired up in django_settings.py (CSRF_FAILURE_VIEW) and is therefore never
reached by ordinary URL routing, so nothing else in the suite exercises it.

Two things here are easy to break without noticing:

  - the debug details are gated on the viewer being an administrator, so a
    regression there leaks the CSRF failure reason to anonymous visitors; and
  - the whole body is wrapped in a try/except that falls back to Django's
    built-in view, so a rendering error degrades silently rather than 500ing.

Both are covered below, along with the program lookup done on the request path.
"""

from unittest.mock import patch

from django.http import HttpResponse, HttpResponseForbidden
from django.middleware.csrf import REASON_NO_REFERER
from django.test import Client, RequestFactory, override_settings

from esp.tests.factories import make_program, make_user
from esp.tests.util import CacheFlushTestCase
from esp.users.models import AnonymousESPUser
from esp.web.views.csrf import csrf_failure


class CsrfFailureViewTest(CacheFlushTestCase):

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def _request(self, path='/', user=None):
        """Build a request shaped like one that reached the CSRF middleware.

        ESPAuthMiddleware replaces Django's AnonymousUser with AnonymousESPUser,
        so the view can call ESP-specific methods such as isAdministrator() on
        request.user. Tests using RequestFactory bypass that middleware, so the
        substitution is made here instead.
        """
        request = self.factory.post(path)
        request.user = AnonymousESPUser() if user is None else user
        request.session = self.client.session
        return request

    def test_returns_403(self):
        response = csrf_failure(self._request())
        self.assertEqual(response.status_code, 403)
        self.assertIsInstance(response, HttpResponseForbidden)

    def test_page_states_the_csrf_failure(self):
        response = csrf_failure(self._request())
        content = response.content.decode('utf-8')
        self.assertIn('CSRF verification failed', content)
        self.assertIn('Forbidden', content)

    def test_serves_the_esp_page_and_not_djangos_default(self):
        """The whole point of this view: our page, not the built-in one.

        403_csrf_failure.html was adapted from Django's built-in CSRF page, so
        most of the wording is common to both and cannot tell them apart. These
        assertions use text that belongs to exactly one of the two, which is
        what makes this a regression test for the view falling back silently.
        """
        content = csrf_failure(self._request()).content.decode('utf-8')

        # Only in ours: the site template wrapper and the sign-off.
        self.assertIn('Web Team', content)
        self.assertIn('sorry for the inconvenience', content)
        # Only in Django's: its own troubleshooting list.
        self.assertNotIn('The form has a valid CSRF token', content)

    def test_renders_any_render_capable_response(self):
        """A response with render() but no is_rendered must still be rendered.

        Django's render() is a no-op once the content is baked, so the view
        calls it unconditionally rather than consulting is_rendered, which is
        specific to SimpleTemplateResponse. Skipping the call for a type that
        does not define that attribute would put us back to reading .content
        off an unrendered response.
        """
        class LazilyRenderedResponse(HttpResponse):
            def __init__(self):
                super().__init__('', content_type='text/html')

            def render(self):
                self.content = 'body available only after render()'
                return self

        with patch('esp.utils.web.render_to_response',
                   return_value=LazilyRenderedResponse()):
            response = csrf_failure(self._request())

        self.assertEqual(response.status_code, 403)
        self.assertIn(
            'body available only after render()',
            response.content.decode('utf-8'),
        )

    def test_middleware_rejection_serves_the_esp_page(self):
        """End-to-end: a real rejected POST, not a direct call to the view.

        CSRF_FAILURE_VIEW is only reached through CsrfViewMiddleware, so this
        is the path that actually matters. /accounts/login/ is used simply
        because it accepts POST and is CSRF-protected.
        """
        client = Client(enforce_csrf_checks=True)
        response = client.post('/accounts/login/', {'username': 'nobody'})

        self.assertEqual(response.status_code, 403)
        content = response.content.decode('utf-8')
        self.assertIn('CSRF verification failed', content)
        self.assertIn('Web Team', content)

    def test_response_is_html(self):
        response = csrf_failure(self._request())
        self.assertIn('text/html', response['Content-Type'])

    def test_no_referer_reason_explains_the_referer_header(self):
        response = csrf_failure(self._request(), reason=REASON_NO_REFERER)
        content = response.content.decode('utf-8')
        self.assertIn('Referer', content)
        self.assertIn('none was sent', content)

    def test_other_reason_omits_the_referer_explanation(self):
        response = csrf_failure(self._request(), reason='CSRF token missing.')
        self.assertNotIn('none was sent', response.content.decode('utf-8'))

    @override_settings(DEBUG=True)
    def test_failure_reason_is_hidden_from_anonymous_visitors(self):
        """The reason is debug detail: only administrators may see it."""
        response = csrf_failure(self._request(), reason='CSRF token missing.')
        content = response.content.decode('utf-8')
        self.assertNotIn('Reason given for failure', content)
        self.assertNotIn('CSRF token missing.', content)

    @override_settings(DEBUG=True)
    def test_failure_reason_is_shown_to_administrators(self):
        admin = make_user('Administrator', username='csrf_failure_admin')
        response = csrf_failure(
            self._request(user=admin), reason='CSRF token missing.')
        content = response.content.decode('utf-8')
        self.assertIn('Reason given for failure', content)
        self.assertIn('CSRF token missing.', content)

    @override_settings(DEBUG=True)
    def test_failure_reason_is_hidden_from_non_admin_users(self):
        student = make_user('Student', username='csrf_failure_student')
        response = csrf_failure(
            self._request(user=student), reason='CSRF token missing.')
        self.assertNotIn(
            'Reason given for failure', response.content.decode('utf-8'))

    def test_debug_details_stay_off_when_debug_is_off(self):
        """With DEBUG off, not even an administrator sees the reason."""
        admin = make_user('Administrator', username='csrf_failure_admin_nodebug')
        response = csrf_failure(
            self._request(user=admin), reason='CSRF token missing.')
        self.assertNotIn(
            'Reason given for failure', response.content.decode('utf-8'))

    def _captured_context(self, path):
        """Call the view with render_to_response patched, return its context.

        The view imports render_to_response inside the function body, so the
        patch is applied where it is defined rather than where it is used.
        """
        with patch('esp.utils.web.render_to_response') as mock_render:
            mock_render.return_value = HttpResponse(
                'rendered', content_type='text/html')
            csrf_failure(self._request(path))
        self.assertTrue(mock_render.called)
        return mock_render.call_args[0][2]

    def test_program_url_populates_the_program_context(self):
        program = make_program()
        context = self._captured_context('/learn/%s' % program.url)
        self.assertEqual(context['prog'], program)

    def test_unknown_program_leaves_the_context_program_empty(self):
        """A program-shaped path for a program that does not exist is not an error."""
        context = self._captured_context('/learn/NoSuchProgram/9999_Fall')
        self.assertIsNone(context['prog'])

    def test_non_program_path_leaves_the_context_program_empty(self):
        context = self._captured_context('/')
        self.assertIsNone(context['prog'])

    def test_reason_and_no_referer_reach_the_template_context(self):
        with patch('esp.utils.web.render_to_response') as mock_render:
            mock_render.return_value = HttpResponse(
                'rendered', content_type='text/html')
            csrf_failure(self._request(), reason=REASON_NO_REFERER)
        context = mock_render.call_args[0][2]
        self.assertEqual(context['reason'], REASON_NO_REFERER)
        self.assertTrue(context['no_referer'])

    def test_falls_back_to_djangos_view_when_rendering_fails(self):
        """The custom page must never be the reason the error page fails."""
        sentinel = HttpResponseForbidden('django default csrf page')
        with patch('esp.utils.web.render_to_response',
                   side_effect=RuntimeError('template exploded')), \
                patch('esp.web.views.csrf.django_csrf_failure',
                      return_value=sentinel) as mock_default:
            response = csrf_failure(self._request(), reason='some reason')

        self.assertIs(response, sentinel)
        self.assertEqual(response.status_code, 403)
        mock_default.assert_called_once()
        self.assertEqual(mock_default.call_args[1]['reason'], 'some reason')
