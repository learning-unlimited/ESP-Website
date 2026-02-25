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
from esp.dbmail.models import ActionHandler, MessageRequest
from esp.dbmail.cronmail import process_messages, send_email_requests
from esp.users.models import Permission
from django.contrib.auth.models import Group

from django.conf import settings
from django.core import mail
from django.template import Context as DjangoContext
from django.template import Template
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from datetime import datetime, timedelta
import json
import os
import re
try:
    from unittest.mock import patch, MagicMock
except ImportError:
    from mock import patch, MagicMock

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
        super().setUp(*args, **kwargs)

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
        s = re.search(r'<input type="hidden" name="filterid" value="([0-9]+)" />', response.content.decode('UTF-8'))
        filterid = s.groups()[0]
        s = re.search(r'<input type="hidden" name="listcount" value="([0-9]+)" />', response.content.decode('UTF-8'))
        listcount = s.groups()[0]

        #   Enter email information
        post_data = {
            'subject': 'Test Subject 123',
            'body': 'Test Body 123',
            'from': 'info@testserver.learningu.org',
            'replyto': 'replyto@testserver.learningu.org',
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
        self.assertEqual(msg.from_email, 'info@testserver.learningu.org')
        self.assertEqual(msg.extra_headers.get('Reply-To', ''), 'replyto@testserver.learningu.org')

        #   Check that the HTML-templated email renders correctly
        context_dict = {'user'   : ActionHandler(self.students[0], self.students[0]),
                        'program': ActionHandler(self.program, self.students[0]),
                        'request': ActionHandler(MessageRequest(), self.students[0]),
                        'EMAIL_HOST_SENDER': settings.EMAIL_HOST_SENDER}
        rendered_text = render_to_string('email/default_email.html', {'msgbody': 'Test Body 123',})
        rendered_text = Template(rendered_text).render(DjangoContext(context_dict))
        self.assertEqual(msg.body, strip_tags(rendered_text).strip())


        #   Check that the MessageRequest was marked as processed
        m = MessageRequest.objects.filter(recipients__id=filterid, subject='Test Subject 123')
        self.assertTrue(m.count() == 1)
        self.assertTrue(m[0].processed)

    def test_program_date_variables_in_comms(self):
        """Test that {{ program.date }}, {{ program.date_range }}, {{ program.teacher_reg_deadline }} work in email templates."""
        # ProgramFrameworkTest uses start_time datetime(2222, 7, 7, 7, 5); all timeslots same day
        expected_first_day = 'Jul. 07, 2222'
        expected_date_range = 'Jul. 07, 2222'

        # Add Teacher/Classes/Create permission with known end_date so we can assert on teacher_reg_deadline
        teacher_reg_deadline_dt = datetime(2222, 6, 15, 23, 59)
        expected_teacher_reg_deadline = 'June 15, 2222 11:59 PM'
        Permission.objects.update_or_create(
            program=self.program,
            permission_type='Teacher/Classes/Create',
            role=Group.objects.get(name='Teacher'),
            defaults={'end_date': teacher_reg_deadline_dt}
        )

        context_dict = {'user': ActionHandler(self.students[0], self.students[0]),
                       'program': ActionHandler(self.program, self.students[0]),
                       'request': ActionHandler(MessageRequest(), self.students[0]),
                       'EMAIL_HOST_SENDER': settings.EMAIL_HOST_SENDER}
        body = 'Program first day: {{ program.date }}. Date range: {{ program.date_range }}. Teacher reg deadline: {{ program.teacher_reg_deadline }}.'
        rendered = render_to_string('email/default_email.html', {'msgbody': body})
        rendered = Template(rendered).render(DjangoContext(context_dict))

        # Variables should be substituted (not left as literal {{ ... }})
        self.assertNotIn('{{ program.date }}', rendered)
        self.assertNotIn('{{ program.date_range }}', rendered)
        self.assertNotIn('{{ program.teacher_reg_deadline }}', rendered)

        # Check that the correct values appear in the rendered text
        self.assertIn(expected_first_day, rendered, 'program.date should render as first program day')
        self.assertIn(expected_date_range, rendered, 'program.date_range should render as program date range')
        self.assertIn(expected_teacher_reg_deadline, rendered, 'program.teacher_reg_deadline should render as Teacher/Classes/Create end_date')

    # ------------------------------------------------------------------
    # Tests for the "Process Emails Now" button  (issue #2920)
    # ------------------------------------------------------------------

    def test_process_emails_success(self):
        """POST to /manage/process_emails succeeds for admin and returns JSON."""
        self.client.login(username=self.admins[0].username, password='password')
        response = self.client.post('/manage/process_emails')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content.decode('UTF-8'))
        self.assertEqual(data['status'], 'started')
        self.assertIn('message', data)

    def test_process_emails_rejects_get(self):
        """GET to /manage/process_emails returns 400."""
        self.client.login(username=self.admins[0].username, password='password')
        response = self.client.get('/manage/process_emails')
        self.assertEqual(response.status_code, 400)

    def test_process_emails_rejects_put(self):
        """PUT to /manage/process_emails returns 400."""
        self.client.login(username=self.admins[0].username, password='password')
        response = self.client.put('/manage/process_emails')
        self.assertEqual(response.status_code, 400)

    def test_process_emails_rejects_delete(self):
        """DELETE to /manage/process_emails returns 400."""
        self.client.login(username=self.admins[0].username, password='password')
        response = self.client.delete('/manage/process_emails')
        self.assertEqual(response.status_code, 400)

    def test_process_emails_anonymous_redirect(self):
        """Anonymous user is redirected to login."""
        response = self.client.post('/manage/process_emails')
        self.assertEqual(response.status_code, 302)  # redirect to login

    def test_process_emails_student_forbidden(self):
        """Authenticated student gets 403 (not admin)."""
        self.client.login(username=self.students[0].username, password='password')
        response = self.client.post('/manage/process_emails')
        self.assertEqual(response.status_code, 403)

    def test_process_emails_teacher_forbidden(self):
        """Authenticated teacher gets 403 (not admin)."""
        self.client.login(username=self.teachers[0].username, password='password')
        response = self.client.post('/manage/process_emails')
        self.assertEqual(response.status_code, 403)

    @patch('esp.program.views.subprocess.Popen')
    def test_process_emails_spawns_correct_script(self, mock_popen):
        """Verify subprocess.Popen is called with the correct dbmail_cron.py path."""
        from django.conf import settings as django_settings
        import sys as _sys
        expected_path = os.path.join(django_settings.PROJECT_ROOT, 'dbmail_cron.py')

        self.client.login(username=self.admins[0].username, password='password')
        response = self.client.post('/manage/process_emails')
        self.assertEqual(response.status_code, 200)

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args
        cmd = call_args[0][0]  # first positional arg is the command list
        self.assertEqual(cmd[0], _sys.executable)
        self.assertEqual(cmd[1], expected_path)

    @patch('esp.program.views.subprocess.Popen', side_effect=OSError('No such file'))
    def test_process_emails_subprocess_failure(self, mock_popen):
        """When subprocess.Popen raises, view returns 500 with JSON error."""
        self.client.login(username=self.admins[0].username, password='password')
        response = self.client.post('/manage/process_emails')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content.decode('UTF-8'))
        self.assertEqual(data['status'], 'error')
        self.assertIn('Failed to start email processing', data['message'])

    def test_process_emails_button_on_emails_page(self):
        """The 'Process Emails Now' button appears on /manage/emails."""
        self.client.login(username=self.admins[0].username, password='password')
        response = self.client.get('/manage/emails')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('UTF-8')
        self.assertIn('id="process-emails-btn"', content)
        self.assertIn('Process Emails Now', content)
        self.assertIn('/manage/process_emails', content)

    @patch('esp.program.modules.handlers.commmodule.subprocess.Popen')
    def test_commfinal_auto_triggers_email_processing(self, mock_popen):
        """Submitting an email via commpanel auto-triggers dbmail_cron.py."""
        self.assertTrue(self.client.login(
            username=self.admins[0].username, password='password'))

        # Step 1: generate a user list to get a filterid
        post_data = {
            'submit_user_list': 'true',
            'base_list': 'enrolled',
            'keys': '',
            'finalsent': 'Test List',
            'submitform': 'I have my list, go on!',
        }
        response = self.client.post(
            '/manage/%s/commpanel_old' % self.program.getUrlBase(), post_data)
        self.assertEqual(response.status_code, 200)
        s = re.search(
            r'<input type="hidden" name="filterid" value="([0-9]+)" />',
            response.content.decode('UTF-8'))
        filterid = s.groups()[0]

        # Step 2: submit the email — this should auto-trigger processing
        post_data = {
            'subject': 'Auto-trigger Test',
            'body': 'Testing auto-trigger',
            'from': 'info@testserver.learningu.org',
            'replyto': 'replyto@testserver.learningu.org',
            'filterid': filterid,
        }
        response = self.client.post(
            '/manage/%s/commfinal' % self.program.getUrlBase(), post_data)
        self.assertEqual(response.status_code, 200)

        # Verify subprocess.Popen was called (auto-trigger fired)
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        self.assertTrue(cmd[1].endswith('dbmail_cron.py'))

    @patch('esp.program.modules.handlers.commmodule.subprocess.Popen',
           side_effect=OSError('spawn failed'))
    def test_commfinal_auto_trigger_failure_does_not_break_submit(self, mock_popen):
        """If auto-trigger fails, the email submission still succeeds."""
        from esp.dbmail.models import MessageRequest as MR

        self.assertTrue(self.client.login(
            username=self.admins[0].username, password='password'))

        post_data = {
            'submit_user_list': 'true',
            'base_list': 'enrolled',
            'keys': '',
            'finalsent': 'Test List',
            'submitform': 'I have my list, go on!',
        }
        response = self.client.post(
            '/manage/%s/commpanel_old' % self.program.getUrlBase(), post_data)
        s = re.search(
            r'<input type="hidden" name="filterid" value="([0-9]+)" />',
            response.content.decode('UTF-8'))
        filterid = s.groups()[0]

        post_data = {
            'subject': 'Resilience Test',
            'body': 'This should still be saved',
            'from': 'info@testserver.learningu.org',
            'replyto': 'replyto@testserver.learningu.org',
            'filterid': filterid,
        }
        response = self.client.post(
            '/manage/%s/commfinal' % self.program.getUrlBase(), post_data)

        # Email submission must succeed even though Popen raised
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            MR.objects.filter(subject='Resilience Test').exists(),
            'MessageRequest should be saved even when auto-trigger fails')
