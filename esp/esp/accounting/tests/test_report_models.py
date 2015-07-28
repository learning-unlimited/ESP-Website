
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

from ..models import LineItemType, Account
from ..views import ReportSection
from django.test import TestCase
from esp.program.models import Program
from test_report_views import TransferDetailsReportTestBase


class TestReportSection(TransferDetailsReportTestBase):
    """ Tests for the underlying Report Models. 
    Specific attention is paid to accuracy of calculations"""

    def setUp(self):
        """ Create a test non-admin account and a test admin account. """
        super(TestReportSection, self).setUp()
        
    def tearDown(self):
        LineItemType.objects.filter(pk__in=[l.id for l in self.line_item_types]).delete()

 