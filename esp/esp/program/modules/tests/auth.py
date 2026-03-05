__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2015 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

from unittest.mock import MagicMock, patch
from django.test import TestCase, RequestFactory

from esp.program.modules.base import (
    user_passes_test, render_deadline_for_tl, not_logged_in,
)
from esp.program.tests import ProgramFrameworkTest


class UserPassesTestDecoratorTest(TestCase):
    """Unit tests for the enhanced user_passes_test() decorator factory."""

    def _make_view(self, **decorator_kwargs):
        """Return a simple view wrapped with user_passes_test(**decorator_kwargs)."""
        test_func = decorator_kwargs.pop('test_func', lambda mo, req: True)

        @user_passes_test(test_func, **decorator_kwargs)
        def view(moduleObj, request, tl, *args, **kwargs):
            return 'ok'

        return view

    def _make_request(self, authenticated=True):
        request = MagicMock()
        request.user.is_authenticated = authenticated
        request.user.id = 1 if authenticated else None
        return request

    def test_sets_has_auth_check(self):
        """Wrapped view must expose has_auth_check = True."""
        view = self._make_view()
        self.assertTrue(getattr(view, 'has_auth_check', False))

    def test_sets_method_attribute(self):
        """Wrapped view must expose .method pointing to the original function."""
        def inner(moduleObj, request, tl):
            return 'inner'

        wrapped = user_passes_test(lambda mo, req: True)(inner)
        self.assertIs(wrapped.method, inner)

    def test_sets_call_tl(self):
        """call_tl kwarg must be surfaced on the wrapper function."""
        view = self._make_view(call_tl='learn')
        self.assertEqual(view.call_tl, 'learn')

    def test_no_call_tl_by_default(self):
        """call_tl must not be set when not provided."""
        view = self._make_view()
        self.assertFalse(hasattr(view, 'call_tl'))

    def test_passes_when_test_returns_true(self):
        """View is called normally when test_func returns True."""
        moduleObj = MagicMock()
        request = self._make_request()
        view = self._make_view(test_func=lambda mo, req: True)
        result = view(moduleObj, request, 'learn')
        self.assertEqual(result, 'ok')

    def test_require_login_redirects_unauthenticated(self):
        """require_login=True (default) must redirect anonymous users."""
        moduleObj = MagicMock()
        request = self._make_request(authenticated=False)
        request.user.is_authenticated = False
        request.user.id = None
        view = self._make_view(test_func=lambda mo, req: True, require_login=True)
        with patch('esp.program.modules.base._login_redirect') as mock_redirect:
            mock_redirect.return_value = 'redirect'
            result = view(moduleObj, request, 'learn')
        mock_redirect.assert_called_once_with(request)
        self.assertEqual(result, 'redirect')

    def test_require_login_false_skips_redirect(self):
        """require_login=False must skip the login check entirely."""
        moduleObj = MagicMock()
        request = self._make_request(authenticated=False)
        request.user.is_authenticated = False
        request.user.id = None
        view = self._make_view(test_func=lambda mo, req: True, require_login=False)
        with patch('esp.program.modules.base._login_redirect') as mock_redirect:
            result = view(moduleObj, request, 'learn')
        mock_redirect.assert_not_called()
        self.assertEqual(result, 'ok')

    def test_custom_error_template_on_failure(self):
        """error_template must be rendered instead of render_deadline_for_tl."""
        moduleObj = MagicMock()
        request = self._make_request()
        view = self._make_view(
            test_func=lambda mo, req: False,
            error_template='errors/program/notateacher.html',
        )
        with patch('esp.program.modules.base.render_to_response') as mock_render:
            mock_render.return_value = 'error_page'
            result = view(moduleObj, request, 'teach')
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        self.assertEqual(call_args[0][0], 'errors/program/notateacher.html')
        self.assertEqual(result, 'error_page')

    def test_fallback_to_render_deadline_when_no_error_template(self):
        """Without error_template, render_deadline_for_tl must be used."""
        moduleObj = MagicMock()
        request = self._make_request()
        view = self._make_view(
            test_func=lambda mo, req: False,
            error_message='the deadline Foo was',
        )
        with patch('esp.program.modules.base.render_deadline_for_tl') as mock_dl:
            mock_dl.return_value = 'deadline_page'
            result = view(moduleObj, request, 'learn')
        mock_dl.assert_called_once()
        context = mock_dl.call_args[0][2]
        self.assertEqual(context['extension'], 'the deadline Foo was')
        self.assertEqual(result, 'deadline_page')

    def test_error_context_var(self):
        """error_context_var must control the template variable name."""
        moduleObj = MagicMock()
        request = self._make_request()
        view = self._make_view(
            test_func=lambda mo, req: False,
            error_message='some message',
            error_context_var='my_var',
        )
        with patch('esp.program.modules.base.render_deadline_for_tl') as mock_dl:
            mock_dl.return_value = 'page'
            view(moduleObj, request, 'learn')
        context = mock_dl.call_args[0][2]
        self.assertIn('my_var', context)
        self.assertEqual(context['my_var'], 'some message')
        self.assertNotIn('extension', context)

    def test_extra_context_func_on_failure(self):
        """extra_context_func must contribute its dict to the error context."""
        moduleObj = MagicMock()
        request = self._make_request()
        extra = lambda mo, req: {'yog': 2025, 'program': 'Splash'}
        view = self._make_view(
            test_func=lambda mo, req: False,
            error_template='errors/program/wronggrade.html',
            extra_context_func=extra,
        )
        with patch('esp.program.modules.base.render_to_response') as mock_render:
            mock_render.return_value = 'page'
            view(moduleObj, request, 'learn')
        context = mock_render.call_args[0][2]
        self.assertEqual(context['yog'], 2025)
        self.assertEqual(context['program'], 'Splash')


class ProgramModuleAuthTest(ProgramFrameworkTest):
    """Validate that all program modules have some property."""

    def testViewsHaveAuths(self):
        """Test that all views of all program modules have some sort of auth decorator,
        e.g., @needs_admin, @needs_student, @needs_account, @no_auth"""

        # self.program has all possible modules
        modules = self.program.getModules()
        for module in modules:
            view_names = module.views
            for view_name in view_names:
                view = getattr(module, view_name)
                self.assertTrue(getattr(view, 'has_auth_check', None), \
                    'Module "{}" is missing an auth check for view "{}"'.format(
                        module,
                        view_name
                    ))
