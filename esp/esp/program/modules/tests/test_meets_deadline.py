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

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from esp.program.modules.base import meets_deadline, meets_any_deadline


class MeetsDeadlineValidationTest(SimpleTestCase):
    """
    Tests that @meets_deadline and @meets_any_deadline raise ImproperlyConfigured
    at decoration time (startup time) when an invalid permission extension is used.
    See GitHub issue #1163.
    """

    def test_valid_extension_does_not_raise(self):
        """Known-valid extensions should not raise any exception."""
        # '/Classes' is valid because 'Student/Classes' is in PERMISSION_CHOICES
        try:
            meets_deadline('/Classes')
        except ImproperlyConfigured:
            self.fail("meets_deadline('/Classes') raised ImproperlyConfigured unexpectedly.")

    def test_valid_teacher_extension_does_not_raise(self):
        """Teacher-only extensions should not raise any exception."""
        # '/Availability' maps to 'Teacher/Availability' which is valid
        try:
            meets_deadline('/Availability')
        except ImproperlyConfigured:
            self.fail("meets_deadline('/Availability') raised ImproperlyConfigured unexpectedly.")

    def test_valid_volunteer_extension_does_not_raise(self):
        """Volunteer extensions should not raise any exception."""
        # '/Signup' maps to 'Volunteer/Signup' which is valid
        try:
            meets_deadline('/Signup')
        except ImproperlyConfigured:
            self.fail("meets_deadline('/Signup') raised ImproperlyConfigured unexpectedly.")

    def test_invalid_extension_raises(self):
        """An extension that maps to no valid permission in any tl should raise ImproperlyConfigured."""
        with self.assertRaises(ImproperlyConfigured) as ctx:
            meets_deadline('/NonExistentDeadline')
        self.assertIn('/NonExistentDeadline', str(ctx.exception))

    def test_invalid_extension_error_message_contains_candidates(self):
        """The error message should list the invalid candidate permission strings."""
        with self.assertRaises(ImproperlyConfigured) as ctx:
            meets_deadline('/Bogus')
        msg = str(ctx.exception)
        self.assertIn('Student/Bogus', msg)
        self.assertIn('Teacher/Bogus', msg)
        self.assertIn('Volunteer/Bogus', msg)

    def test_invalid_extension_error_message_contains_valid_choices(self):
        """The error message should list valid deadline choices to aid debugging."""
        with self.assertRaises(ImproperlyConfigured) as ctx:
            meets_deadline('/Bogus')
        msg = str(ctx.exception)
        # Some well-known valid choices should appear in the message
        self.assertIn('Student/Classes', msg)
        self.assertIn('Teacher/Profile', msg)

    def test_meets_any_deadline_invalid_raises(self):
        """meets_any_deadline should also raise when all extensions are invalid."""
        with self.assertRaises(ImproperlyConfigured):
            meets_any_deadline(['/InvalidPerm'])

    def test_meets_any_deadline_one_invalid_raises(self):
        """meets_any_deadline with a mix of valid and invalid extensions should raise for the invalid one."""
        with self.assertRaises(ImproperlyConfigured):
            meets_any_deadline(['/Classes', '/InvalidPerm'])

    def test_meets_any_deadline_all_valid_does_not_raise(self):
        """meets_any_deadline with all valid extensions should not raise."""
        try:
            meets_any_deadline(['/Classes', '/Confirm'])
        except ImproperlyConfigured:
            self.fail("meets_any_deadline with valid extensions raised ImproperlyConfigured unexpectedly.")
