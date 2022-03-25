__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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
from esp.dbmail.models import MessageRequest
from esp.dbmail.cronmail import process_messages, send_email_requests

from django.core import mail

from datetime import datetime, timedelta
import re

class CommunicationsPanelTest(ProgramFrameworkTest):
    """ A test of the basic functionality of the communications panel:
        Does a message
        Future improvements should include:
        - more complex user lists
        - 'smart text' like {{ program.schedule }} in email content
    """

    def setUp(self, *args, **kwargs):
        from esp.program.models import Program
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        # Set up the program -- we want to be sure of these parameters
        kwargs.update({'num_students': 3, 'num_teachers': 3})
        super(CommunicationsPanelTest, self).setUp(*args, **kwargs)

        self.add_student_profiles()
        self.schedule_randomly()
        self.classreg_students()

        # Get and remember the instance of this module
        m = ProgramModule.objects.get(handler='CommModule', module_type='manage')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, m)

    def runTest(self):
        #   Log in an administrator
        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'), "Failed to log in admin user.")

        #   Select users to fetch
        post_data = {
            'submit_user_list': 'true',
            'base_list': 'enrolled',
            'keys': '',
            'finalsent': 'Test List',
            'submitform': 'I have my list, go on!',
        }
        response = self.client.post('/manage/%s/%s' % (self.program.getUrlBase(), 'commpanel_old'), post_data)
        self.assertEqual(response.status_code, 200)

        #   Extract filter ID from response
        s = re.search(r'<input type="hidden" name="filterid" value="([0-9]+)" />', response.content)
        filterid = s.groups()[0]
        s = re.search(r'<input type="hidden" name="listcount" value="([0-9]+)" />', response.content)
        listcount = s.groups()[0]

        #   Enter email information
        post_data = {
            'subject': 'Test Subject 123',
            'body':    'Test Body 123',
            'from':    'from@email-server',
            'replyto': 'replyto@email-server',
            'filterid': filterid,
        }
        response = self.client.post('/manage/%s/%s' % (self.program.getUrlBase(), 'commfinal'), post_data)
        self.assertEqual(response.status_code, 200)

        #   Check that a MessageRequest has been created
        m = MessageRequest.objects.filter(recipients__id=filterid, subject='Test Subject 123')
        self.assertTrue(m.count() == 1)
        self.assertFalse(m[0].processed)

        #   Send out email
        msgs = process_messages()
        send_email_requests()

        #   Check that the email was sent to all students
        self.assertEqual(len(mail.outbox), len(self.students))

        #   Check that the emails matched the entered information
        msg = mail.outbox[0]
        self.assertEqual(msg.subject, 'Test Subject 123')
        self.assertEqual(msg.body, 'Test Body 123')
        self.assertEqual(msg.from_email, 'from@email-server')
        self.assertEqual(msg.extra_headers.get('Reply-To', ''), 'replyto@email-server')

        #   Check that the MessageRequest was marked as processed
        m = MessageRequest.objects.filter(recipients__id=filterid, subject='Test Subject 123')
        self.assertTrue(m.count() == 1)
        self.assertTrue(m[0].processed)
