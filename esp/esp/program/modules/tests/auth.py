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

from esp.program.tests import ProgramFrameworkTest

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
                    'Module "{}" is missing an auth check for view "{}"'.format(
                        module,
                        view_name
                    ))

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

                    method_name = '{}.{}'.format(class_node.name, func_node.name)
                    decorator_list = ', '.join('@{}'.format(name) for name in decorator_names if name)

                    if call_pos != 0:
                        failures.append(
                            '{}:{} {} should have @main_call/@aux_call as the outermost decorator. '
                            'Found: {}'.format(
                                handler_file.as_posix(),
                                func_node.lineno,
                                method_name,
                                decorator_list,
                            )
                        )

                    if auth_positions and grade_positions and min(auth_positions) > min(grade_positions):
                        failures.append(
                            '{}:{} {} has @meets_grade outside auth decorators. Found: {}'.format(
                                handler_file.as_posix(),
                                func_node.lineno,
                                method_name,
                                decorator_list,
                            )
                        )

                    if auth_positions and deadline_positions and min(auth_positions) > min(deadline_positions):
                        failures.append(
                            '{}:{} {} has deadline decorators outside auth decorators. Found: {}'.format(
                                handler_file.as_posix(),
                                func_node.lineno,
                                method_name,
                                decorator_list,
                            )
                        )

                    if grade_positions and deadline_positions and min(grade_positions) > min(deadline_positions):
                        failures.append(
                            '{}:{} {} has deadline decorators outside @meets_grade. Found: {}'.format(
                                handler_file.as_posix(),
                                func_node.lineno,
                                method_name,
                                decorator_list,
                            )
                        )

                    if auth_positions and cap_positions and min(auth_positions) > min(cap_positions):
                        failures.append(
                            '{}:{} {} has @meets_cap outside auth decorators. Found: {}'.format(
                                handler_file.as_posix(),
                                func_node.lineno,
                                method_name,
                                decorator_list,
                            )
                        )

                    if grade_positions and cap_positions and min(grade_positions) > min(cap_positions):
                        failures.append(
                            '{}:{} {} has @meets_cap outside @meets_grade. Found: {}'.format(
                                handler_file.as_posix(),
                                func_node.lineno,
                                method_name,
                                decorator_list,
                            )
                        )

                    if deadline_positions and cap_positions and min(deadline_positions) > min(cap_positions):
                        failures.append(
                            '{}:{} {} has @meets_cap outside deadline decorators. Found: {}'.format(
                                handler_file.as_posix(),
                                func_node.lineno,
                                method_name,
                                decorator_list,
                            )
                        )

                    if no_auth_positions and cache_positions and min(no_auth_positions) > min(cache_positions):
                        failures.append(
                            '{}:{} {} has cache decorators outside @no_auth. Found: {}'.format(
                                handler_file.as_posix(),
                                func_node.lineno,
                                method_name,
                                decorator_list,
                            )
                        )

        self.assertEqual([], failures, '\n'.join(failures))
