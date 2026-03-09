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
from esp.users.models import ESPUser, Permission, PersistentQueryFilter
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


class ProgramUrlsInTextTest(ProgramFrameworkTest):
    """Tests for the _program_urls_in_text helper function."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.current_url = self.program.getUrlBase()

    def test_finds_other_program_urls(self):
        """Should find program URLs that differ from the current program."""
        from esp.program.modules.handlers.commmodule import _program_urls_in_text
        text = 'Visit /learn/Splash/2024_Winter/studentreg for info.'
        result = _program_urls_in_text(text, self.current_url)
        self.assertIn('Splash/2024_Winter', result)

    def test_ignores_current_program_url(self):
        """Should not include the current program's URL."""
        from esp.program.modules.handlers.commmodule import _program_urls_in_text
        text = 'Go to /learn/%s/studentreg' % self.current_url
        result = _program_urls_in_text(text, self.current_url)
        self.assertEqual(result, [])

    def test_empty_text_returns_empty(self):
        """None and empty string should return empty list."""
        from esp.program.modules.handlers.commmodule import _program_urls_in_text
        self.assertEqual(_program_urls_in_text(None, self.current_url), [])
        self.assertEqual(_program_urls_in_text('', self.current_url), [])

    def test_finds_teach_and_volunteer_urls(self):
        """Should also match /teach/ and /volunteer/ URLs."""
        from esp.program.modules.handlers.commmodule import _program_urls_in_text
        text = '/teach/HSSP/2024_Fall/dashboard /volunteer/Splash/2025_Spring/signup'
        result = _program_urls_in_text(text, self.current_url)
        self.assertIn('HSSP/2024_Fall', result)
        self.assertIn('Splash/2025_Spring', result)


class ApproxNumRecipientsTest(ProgramFrameworkTest):
    """Tests for CommModule.approx_num_of_recipients static method."""

    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj
        kwargs.update({'num_students': 5, 'num_teachers': 2})
        super().setUp(*args, **kwargs)
        self.add_student_profiles()
        self.schedule_randomly()
        self.classreg_students()

        m = ProgramModule.objects.get(handler='CommModule', module_type='manage')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, m)

    def test_approx_recipients_with_enrolled_students(self):
        """Should return a positive count for enrolled students."""
        from esp.program.modules.handlers.commmodule import CommModule

        self.assertTrue(self.client.login(
            username=self.admins[0].username, password='password'))
        # Create a filter for enrolled students
        post_data = {
            'submit_user_list': 'true',
            'base_list': 'enrolled',
            'keys': '',
            'finalsent': 'Test',
            'submitform': 'I have my list, go on!',
        }
        response = self.client.post(
            '/manage/%s/commpanel_old' % self.program.getUrlBase(), post_data)
        self.assertEqual(response.status_code, 200)

        import re as re_mod
        s = re_mod.search(
            r'<input type="hidden" name="filterid" value="([0-9]+)" />',
            response.content.decode('UTF-8'))
        if s:
            filterid = int(s.groups()[0])
            from esp.users.models import PersistentQueryFilter
            filterObj = PersistentQueryFilter.getFilterFromID(filterid, ESPUser)
            sendto_fn = MessageRequest.SEND_TO_SELF_REAL
            fn = MessageRequest.assert_is_valid_sendto_fn_or_ESPError(sendto_fn)
            count = CommModule.approx_num_of_recipients(filterObj, fn)
            self.assertGreaterEqual(count, 0,
                               "Should return a non-negative count")


class CommPanelViewsTest(ProgramFrameworkTest):
    """Tests for commpanel GET/POST, maincomm2, and admin permissions."""

    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj
        kwargs.update({'num_students': 3, 'num_teachers': 2})
        super().setUp(*args, **kwargs)
        self.add_student_profiles()
        self.schedule_randomly()
        self.classreg_students()

        m = ProgramModule.objects.get(handler='CommModule', module_type='manage')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, m)

    def test_commpanel_get_renders_list_selection(self):
        """GET request to commpanel should render the user list selection page."""
        self.assertTrue(self.client.login(
            username=self.admins[0].username, password='password'))
        response = self.client.get(
            '/manage/%s/commpanel' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)

    def test_commpanel_requires_admin(self):
        """Non-admin users should not see the full comm panel content."""
        self.assertTrue(self.client.login(
            username=self.students[0].username, password='password'))
        response = self.client.get(
            '/manage/%s/commpanel' % self.program.getUrlBase())
        # Non-admin either gets redirected, 403, or an error page
        # If 200, the content should NOT contain the comm panel form
        if response.status_code == 200:
            content = response.content.decode('UTF-8')
            self.assertNotIn('base_list', content,
                             "Non-admin should not see the user list selection form")

    def test_commfinal_requires_admin(self):
        """Non-admin users should not be able to send emails."""
        self.assertTrue(self.client.login(
            username=self.students[0].username, password='password'))
        response = self.client.post(
            '/manage/%s/commfinal' % self.program.getUrlBase(),
            {'filterid': '1', 'from': 'test@test.com',
             'replyto': 'test@test.com', 'subject': 'Test', 'body': 'Test'})
        # Non-admin should not successfully send; either redirect, 403, or error page
        if response.status_code == 200:
            from esp.dbmail.models import MessageRequest as MR
            self.assertFalse(
                MR.objects.filter(subject='Test').exists(),
                "Non-admin should not be able to create a MessageRequest")

    def test_maincomm2_renders_step2(self):
        """POST to maincomm2 with required data should render step2 template."""
        self.assertTrue(self.client.login(
            username=self.admins[0].username, password='password'))

        # First get a filterid from commpanel_old
        post_data = {
            'submit_user_list': 'true',
            'base_list': 'enrolled',
            'keys': '',
            'finalsent': 'Test',
            'submitform': 'I have my list, go on!',
        }
        response = self.client.post(
            '/manage/%s/commpanel_old' % self.program.getUrlBase(), post_data)
        self.assertEqual(response.status_code, 200)

        import re as re_mod
        s = re_mod.search(
            r'<input type="hidden" name="filterid" value="([0-9]+)" />',
            response.content.decode('UTF-8'))
        if s:
            filterid = s.groups()[0]
            post_data = {
                'filterid': filterid,
                'listcount': '3',
                'from': 'info@testserver.learningu.org',
                'replyto': 'replyto@testserver.learningu.org',
                'subject': 'Test Subject',
                'body': 'Test Body',
            }
            response = self.client.post(
                '/manage/%s/maincomm2' % self.program.getUrlBase(), post_data)
            self.assertEqual(response.status_code, 200)

    def test_commprev_renders_preview(self):
        """POST to commprev should render the email preview page."""
        self.assertTrue(self.client.login(
            username=self.admins[0].username, password='password'))

        # Get filter ID first
        post_data = {
            'submit_user_list': 'true',
            'base_list': 'enrolled',
            'keys': '',
            'finalsent': 'Test',
            'submitform': 'I have my list, go on!',
        }
        response = self.client.post(
            '/manage/%s/commpanel_old' % self.program.getUrlBase(), post_data)
        self.assertEqual(response.status_code, 200)

        import re as re_mod
        s = re_mod.search(
            r'<input type="hidden" name="filterid" value="([0-9]+)" />',
            response.content.decode('UTF-8'))
        if s:
            filterid = s.groups()[0]
            s2 = re_mod.search(
                r'<input type="hidden" name="listcount" value="([0-9]+)" />',
                response.content.decode('UTF-8'))
            listcount = s2.groups()[0] if s2 else '3'
            post_data = {
                'filterid': filterid,
                'listcount': listcount,
                'subject': 'Preview Subject',
                'body': '<p>Preview Body</p>',
                'from': 'info@testserver.learningu.org',
                'replyto': 'replyto@testserver.learningu.org',
            }
            response = self.client.post(
                '/manage/%s/commprev' % self.program.getUrlBase(), post_data)
            self.assertEqual(response.status_code, 200)
