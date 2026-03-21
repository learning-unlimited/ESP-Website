__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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
from esp.users.models import ESPUser, Record, RecordType
from esp.program.models import ClassSection, ProgramModule


class OnSiteCheckoutModuleTest(ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.add_user_profiles()
        self.admin = self.admins[0]
        self.student = self.students[0]

        # Get and initialize the module
        pm, created = ProgramModule.objects.get_or_create(
            handler='OnSiteCheckoutModule',
            defaults={
                'link_title': 'Check-out Students',
                'admin_title': 'On-Site User Check-Out',
                'module_type': 'onsite',
                'seq': 1,
            }
        )
        # Ensure it's in the program
        self.program.program_modules.add(pm)
        # Get proxy object
        self.module = pm.getPythonClass()()
        self.module.program = self.program

        # Ensure "checked_out" and "attended" RecordTypes exist
        RecordType.objects.get_or_create(name="checked_out")
        RecordType.objects.get_or_create(name="attended")
        RecordType.objects.get_or_create(name="Enrolled")

    def get_checkout_url(self):
        return '/onsite/%s/checkout' % self.program.getUrlBase()

    def test_checkout_page_renders(self):
        """Test that the checkout page renders correctly."""
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        response = self.client.get(self.get_checkout_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Check-out Students')
        self.assertContains(response, 'Bulk Check-Out All Students')

    def test_checkout_search_user_by_id(self):
        """Test searching for a user by ID."""
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        response = self.client.get(self.get_checkout_url(), {'user': self.student.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.first_name)
        self.assertContains(response, self.student.last_name)

    def test_checkout_search_user_by_username(self):
        """Test searching for a user by username."""
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        response = self.client.get(self.get_checkout_url(), {'user': self.student.username})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.first_name)
        self.assertContains(response, self.student.last_name)

    def test_checkout_single_user(self):
        """Test checking out a single user and verifying record creation."""
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        # Before checkout, no "checked_out" record should exist for this program/user
        self.assertFalse(Record.objects.filter(user=self.student, program=self.program, event__name='checked_out').exists())

        response = self.client.post(self.get_checkout_url(), {
            'user': self.student.id,
            'checkout_student': 'true'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Successfully checked out")

        # Verify record creation
        self.assertTrue(Record.objects.filter(user=self.student, program=self.program, event__name='checked_out').exists())

    def test_checkout_all_students(self):
        """Test checking out all currently checked-in students."""
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        # Mock check-in: Ensure some students are checked in
        attended_rt = RecordType.objects.get(name='attended')
        Record.objects.create(user=self.students[1], event=attended_rt, program=self.program)
        Record.objects.create(user=self.students[2], event=attended_rt, program=self.program)

        # Before bulk checkout, no "checked_out" records should exist for these students
        self.assertFalse(Record.objects.filter(user__in=[self.students[1], self.students[2]], program=self.program, event__name='checked_out').exists())

        response = self.client.post(self.get_checkout_url(), {
            'checkoutall': 'true',
            'confirm': 'true'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Successfully checked out 2 students")

        # Verify record creation for both students
        self.assertTrue(Record.objects.filter(user=self.students[1], program=self.program, event__name='checked_out').exists())
        self.assertTrue(Record.objects.filter(user=self.students[2], program=self.program, event__name='checked_out').exists())

    def test_checkout_invalid_user(self):
        """Test that an invalid user search returns an informative message."""
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        response = self.client.get(self.get_checkout_url(), {'user': '9999999'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'does not appear to exist', status_code=200)

    def test_checkout_not_checked_in_warning(self):
        """Test that checking out a user who is not checked in shows a warning."""
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        # User is not checked in (no "attended" record)
        response = self.client.get(self.get_checkout_url(), {'user': self.student.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "is not currently checked in for this program")

    def test_checkout_unenrollment(self):
        """Test that checking out a user also unenrolls them from selected classes."""
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        # Enroll student in a class
        cls = self.program.classes().first()
        sec = cls.get_sections().first()
        sec.preregister_student(self.student, fast_force_create=True)

        # Verify enrollment
        self.assertTrue(self.student.getEnrolledSections(program=self.program).filter(id=sec.id).exists())

        # Perform checkout and unenroll
        response = self.client.post(self.get_checkout_url(), {
            'user': self.student.id,
            'checkout_student': 'true',
            'unenroll': [sec.id]
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Successfully checked out")

        # Verify unenrollment
        # Wait, sec.unpreregister_student(student, verbs) is called in onsitecheckoutmodule.py
        # I should check if they are still enrolled.
        self.assertFalse(self.student.getEnrolledSections(program=self.program).filter(id=sec.id).exists())
