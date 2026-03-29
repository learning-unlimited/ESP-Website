__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2010 by the individual contributors
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

from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.models import VolunteerRequest
from esp.program.tests import ProgramFrameworkTest
from esp.cal.models import Event

class VolunteerManageTest(ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.add_user_profiles()
        pm = ProgramModule.objects.get(handler='VolunteerManage')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.admin = self.admins[0]
        self.base_url = '/manage/%s/volunteering' % (
            self.program.getUrlBase()
        )

    def test_volunteering_page_loads(self):
        """Test that volunteer management page loads for admin."""
        self.assertTrue(
            self.client.login(
                username=self.admin.username,
                password='password'
            ),
            "Couldn't log in as admin"
        )
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

    def test_create_volunteer_request(self):
        """Test that a new volunteer request can be created."""
        self.assertTrue(
            self.client.login(
                username=self.admin.username,
                password='password'
            ),
            "Couldn't log in as admin"
        )
        initial_count = VolunteerRequest.objects.filter(
            program=self.program
        ).count()

        timeslot = Event.objects.filter(
            program=self.program
        ).first()

        response = self.client.post(
            self.base_url,
            {
                'start_time': '2020-01-01 10:00',
                'end_time': '2020-01-01 11:00',
                'description': 'Test volunteer request',
                'num_volunteers': 5,
            }
        )
        new_count = VolunteerRequest.objects.filter(
            program=self.program
        ).count()
        self.assertGreaterEqual(new_count, initial_count)

    def test_delete_volunteer_request(self):
        """Test that a volunteer request can be deleted."""
        self.assertTrue(
            self.client.login(
                username=self.admin.username,
                password='password'
            ),
            "Couldn't log in as admin"
        )
        timeslot = Event.objects.filter(
            program=self.program
        ).first()

        vr = VolunteerRequest.objects.create(
            program=self.program,
            timeslot=timeslot,
            num_volunteers=3
        )
        response = self.client.get(
            self.base_url + '?op=delete&id=%s' % vr.id
        )
        self.assertFalse(
            VolunteerRequest.objects.filter(id=vr.id).exists()
        )

    def test_edit_volunteer_request(self):
        """Test that edit operation loads correctly."""
        self.assertTrue(
            self.client.login(
                username=self.admin.username,
                password='password'
            ),
            "Couldn't log in as admin"
        )
        timeslot = Event.objects.filter(
            program=self.program
        ).first()

        vr = VolunteerRequest.objects.create(
            program=self.program,
            timeslot=timeslot,
            num_volunteers=3
        )
        response = self.client.get(
            self.base_url + '?op=edit&id=%s' % vr.id
        )
        self.assertEqual(response.status_code, 200)

    def test_csv_export(self):
        """Test that CSV export works correctly."""
        self.assertTrue(
            self.client.login(
                username=self.admin.username,
                password='password'
            ),
            "Couldn't log in as admin"
        )
        response = self.client.get(self.base_url + '/csv')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response['Content-Type'].startswith('text/csv')
        )
