
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

from datetime import datetime, timedelta
from model_mommy import mommy
from django.test import TestCase
from esp.users.models import ESPUser
from ..forms import TransferDetailsReportForm
from esp.program.models import Program


class TestTransferDetailsReportForm(TestCase):
    """ Tests for the backend views/models provided by the custom forms app. """
    
    def setUp(self):
        """ Create a test non-admin account and a test admin account. """
        new_student, created = ESPUser.objects.get_or_create(username='forms_student')
        new_student.set_password('password')
        new_student.save()
        new_student.makeRole('Student')
        self.student = new_student

        self.user_programs = mommy.make(Program)

    def test_from_date_is_30days_ago(self):
        user_programs = [self.user_programs]
        form = TransferDetailsReportForm({}, user_programs=user_programs)
        from_date_cmp = datetime.now() - timedelta(days=30)
        from_date = form.fields['from_date'].initial
    
        self.assertEqual(from_date.year, from_date_cmp.year, 'from date year must be the same')
        self.assertEqual(from_date.month, from_date_cmp.month, 'from date month must be the same')
        self.assertEqual(from_date.day, from_date_cmp.day, 'from date day must be the same')