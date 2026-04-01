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

from esp.program.modules.base import ProgramModuleObj
from esp.program.models import ProgramModule
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser
from esp.program.models import Record


class OnSiteCheckinModuleTest(ProgramFrameworkTest):
    """
    Tests the logic and views for the OnSiteCheckinModule.
    Handles student registration status, medical/liability forms, and onsite presence.
    """

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        
        # Setup student/teacher profiles and schedule
        self.add_user_profiles()
        self.schedule_randomly()
        
        # Instantiate the module
        pm = ProgramModule.objects.get(handler='OnSiteCheckinModule')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)
        
        self.admin = self.admins[0]
        self.student = self.students[0]
        self.module.student = self.student

        # Base URL for the module's views
        self.base_url = '/onsite/' + self.program.getUrlBase() + '/'

    def tearDown(self):
        # Clean up all records created during testing to avoid interference
        Record.objects.filter(
            program=self.program,
            event__name__in=["attended", "checked_out", "paid", "med", "liab"]
        ).delete()
        super().tearDown()

    def get_ajax_url(self):
        return self.base_url + 'ajaxbarcodecheckin'

    # -----------------------------------------------------------------------
    # Business Logic Tests (Record Management)
    # -----------------------------------------------------------------------

    def test_create_record_attended(self):
        """Test 'attended' record creation logic."""
        created = self.module.create_record("attended")
        self.assertTrue(created)
        self.assertTrue(self.module.hasAttended())
        self.assertTrue(self.module.isAttending())

        # Second call while already checked in should return False
        created_again = self.module.create_record("attended")
        self.assertFalse(created_again)

    def test_create_record_paid_liab_med(self):
        """Test get_or_create logic for forms and payments."""
        for key in ["med", "liab", "paid"]:
            self.assertTrue(self.module.create_record(key))
            self.assertFalse(self.module.create_record(key)) # Already exists

    def test_delete_record_attended(self):
        """Test that deleting 'attended' creates a 'checked_out' record."""
        self.module.create_record("attended")
        self.assertTrue(self.module.isAttending())

        self.module.delete_record("attended")
        self.assertFalse(self.module.isAttending())
        
        checkout_count = Record.objects.filter(
            user=self.student, 
            event__name="checked_out", 
            program=self.program
        ).count()
        self.assertEqual(checkout_count, 1)

    def test_delete_record_other(self):
        """Test that deleting med/liab records actually removes them from DB."""
        self.module.create_record("med")
        self.assertTrue(self.module.hasMedical())

        self.module.delete_record("med")
        self.assertFalse(self.module.hasMedical())

    def test_status_queries(self):
        """Test the various boolean status checker methods."""
        self.assertFalse(self.module.hasMedical())
        self.assertFalse(self.module.hasLiability())

        self.module.create_record("med")
        self.module.create_record("liab")

        self.assertTrue(self.module.hasMedical())
        self.assertTrue(self.module.hasLiability())

    def test_checkinPairs(self):
        """Verify checkinPairs pairs contiguous attended/checked_out records."""
        self.module.create_record("attended")
        self.module.delete_record("attended")
        self.module.create_record("attended")

        pairs = self.module.checkinPairs()
        self.assertEqual(len(pairs), 2)
        self.assertIsNotNone(pairs[0][0])
        self.assertIsNotNone(pairs[0][1])
        self.assertIsNotNone(pairs[1][0])
        self.assertEqual(len(pairs[1]), 1)

    # -----------------------------------------------------------------------
    # HTTP View Tests
    # -----------------------------------------------------------------------

    def test_rapidcheckin_get(self):
        """Test GET access to the rapid checkin view."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(self.base_url + 'rapidcheckin')
        self.assertEqual(response.status_code, 200)

    def test_rapidcheckin_post(self):
        """Test checking in a student via the rapid checkin form."""
        self.client.login(username=self.admin.username, password='password')
       
        data = {'target_user': self.student.id}  
        response = self.client.post(self.base_url + 'rapidcheckin', data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.program.isCheckedIn(self.student))

    def test_barcodecheckin_get(self):
        """Test GET access to the bulk barcode checkin view."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(self.base_url + 'barcodecheckin')
        self.assertEqual(response.status_code, 200)

    def test_barcodecheckin_post(self):
        """Test processing multiple student IDs at once via barcode checkin."""
        self.client.login(username=self.admin.username, password='password')
        data = {
            'uids': str(self.student.id),
            'attended': 'on',
            'med': 'on'
        }
        response = self.client.post(self.base_url + 'barcodecheckin', data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.module.hasAttended())
        self.assertTrue(self.module.hasMedical())

    def test_checkin_get(self):
        """Test GET access to the detailed student checkin view."""
        self.client.login(username=self.admin.username, password='password')
        url = self.base_url + 'checkin/' + str(self.student.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_ajax_status(self):
        """Test the AJAX endpoint that retrieves current status booleans."""
        self.client.login(username=self.admin.username, password='password')
        self.module.create_record("liab")

        url = self.base_url + 'ajax_status/' + str(self.student.id)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)  
       
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')  
          
       
        self.assertContains(response, 'checkin_status_html')

    # -----------------------------------------------------------------------
    # Regression & AJAX Tests
    # -----------------------------------------------------------------------

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
        json_data = json.loads(response.content.decode('utf-8'))
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
        json_data = json.loads(response.content.decode('utf-8'))
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
        json_data = json.loads(response.content.decode('utf-8'))
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
        json_data = json.loads(response.content.decode('utf-8'))
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
        json_data = json.loads(response.content.decode('utf-8'))
        self.assertIn('is now checked in', json_data['message'])

        response = self.client.post(
            self.get_ajax_url(),
            {'code': str(self.student.id), 'attended': 'true'}
        )
        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.content.decode('utf-8'))
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
            json_data = json.loads(response.content.decode('utf-8'))
            self.assertTrue(
                'is not a valid user ID' in json_data.get('message', '') or
                'is not a user' in json_data.get('message', ''),
                f"Unexpected message for code {code!r}: {json_data.get('message')}"
            )