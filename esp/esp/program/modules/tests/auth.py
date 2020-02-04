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

from esp.program.tests import ProgramFrameworkTest

class ProgramModuleAuthTest(ProgramFrameworkTest):
    """Validate that all program modules have some property."""

    def testViewsHaveAuths(self):
        """Test that all views of all program modules have some sort of auth decorator,
        e.g., @needs_admin, @needs_student, @needs_account, @no_auth"""

        # self.program has all possible modules
        modules = self.program.getModules()
        for module in modules:
            view_names = module.get_all_views()
            for view_name in view_names:
                view = getattr(module, view_name)
                self.assertTrue(getattr(view, 'has_auth_check', None), \
                    'Module "{}" is missing an auth check for view "{}"'.format(
                        module,
                        view_name
                    ))
