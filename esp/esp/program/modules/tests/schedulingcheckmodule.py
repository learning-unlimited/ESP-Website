__author__ = "Individual contributors (see AUTHORS file)"
__date__ = "$DATE$"
__rev__ = "$REV$"
__license__ = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
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

from unittest.mock import patch, MagicMock
import json

from esp.program.tests import ProgramFrameworkTest

from esp.program.modules.handlers.schedulingcheckmodule import (
    RawSCFormatter,
    JSONFormatter,
    SchedulingCheckRunner,
)

class SchedulingCheckModuleTest(ProgramFrameworkTest):

    # Test RawSCFormatter methods
    def test_format_table(self):
        formatter = RawSCFormatter()

        data = [{"a": 1}]
        result = formatter.format_table(data)

        self.assertEqual(result, data)

    def test_format_list(self):
        formatter = RawSCFormatter()

        data = ["x", "y"]
        result = formatter.format_list(data)

        self.assertEqual(result, data)

    # Test JSONFormatter methods
    def test_format_list(self):
        formatter = JSONFormatter()

        output = formatter.format_list(["A", "B"], ["Heading"])

        parsed = json.loads(output)

        self.assertIn("body", parsed)
        self.assertEqual(len(parsed["body"]), 2)

    def test_format_table_with_list(self):
        formatter = JSONFormatter()

        data = [{"Name": "Test"}]

        output = formatter.format_table(data, {"headings": ["Name"]})

        parsed = json.loads(output)

        self.assertEqual(parsed["headings"], ["Name"])

    # Test SchedulingCheckRunner methods
    @patch("esp.program.modules.handlers.schedulingcheckmodule.get_current_request")
    def test_runner_initializes(self, mock_request):
        """
        Ensure runner initializes correctly with mocked request.
        """

        fake_request = MagicMock()
        fake_request.GET = {}

        mock_request.return_value = fake_request

        runner = SchedulingCheckRunner(self.program)

        self.assertIsNotNone(runner)
        self.assertEqual(runner.incl_unreview, False)

    @patch("esp.program.modules.handlers.schedulingcheckmodule.get_current_request")
    def test_all_diagnostics(self, mock_request):
        """
        Verify diagnostics list is generated.
        """

        fake_request = MagicMock()
        fake_request.GET = {}

        mock_request.return_value = fake_request

        runner = SchedulingCheckRunner(self.program)

        diagnostics = runner.all_diagnostics()

        self.assertTrue(isinstance(diagnostics, list))
        self.assertTrue(len(diagnostics) > 0)

    @patch("esp.program.modules.handlers.schedulingcheckmodule.get_current_request")
    def test_run_diagnostics(self, mock_request):
        """
        Ensure run_diagnostics executes without crashing.
        """

        fake_request = MagicMock()
        fake_request.GET = {}

        mock_request.return_value = fake_request

        runner = SchedulingCheckRunner(self.program)

        results = runner.run_diagnostics(["lunch_blocks_setup"])

        self.assertTrue(isinstance(results, list))
