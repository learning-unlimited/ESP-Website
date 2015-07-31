
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
import csv
from datetime import datetime
import StringIO

from model_mommy import mommy

from django.core.urlresolvers import reverse

from esp.program.models import Program
from esp.program.tests import ProgramFrameworkTest
from ..models import LineItemType, Account, Transfer


class TransferDetailsReportTestBase(ProgramFrameworkTest):
    """Base Test Case class for Transfer Details Report test_support
       Initializes minimal data set for evaluating report functionality
       and output.
    """
    def setUp(self):
        super(TransferDetailsReportTestBase, self).setUp()

        self.student = self.students[0]
        self.admin = self.admins[0]
        self.line_item_types = []

        for i in range(3):
            program = mommy.make(Program)
            account = mommy.make(Account)
            account.program = program
            account.save()

            line_item_types = mommy.make_recipe('esp.accounting.tests.line_item_type', _quantity=20)

            for line_item in line_item_types:
                line_item.program = program
                line_item.save()
                self.line_item_types.append(line_item)

                transfer = mommy.make(Transfer)
                transfer.user = self.student
                transfer.line_item = line_item
                transfer.source = account
                transfer.amount_dec = line_item.amount_dec
                transfer.save()


class TestTransferDetailsReport(TransferDetailsReportTestBase):
    """ Tests for the underlying Report View. """

    def setUp(self):
        """ Create a test non-admin account and a test admin account. """
        super(TestTransferDetailsReport, self).setUp()

        self.client.login(username=self.admin.username, password='password')
        self.report_url = reverse('transfer-details-report', kwargs={'username':self.student.username})

    def test_only_admin_can_access(self):
        """
        Ensures that only and admin user may access the report
        """
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(self.report_url)
        self.assertEqual(response.status_code, 200)

        #student should not be able to access the report
        self.client.login(username=self.student.username, password='password')
        response = self.client.get(self.report_url)
        self.assertEqual(response.status_code, 403)

        #teacher should not be able to access the report
        self.client.login(username=self.teachers[0].username, password='password')
        response = self.client.get(self.report_url)
        self.assertEqual(response.status_code, 403)

    def test_content_is_html(self):
        """
        Verifies that content is html
        """
        response = self.client.get(self.report_url)
        self.assertIn('html', response['Content-Type'])
        self.assertEqual(response.status_code, 200)

    def test_content_is_html_with_invalid_type(self):
        response = self.client.get(self.report_url,{'file_type':'hjashdjashdj'})
        self.assertIn('html', response['Content-Type'])
        self.assertEqual(response.status_code, 200)

    def test_content_is_pdf(self):
        """
        Verifies that content is pdf when file_type param is pdf
        """
        response = self.client.get(self.report_url,{'file_type':'pdf'})
        self.assertIn('pdf', response['Content-Type'])
        self.assertEqual(response.status_code, 200)

    def test_content_is_csv(self):
        """
        Verifies that content is csv when file_type param is csv
        """
        response = self.client.get(self.report_url,{'file_type':'csv'})
        self.assertIn('csv', response['Content-Type'])
        self.assertEqual(response.status_code, 200)

    def test_csv_matches_model(self):
        """
        Verifies that the data contained in the csv rows matches the data in the report model
        """
        csv_response = self.client.get(self.report_url,{'file_type':'csv'})
        response = self.client.get(self.report_url)
        report_model = response.context['report_model']
        report_transfers = {}

        for section in report_model.sections:
            for transfer in section.transfers:
                report_transfers[transfer.id] = transfer

        csv_rows = StringIO.StringIO(csv_response.content)
        reader = csv.reader(csv_rows, delimiter=',')
        num_cvs_rows = 0

        for row in reader:

            transfer_id = row[1]
            timestamp = str(row[2])
            line_item_text = str(row[3])
            amount_dec = str(row[4])
            report_transfer = report_transfers[int(transfer_id)]

            self.assertEquals(str(report_transfer.timestamp), timestamp)
            self.assertEquals(report_transfer.line_item.text, line_item_text)
            self.assertEquals(str(report_transfer.amount_dec), amount_dec.replace('-', ''))
            num_cvs_rows += 1

        self.assertEqual(num_cvs_rows, len(report_transfers.keys()))

    def test_report_should_show_all_programs(self):
        """
        Report should should show all programs for specific student, when default
        options provided
        """
        csv_response = self.client.get(self.report_url)
        student_programs_names = [p.name for p in self.student.get_purchased_programs()]
        report_programs_names = [p.name for p in response.context['report_model'].user_programs]
        self.assertEquals(report_programs_names, student_programs_names, "Student programs should be equal to programs in report model")

    def test_report_should_show_one_program(self):
        """
        Report should should show one programs for specific student, when one program selected
        """
        student_programs = self.student.get_purchased_programs()

        response = self.client.get(self.report_url,{'program':student_programs[0].id})
        student_programs_names = [p.name for p in student_programs]
        report_program_names = [p.name for p in response.context['report_model'].user_programs]

        self.assertEquals(len(report_program_names), 1)
        self.assertIn(report_program_names[0], student_programs_names)

    def tearDown(self):
        LineItemType.objects.filter(pk__in=[l.id for l in self.line_item_types]).delete()

 