__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2014 by the individual contributors
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

import json

from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, Record


class OnSiteCheckinModuleTest(ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.add_user_profiles()
        pm = ProgramModule.objects.get(handler='OnSiteCheckinModule')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.admin = self.admins[0]
        self.student = self.students[0]

    def tearDown(self):
        Record.objects.filter(program=self.program, event__name='attended').delete()
        super().tearDown()

    def get_ajax_url(self):
        return '/onsite/%s/ajaxbarcodecheckin' % self.program.getUrlBase()

    def test_ajaxbarcodecheckin_valid_student(self):
        """Test that a valid student ID can be checked in via AJAX."""
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        response = self.client.post(
            self.get_ajax_url(),
            {'code': str(self.student.id), 'attended': 'true'}
        )

        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.content)
        self.assertIn('is now checked in', json_data['message'])

    def test_ajaxbarcodecheckin_non_numeric_id(self):
        """Test that a non-numeric user ID returns an informative error message.

        This is a regression test for:
        https://github.com/learning-unlimited/ESP-Website/issues/1854
        """
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        response = self.client.post(
            self.get_ajax_url(),
            {'code': 'abc123', 'attended': 'true'}
        )

        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.content)
        self.assertIn('is not a valid user ID (must be numeric)', json_data['message'])
        self.assertIn('abc123', json_data['message'])

    def test_ajaxbarcodecheckin_nonexistent_user(self):
        """Test that a non-existent user ID returns an appropriate message."""
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        response = self.client.post(
            self.get_ajax_url(),
            {'code': '999999999', 'attended': 'true'}
        )

        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.content)
        self.assertIn('is not a user', json_data['message'])
        self.assertIn('999999999', json_data['message'])

    def test_ajaxbarcodecheckin_non_student(self):
        """Test that checking in a non-student user returns an appropriate message."""
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        teacher = self.teachers[0]
        response = self.client.post(
            self.get_ajax_url(),
            {'code': str(teacher.id), 'attended': 'true'}
        )

        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.content)
        self.assertIn('is not a student', json_data['message'])

    def test_ajaxbarcodecheckin_already_checked_in(self):
        """Test that checking in an already checked-in student returns appropriate message."""
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        response = self.client.post(
            self.get_ajax_url(),
            {'code': str(self.student.id), 'attended': 'true'}
        )
        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.content)
        self.assertIn('is now checked in', json_data['message'])

        response = self.client.post(
            self.get_ajax_url(),
            {'code': str(self.student.id), 'attended': 'true'}
        )
        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.content)
        self.assertIn('is already checked in', json_data['message'])

    def test_ajaxbarcodecheckin_special_characters(self):
        """Test that various special characters in the code return informative error."""
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        invalid_codes = ['12.34', '12-34', '12 34', '@#$%', '', '   ']
        for code in invalid_codes:
            response = self.client.post(
                self.get_ajax_url(),
                {'code': code, 'attended': 'true'}
            )
            self.assertEqual(response.status_code, 200, f"Failed for code: {code!r}")
            json_data = json.loads(response.content)
            self.assertTrue(
                'is not a valid user ID' in json_data.get('message', '') or
                'is not a user' in json_data.get('message', ''),
                f"Unexpected message for code {code!r}: {json_data.get('message')}"
            )
