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
        super().setUp(*args, **kwargs)

        self.add_student_profiles()
        self.schedule_randomly()
        self.classreg_students()

        # Get and remember the instance of this module
        m = ProgramModule.objects.get(handler='CommModule', module_type='manage')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, m)

    def _login_admin_and_get_filter_data(self):
        self.assertTrue(
            self.client.login(username=self.admins[0].username, password='password'),
            "Failed to log in admin user.",
        )

        response = self.client.post('/manage/%s/%s' % (self.program.getUrlBase(), 'commpanel_old'), {
            'submit_user_list': 'true',
            'base_list': 'enrolled',
            'keys': '',
            'finalsent': 'Test List',
            'submitform': 'I have my list, go on!',
        })
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('UTF-8')
        filter_match = re.search(r'<input type="hidden" name="filterid" value="([0-9]+)" />', content)
        listcount_match = re.search(r'<input type="hidden" name="listcount" value="([0-9]+)" />', content)
        self.assertIsNotNone(filter_match, 'Expected filterid hidden input in step2 response')
        self.assertIsNotNone(listcount_match, 'Expected listcount hidden input in step2 response')

        return filter_match.groups()[0], listcount_match.groups()[0], content

    def runTest(self):
        filterid, listcount, unused_content = self._login_admin_and_get_filter_data()

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

    def test_step2_includes_template_selector(self):
        filterid, listcount, content = self._login_admin_and_get_filter_data()

        self.assertIn('Email Template:', content)
        self.assertIn('data-template-key="default"', content)
        self.assertIn('data-template-key="minimal"', content)
        self.assertIn('name="template" id="selected_template" value="default"', content)

    def test_template_selection_persists_preview_to_edit(self):
        filterid, listcount, unused_content = self._login_admin_and_get_filter_data()

        preview_response = self.client.post('/manage/%s/%s' % (self.program.getUrlBase(), 'commprev'), {
            'subject': 'Template persistence test',
            'body': 'Hello from preview',
            'from': 'info@testserver.learningu.org',
            'replyto': 'replyto@testserver.learningu.org',
            'filterid': filterid,
            'listcount': listcount,
            'template': 'minimal',
        })
        self.assertEqual(preview_response.status_code, 200)
        self.assertIn('name="template" value="minimal"', preview_response.content.decode('UTF-8'))

        edit_response = self.client.post('/manage/%s/%s' % (self.program.getUrlBase(), 'maincomm2'), {
            'subject': 'Template persistence test',
            'body': 'Hello from preview',
            'from': 'info@testserver.learningu.org',
            'replyto': 'replyto@testserver.learningu.org',
            'filterid': filterid,
            'listcount': listcount,
            'template': 'minimal',
        })
        self.assertEqual(edit_response.status_code, 200)
        self.assertIn('name="template" id="selected_template" value="minimal"', edit_response.content.decode('UTF-8'))

    def test_commfinal_uses_selected_template_wrapper(self):
        filterid, listcount, unused_content = self._login_admin_and_get_filter_data()

        response = self.client.post('/manage/%s/%s' % (self.program.getUrlBase(), 'commfinal'), {
            'subject': 'Template wrapper test',
            'body': 'Body in minimal template',
            'from': 'info@testserver.learningu.org',
            'replyto': 'replyto@testserver.learningu.org',
            'filterid': filterid,
            'template': 'minimal',
        })
        self.assertEqual(response.status_code, 200)

        req = MessageRequest.objects.get(recipients__id=filterid, subject='Template wrapper test')
        self.assertIn('user.unsubscribe_link', req.msgtext, 'Minimal wrapper should include unsubscribe footer')

        process_messages()
        send_email_requests()

        msg = mail.outbox[0]
        context_dict = {'user': ActionHandler(self.students[0], self.students[0]),
                        'program': ActionHandler(self.program, self.students[0]),
                        'request': ActionHandler(MessageRequest(), self.students[0]),
                        'EMAIL_HOST_SENDER': settings.EMAIL_HOST_SENDER}
        rendered_text = render_to_string('email/minimal_email.html', {'msgbody': 'Body in minimal template'})
        rendered_text = Template(rendered_text).render(DjangoContext(context_dict))
        self.assertEqual(msg.body, strip_tags(rendered_text).strip())

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
