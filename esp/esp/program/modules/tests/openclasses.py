__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2026 by the individual contributors
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


class OpenClassesPublicTest(ProgramFrameworkTest):
    def get_openclasses_url(self):
        return '/learn/%s/openclasses' % self.program.getUrlBase()

    def test_openclasses_renders_for_anonymous(self):
        response = self.client.get(self.get_openclasses_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/onsiteclasslist/openclasses.html')

    def test_openclasses_ignores_unsupported_query_params(self):
        # Unsupported params should be dropped before classList_base processing.
        response = self.client.get(self.get_openclasses_url(), {'refresh': 'abc', 'foo': 'bar'})
        self.assertEqual(response.status_code, 200)

    def test_openclasses_invalid_start_values_do_not_crash(self):
        for invalid_start in ['', 'abc']:
            response = self.client.get(self.get_openclasses_url(), {'start': invalid_start})
            self.assertEqual(response.status_code, 200)

    def test_openclasses_ignores_foreign_program_timeslot_id(self):
        self.create_past_program()
        foreign_timeslot = self.new_prog.getTimeSlots()[0]

        response = self.client.get(self.get_openclasses_url(), {'start': str(foreign_timeslot.id)})
        self.assertEqual(response.status_code, 200)

        current_time = response.context['current_time']
        self.assertEqual(current_time.program_id, self.program.id)
