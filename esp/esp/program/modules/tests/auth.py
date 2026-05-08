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

import ast
from pathlib import Path
import warnings
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase, TestCase

from esp.program.modules.base import user_passes_test
from esp.program.tests import ProgramFrameworkTest


class UserPassesTestDecoratorTest(SimpleTestCase):
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


class NeedsStudentInGradeCompositionTest(SimpleTestCase):
    """Test needs_student_in_grade composes needs_student + meets_grade correctly."""

    def _make_request(self, authenticated=True, is_student=True, is_admin=False):
        request = MagicMock()
        request.user.is_authenticated = authenticated
        request.user.id = 1 if authenticated else None
        request.user.isStudent.return_value = is_student
        request.user.isAdmin.return_value = is_admin
        return request

    def test_unauthenticated_redirects(self):
        """Anonymous user should be redirected to login."""
        from esp.program.modules.base import needs_student_in_grade

        @needs_student_in_grade
        def view(moduleObj, request, tl, *args, **kwargs):
            return 'ok'

        moduleObj = MagicMock()
        request = self._make_request(authenticated=False)
        request.user.is_authenticated = False
        request.user.id = None
        with patch('esp.program.modules.base._login_redirect') as mock_redirect:
            mock_redirect.return_value = 'redirect'
            result = view(moduleObj, request, 'learn')
        mock_redirect.assert_called_once_with(request)
        self.assertEqual(result, 'redirect')

    def test_non_student_gets_notastudent(self):
        """Non-student user should see notastudent.html, not wronggrade.html."""
        from esp.program.modules.base import needs_student_in_grade

        @needs_student_in_grade
        def view(moduleObj, request, tl, *args, **kwargs):
            return 'ok'

        moduleObj = MagicMock()
        request = self._make_request(is_student=False, is_admin=False)
        with patch('esp.program.modules.base.render_to_response') as mock_render:
            mock_render.return_value = 'error_page'
            result = view(moduleObj, request, 'learn')
        self.assertEqual(mock_render.call_args[0][0], 'errors/program/notastudent.html')

    def test_student_wrong_grade_gets_wronggrade(self):
        """Student outside grade range should see wronggrade.html."""
        from esp.program.modules.base import needs_student_in_grade

        @needs_student_in_grade
        def view(moduleObj, request, tl, *args, **kwargs):
            return 'ok'

        moduleObj = MagicMock()
        moduleObj.program.grade_min = 9
        moduleObj.program.grade_max = 12
        request = self._make_request(is_student=True)
        request.user.getGrade.return_value = 7
        with patch('esp.program.modules.base.Permission') as MockPerm:
            MockPerm.user_has_perm.return_value = False
            with patch('esp.program.modules.base.render_to_response') as mock_render:
                mock_render.return_value = 'error_page'
                result = view(moduleObj, request, 'learn')
        self.assertEqual(mock_render.call_args[0][0], 'errors/program/wronggrade.html')

    def test_student_valid_grade_passes(self):
        """Student within grade range should reach the view."""
        from esp.program.modules.base import needs_student_in_grade

        @needs_student_in_grade
        def view(moduleObj, request, tl, *args, **kwargs):
            return 'ok'

        moduleObj = MagicMock()
        moduleObj.program.grade_min = 9
        moduleObj.program.grade_max = 12
        request = self._make_request(is_student=True)
        request.user.getGrade.return_value = 10
        with patch('esp.program.modules.base.Permission') as MockPerm:
            MockPerm.user_has_perm.return_value = False
            result = view(moduleObj, request, 'learn')
        self.assertEqual(result, 'ok')

    def test_method_attribute_points_to_original(self):
        """needs_student_in_grade must set .method to the original view."""
        from esp.program.modules.base import needs_student_in_grade

        def my_view(moduleObj, request, tl):
            return 'ok'

        wrapped = needs_student_in_grade(my_view)
        self.assertIs(wrapped.method, my_view)


class ProgramModuleAuthTest(ProgramFrameworkTest):
    """Validate that all program modules have some property."""

    CALL_DECORATORS = {'main_call', 'aux_call'}
    AUTH_DECORATORS = {'no_auth'}
    GRADE_DECORATORS = {'meets_grade'}
    DEADLINE_DECORATORS = {'meets_deadline', 'meets_any_deadline'}
    CAP_DECORATORS = {'meets_cap'}
    CACHE_DECORATORS = {'cache_control'}

    @staticmethod
    def _decorator_name(decorator):
        if isinstance(decorator, ast.Name):
            return decorator.id
        if isinstance(decorator, ast.Attribute):
            return decorator.attr
        if isinstance(decorator, ast.Call):
            return ProgramModuleAuthTest._decorator_name(decorator.func)
        return None

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
                    f'Module "{module}" is missing an auth check for view "{view_name}"')

    def testViewDecoratorOrder(self):
        """Check that module view decorators are ordered as expected.

        Outside to inside, expected decorator order is approximately:
        @main_call/@aux_call, then auth (@needs_* or @no_auth),
        then @meets_grade, then @meets_deadline/@meets_any_deadline,
        then @meets_cap.

        This only inspects decorators declared directly on handler methods via
        AST, so it intentionally does not reason about wrappers applied later at
        runtime or through function attributes assigned after definition. For
        public views, it also checks the security-sensitive relative order of
        @no_auth and @cache_control when both are present.
        """
        handlers_dir = Path(__file__).resolve().parents[1] / 'handlers'
        failures = []

        for handler_file in sorted(handlers_dir.glob('*.py')):
            with handler_file.open(encoding='utf-8') as f:
                source = f.read()

            with warnings.catch_warnings():
                warnings.simplefilter('ignore', SyntaxWarning)
                tree = ast.parse(source, filename=str(handler_file))

            for class_node in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
                for func_node in [n for n in class_node.body if isinstance(n, ast.FunctionDef)]:
                    decorator_names = [
                        self._decorator_name(decorator)
                        for decorator in func_node.decorator_list
                    ]

                    if not decorator_names:
                        continue

                    call_positions = [
                        i for i, name in enumerate(decorator_names)
                        if name in self.CALL_DECORATORS
                    ]
                    if not call_positions:
                        continue

                    call_pos = min(call_positions)
                    auth_positions = [
                        i for i, name in enumerate(decorator_names)
                        if name and (name.startswith('needs_') or name in self.AUTH_DECORATORS)
                    ]
                    no_auth_positions = [
                        i for i, name in enumerate(decorator_names)
                        if name == 'no_auth'
                    ]
                    grade_positions = [
                        i for i, name in enumerate(decorator_names)
                        if name in self.GRADE_DECORATORS
                    ]
                    deadline_positions = [
                        i for i, name in enumerate(decorator_names)
                        if name in self.DEADLINE_DECORATORS
                    ]
                    cap_positions = [
                        i for i, name in enumerate(decorator_names)
                        if name in self.CAP_DECORATORS
                    ]
                    cache_positions = [
                        i for i, name in enumerate(decorator_names)
                        if name in self.CACHE_DECORATORS
                    ]

                    method_name = f'{class_node.name}.{func_node.name}'
                    decorator_list = ', '.join(f'@{name}' for name in decorator_names if name)

                    if call_pos != 0:
                        failures.append(
                            f'{handler_file.as_posix()}:{func_node.lineno} {method_name} should have @main_call/@aux_call as the outermost decorator. '
                            f'Found: {decorator_list}'
                        )

                    if auth_positions and grade_positions and min(auth_positions) > min(grade_positions):
                        failures.append(
                            f'{handler_file.as_posix()}:{func_node.lineno} {method_name} has @meets_grade outside auth decorators. '
                            f'Found: {decorator_list}'
                        )

                    if auth_positions and deadline_positions and min(auth_positions) > min(deadline_positions):
                        failures.append(
                            f'{handler_file.as_posix()}:{func_node.lineno} {method_name} has deadline decorators outside auth decorators. '
                            f'Found: {decorator_list}'
                        )

                    if grade_positions and deadline_positions and min(grade_positions) > min(deadline_positions):
                        failures.append(
                            f'{handler_file.as_posix()}:{func_node.lineno} {method_name} has deadline decorators outside @meets_grade. '
                            f'Found: {decorator_list}'
                        )

                    if auth_positions and cap_positions and min(auth_positions) > min(cap_positions):
                        failures.append(
                            f'{handler_file.as_posix()}:{func_node.lineno} {method_name} has @meets_cap outside auth decorators. '
                            f'Found: {decorator_list}'
                        )

                    if grade_positions and cap_positions and min(grade_positions) > min(cap_positions):
                        failures.append(
                            f'{handler_file.as_posix()}:{func_node.lineno} {method_name} has @meets_cap outside @meets_grade. '
                            f'Found: {decorator_list}'
                        )

                    if deadline_positions and cap_positions and min(deadline_positions) > min(cap_positions):
                        failures.append(
                            f'{handler_file.as_posix()}:{func_node.lineno} {method_name} has @meets_cap outside deadline decorators. '
                            f'Found: {decorator_list}'
                        )

                    if no_auth_positions and cache_positions and min(no_auth_positions) > min(cache_positions):
                        failures.append(
                            f'{handler_file.as_posix()}:{func_node.lineno} {method_name} has cache decorators outside @no_auth. '
                            f'Found: {decorator_list}'
                        )

        self.assertEqual([], failures, '\n'.join(failures))
