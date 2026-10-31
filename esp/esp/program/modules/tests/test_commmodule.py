"""
Tests for the CommModule (communications panel) handler views.

These complement commpanel.py, which covers the end-to-end
commpanel_old -> commfinal -> cronmail flow. The tests here cover the
other views (commpanel, commprev, commfinal edge cases, maincomm2,
send_test_email), their error handling and access control, and the
static helpers the views rely on.
"""

from django.conf import settings
from django.core import mail
from django.db.models import Q
from django.test import SimpleTestCase

from esp.dbmail.models import MessageRequest, PlainRedirect
from esp.middleware import ESPError_Log
from esp.program.modules.handlers.commmodule import (
    CommModule,
    _program_urls_in_text,
)
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, PersistentQueryFilter

GRADE_WARNING = "You haven't selected a grade range filter"
GUARDIAN_WARNING = 'parent and/or emergency contact emails'
STALE_FILTER_WARNING = 'no longer valid'
MISSING_MSGREQ_ERROR = ('The selected previous message could not be found.  '
                        'Please go back and select a message from the list.')
BAD_TEMPLATE_ERROR = ('The selected email template does not exist.  '
                      'Please go back and try again.')


class CommModuleViewTest(ModuleHandlerTestMixin, ProgramFrameworkTest):
    """Behavioral tests for the CommModule views, driven through the client."""

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 3, 'num_teachers': 3})
        super().setUp(*args, **kwargs)
        self.add_student_profiles()
        self.schedule_randomly()
        self.classreg_students()
        self.admin = self.admins[0]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def make_filter(self, users):
        """Return a saved PersistentQueryFilter matching exactly `users`."""
        return PersistentQueryFilter.create_from_Q(
            ESPUser, Q(id__in=[u.id for u in users]))

    def filter_user_ids(self, filterid):
        pqf = PersistentQueryFilter.getFilterFromID(filterid, ESPUser)
        return set(pqf.getList(ESPUser).values_list('id', flat=True))

    def compose_data(self, filterobj, **overrides):
        data = {
            'filterid': str(filterobj.id),
            'listcount': '3',
            'from': 'director@learningu.org',
            'replyto': 'replies@learningu.org',
            'subject': 'Schedule update',
            'body': '<p>Your class has moved.</p>',
        }
        data.update(overrides)
        return data

    def enrolled_ids(self):
        return set(ESPUser.objects.filter(
            self.program.students(QObjects=True)['enrolled']
        ).values_list('id', flat=True))

    # ------------------------------------------------------------------
    # Access control
    # ------------------------------------------------------------------

    def test_non_admins_cannot_open_commpanel(self):
        for role in ('student', 'teacher'):
            with self.subTest(role=role):
                self.login_as(role)
                response = self.client.get(
                    self.get_module_url('manage', 'commpanel'))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(
                    response, 'errors/program/notanadmin.html')
                self.assertTemplateNotUsed(
                    response, 'program/modules/commmodule/commpanel_new.html')
                self.logout()

    def test_non_admin_cannot_queue_message_via_commfinal(self):
        filterobj = self.make_filter(self.students)
        self.login_as('student')
        response = self.post_to_module(
            'manage', 'commfinal', self.compose_data(filterobj))
        self.assertTemplateUsed(response, 'errors/program/notanadmin.html')
        self.assertFalse(MessageRequest.objects.exists())

    def test_non_admin_cannot_send_test_email(self):
        self.login_as('teacher')
        response = self.post_to_module('manage', 'send_test_email', {
            'from': 'info@learningu.org',
            'subject': 'Hi',
            'body': 'Hi',
        })
        self.assertTemplateUsed(response, 'errors/program/notanadmin.html')
        self.assertEqual(len(mail.outbox), 0)

    # ------------------------------------------------------------------
    # commpanel (main list-selection view)
    # ------------------------------------------------------------------

    def test_commpanel_get_renders_list_selection(self):
        self.login_as('admin')
        response = self.assert_view_ok(
            self.get_module_url('manage', 'commpanel'))
        self.assertTemplateUsed(
            response, 'program/modules/commmodule/commpanel_new.html')

    def test_commpanel_post_program_list_prepares_compose_step(self):
        PlainRedirect.objects.filter(original='info').delete()
        self.login_as('admin')
        response = self.post_to_module('manage', 'commpanel', {
            'recipient_type': 'Student',
            'base_list': 'enrolled',
            'use_checklist': '0',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'program/modules/commmodule/step2.html')

        enrolled = self.enrolled_ids()
        self.assertTrue(enrolled)
        self.assertEqual(self.filter_user_ids(response.context['filterid']),
                         enrolled)
        self.assertEqual(response.context['listcount'], len(enrolled))
        self.assertEqual(response.context['sendto_fn_name'],
                         MessageRequest.SEND_TO_SELF_REAL)
        self.assertEqual(response.context['selected'], 'enrolled')
        self.assertTrue(response.context['from'].endswith(
            '<info@%s>' % settings.SITE_INFO[1]))
        self.assertTrue(any(GRADE_WARNING in w
                            for w in response.context['mailer_warnings']))
        self.assertFalse(any(GUARDIAN_WARNING in w
                             for w in response.context['mailer_warnings']))
        # A missing "info" redirect is recreated so replies have somewhere to go.
        self.assertEqual(
            PlainRedirect.objects.get(original='info').destination,
            settings.DEFAULT_EMAIL_ADDRESSES['default'])

    def test_commpanel_post_grade_filter_clears_grade_warning(self):
        self.login_as('admin')
        response = self.post_to_module('manage', 'commpanel', {
            'recipient_type': 'Student',
            'base_list': 'enrolled',
            'grade_min': '7',
            'grade_max': '12',
            'use_checklist': '0',
        })
        self.assertTemplateUsed(
            response, 'program/modules/commmodule/step2.html')
        self.assertFalse(any(GRADE_WARNING in w
                             for w in response.context['mailer_warnings']))

    def test_commpanel_post_guardian_sendto_warns(self):
        self.login_as('admin')
        response = self.post_to_module('manage', 'commpanel', {
            'recipient_type': 'Student',
            'base_list': 'enrolled',
            'student_sendto_guardian': '1',
            'use_checklist': '0',
        })
        self.assertTemplateUsed(
            response, 'program/modules/commmodule/step2.html')
        self.assertEqual(response.context['sendto_fn_name'],
                         MessageRequest.SEND_TO_GUARDIAN)
        self.assertTrue(any(GUARDIAN_WARNING in w
                            for w in response.context['mailer_warnings']))

    def test_commpanel_post_use_checklist_renders_checklist(self):
        self.login_as('admin')
        response = self.post_to_module('manage', 'commpanel', {
            'recipient_type': 'Student',
            'base_list': 'enrolled',
            'use_checklist': '1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/userchecklist.html')
        self.assertTemplateNotUsed(
            response, 'program/modules/commmodule/step2.html')

    def test_commpanel_post_without_use_checklist_skips_checklist(self):
        self.login_as('admin')
        response = self.post_to_module('manage', 'commpanel', {
            'recipient_type': 'Student',
            'base_list': 'enrolled',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'program/modules/commmodule/step2.html')
        self.assertTemplateNotUsed(response, 'users/userchecklist.html')
        self.assertEqual(self.filter_user_ids(response.context['filterid']),
                         self.enrolled_ids())

    def test_commpanel_post_invalid_criteria_rerenders_with_error(self):
        self.login_as('admin')
        filters_before = PersistentQueryFilter.objects.count()
        response = self.post_to_module('manage', 'commpanel', {
            'recipient_type': 'Student',
            'base_list': 'enrolled',
            'userid': 'not-a-number',
            'use_checklist': '0',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'program/modules/commmodule/commpanel_new.html')
        self.assertIn('User id invalid', response.context['error'])
        self.assertEqual(PersistentQueryFilter.objects.count(), filters_before)

    def test_commpanel_post_without_list_is_an_error(self):
        self.login_as('admin')
        response = self.post_to_module('manage', 'commpanel', {'foo': 'bar'})
        self.assertEqual(response.status_code, 500)
        self.assertTemplateUsed(response, 'error.html')

    def test_commpanel_reuses_earlier_message_request(self):
        filterobj = self.make_filter(self.students[:2])
        old = MessageRequest.createRequest(
            var_dict={'program': self.program},
            subject='Last week',
            recipients=filterobj,
            sendto_fn_name=MessageRequest.SEND_TO_SELF_AND_GUARDIAN,
            sender='director@learningu.org',
            creator=self.admin,
            msgtext='<html>Old body</html>',
            special_headers_dict={'Reply-To': 'replies@learningu.org'},
        )
        old.save()

        self.login_as('admin')
        response = self.post_to_module(
            'manage', 'commpanel', {'msgreq_id': str(old.id)})
        self.assertTemplateUsed(
            response, 'program/modules/commmodule/step2.html')
        ctx = response.context
        self.assertEqual(ctx['filterid'], filterobj.id)
        self.assertEqual(ctx['sendto_fn_name'],
                         MessageRequest.SEND_TO_SELF_AND_GUARDIAN)
        self.assertEqual(ctx['subject'], 'Last week')
        self.assertEqual(ctx['from'], 'director@learningu.org')
        self.assertEqual(ctx['replyto'], 'replies@learningu.org')
        self.assertEqual(ctx['body'], '<html>Old body</html>')
        self.assertGreaterEqual(ctx['listcount'], 2)
        self.assertTrue(any(GUARDIAN_WARNING in w
                            for w in ctx['mailer_warnings']))

    def test_commpanel_rejects_bad_msgreq_id(self):
        self.login_as('admin')
        for msgreq_id in ('abc', '999999', ''):
            with self.subTest(msgreq_id=msgreq_id):
                response = self.post_to_module(
                    'manage', 'commpanel', {'msgreq_id': msgreq_id})
                self.assertTemplateUsed(response, 'error.html')
                self.assertContains(response, MISSING_MSGREQ_ERROR,
                                    status_code=500)

    # ------------------------------------------------------------------
    # commprev (preview step)
    # ------------------------------------------------------------------

    def test_commprev_renders_preview_for_first_recipient(self):
        recipient = self.students[0]
        filterobj = self.make_filter([recipient])
        PlainRedirect.objects.filter(original='info').delete()
        self.login_as('admin')
        response = self.post_to_module('manage', 'commprev', self.compose_data(
            filterobj,
            body='<p>See <img src="/media/uploaded/map.png"></p>',
            **{'from': '', 'replyto': ''}
        ))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'program/modules/commmodule/preview.html')
        ctx = response.context

        # Blank From falls back to the site's info@ address, and Reply-To to From.
        self.assertTrue(ctx['from'].endswith('<info@%s>' % settings.SITE_INFO[1]))
        self.assertEqual(ctx['replyto'], ctx['from'])
        self.assertEqual(
            PlainRedirect.objects.get(original='info').destination,
            settings.DEFAULT_EMAIL_ADDRESSES['default'])

        # Body is wrapped for HTML email and image paths are made absolute.
        self.assertTrue(ctx['body'].startswith('<html>'))
        self.assertIn('src="http://testserver/media/uploaded/map.png"', ctx['body'])

        # The preview is rendered with the default template for the recipient.
        self.assertEqual(ctx['template'], 'default')
        self.assertIn(recipient.username, ctx['rendered_text'])
        self.assertNotIn('{{', ctx['rendered_text'])
        self.assertEqual(ctx['filterid'], filterobj.id)
        self.assertEqual(ctx['sendto_fn_name'], MessageRequest.SEND_TO_SELF_REAL)
        self.assertEqual(ctx['other_program_urls'], [])
        self.assertFalse(MessageRequest.objects.exists())

    def test_commprev_keeps_explicit_from_and_replyto(self):
        filterobj = self.make_filter(self.students)
        self.login_as('admin')
        response = self.post_to_module('manage', 'commprev', self.compose_data(
            filterobj, public_view='on', template='minimal'))
        self.assertEqual(response.context['from'], 'director@learningu.org')
        self.assertEqual(response.context['replyto'], 'replies@learningu.org')
        self.assertTrue(response.context['public_view'])
        self.assertEqual(response.context['template'], 'minimal')

    def test_commprev_rejects_unknown_template(self):
        filterobj = self.make_filter(self.students)
        self.login_as('admin')
        # '../users/recovery' would otherwise load users/recovery_email.html.
        for template in ('nope', '../users/recovery', ''):
            with self.subTest(template=template):
                response = self.post_to_module(
                    'manage', 'commprev',
                    self.compose_data(filterobj, template=template))
                self.assertTemplateUsed(response, 'error.html')
                self.assertContains(response, BAD_TEMPLATE_ERROR,
                                    status_code=500)

    def test_commprev_rejects_off_domain_from_address(self):
        filterobj = self.make_filter(self.students)
        self.login_as('admin')
        response = self.post_to_module('manage', 'commprev', self.compose_data(
            filterobj, **{'from': 'someone@gmail.com'}))
        self.assertContains(response, 'email address must end in @',
                            status_code=500)

    def test_commprev_rejects_bad_recipient_input(self):
        empty = PersistentQueryFilter.create_from_Q(
            ESPUser, Q(username='no-such-user-anywhere'))
        cases = [
            ('non-integer filter', {'filterid': 'abc'}, 'Corrupted POST data'),
            ('stale filter', {'filterid': '999999'}, STALE_FILTER_WARNING),
            ('empty list', {'filterid': str(empty.id)}, 'email 0 people'),
            ('bad sendto', {'sendto_fn_name': 'send_to_nobody'},
             'Invalid sendto function'),
        ]
        filterobj = self.make_filter(self.students)
        self.login_as('admin')
        for label, overrides, message in cases:
            with self.subTest(label):
                response = self.post_to_module(
                    'manage', 'commprev', self.compose_data(filterobj, **overrides))
                self.assertContains(response, message, status_code=500)

    def test_commprev_flags_links_to_other_programs(self):
        filterobj = self.make_filter(self.students)
        own = self.program.getUrlBase()
        self.login_as('admin')
        response = self.post_to_module('manage', 'commprev', self.compose_data(
            filterobj,
            subject='Reminder about /learn/OtherProg/2020_Fall/catalog',
            body='Register at /learn/%s/studentreg' % own,
        ))
        self.assertEqual(response.context['other_program_urls'],
                         ['OtherProg/2020_Fall'])
        self.assertContains(response, 'OtherProg/2020_Fall')

    # ------------------------------------------------------------------
    # commfinal (queues the MessageRequest)
    # ------------------------------------------------------------------

    def test_commfinal_queues_public_guardian_message(self):
        filterobj = self.make_filter(self.students)
        self.login_as('admin')
        response = self.post_to_module('manage', 'commfinal', self.compose_data(
            filterobj,
            sendto_fn_name=MessageRequest.SEND_TO_GUARDIAN,
            public_view='on',
        ))
        self.assertTemplateUsed(
            response, 'program/modules/commmodule/finished.html')

        msg = MessageRequest.objects.get()
        self.assertEqual(msg.recipients_id, filterobj.id)
        self.assertEqual(msg.subject, 'Schedule update')
        self.assertEqual(msg.sender, 'director@learningu.org')
        self.assertEqual(msg.special_headers_dict,
                         {'Reply-To': 'replies@learningu.org'})
        self.assertEqual(msg.sendto_fn_name, MessageRequest.SEND_TO_GUARDIAN)
        self.assertEqual(msg.creator_id, self.admin.id)
        self.assertTrue(msg.public)
        self.assertFalse(msg.processed)
        self.assertIn('Your class has moved.', msg.msgtext)

        # Public messages link to their public page.
        self.assertEqual(response.context['req_id'], msg.id)
        self.assertContains(response, '/email/%d' % msg.id)
        # Nothing is sent synchronously; cronmail does that later.
        self.assertEqual(len(mail.outbox), 0)

    def test_commfinal_strips_base64_images(self):
        filterobj = self.make_filter(self.students)
        self.login_as('admin')
        self.post_to_module('manage', 'commfinal', self.compose_data(
            filterobj,
            body='<p>Hi</p><img src="data:image/png;base64,iVBORw0KGgoAAAA">',
        ))
        msg = MessageRequest.objects.get()
        self.assertIn('Hi', msg.msgtext)
        self.assertNotIn('base64', msg.msgtext)

    def test_commfinal_rejects_unknown_template_without_queueing(self):
        filterobj = self.make_filter(self.students)
        self.login_as('admin')
        cases = [
            ('unknown', {'template': 'nope'}),
            ('path', {'template': '../users/recovery'}),
            # The other-program-links confirmation page renders the template too.
            ('unknown, other program links', {
                'template': 'nope',
                'body': 'Sign up at /teach/OtherProg/2020_Fall/makeaclass'}),
        ]
        for label, overrides in cases:
            with self.subTest(label):
                response = self.post_to_module(
                    'manage', 'commfinal',
                    self.compose_data(filterobj, **overrides))
                self.assertTemplateUsed(response, 'error.html')
                self.assertContains(response, BAD_TEMPLATE_ERROR,
                                    status_code=500)
                self.assertFalse(MessageRequest.objects.exists())

    def test_commfinal_requires_confirmation_for_other_program_links(self):
        filterobj = self.make_filter(self.students)
        data = self.compose_data(
            filterobj, body='Sign up at /teach/OtherProg/2020_Fall/makeaclass')
        self.login_as('admin')

        response = self.post_to_module('manage', 'commfinal', data)
        self.assertTemplateUsed(
            response, 'program/modules/commmodule/preview.html')
        self.assertTrue(response.context['confirm_send_required'])
        self.assertEqual(response.context['other_program_urls'],
                         ['OtherProg/2020_Fall'])
        self.assertFalse(MessageRequest.objects.exists())

        data['confirm_send_with_other_program_links'] = '1'
        response = self.post_to_module('manage', 'commfinal', data)
        self.assertTemplateUsed(
            response, 'program/modules/commmodule/finished.html')
        self.assertEqual(MessageRequest.objects.count(), 1)

    def test_commfinal_rejects_bad_input_without_queueing(self):
        filterobj = self.make_filter(self.students)
        cases = [
            ('non-integer filter', {'filterid': 'abc'}, 'Corrupted POST data'),
            ('stale filter', {'filterid': '999999'}, STALE_FILTER_WARNING),
            ('bad sendto', {'sendto_fn_name': 'send_to_nobody'},
             'Invalid sendto function'),
        ]
        self.login_as('admin')
        for label, overrides, message in cases:
            with self.subTest(label):
                response = self.post_to_module(
                    'manage', 'commfinal', self.compose_data(filterobj, **overrides))
                self.assertContains(response, message, status_code=500)
                self.assertFalse(MessageRequest.objects.exists())

    # ------------------------------------------------------------------
    # maincomm2 (back to compose from preview)
    # ------------------------------------------------------------------

    def test_maincomm2_returns_to_compose_with_values(self):
        filterobj = self.make_filter(self.students)
        self.login_as('admin')
        response = self.post_to_module('manage', 'maincomm2', self.compose_data(
            filterobj, listcount='2500', selected='enrolled', public_view='on'))
        self.assertTemplateUsed(
            response, 'program/modules/commmodule/step2.html')
        ctx = response.context
        self.assertEqual(ctx['subject'], 'Schedule update')
        self.assertEqual(ctx['body'], '<p>Your class has moved.</p>')
        self.assertEqual(ctx['from'], 'director@learningu.org')
        self.assertEqual(ctx['replyto'], 'replies@learningu.org')
        self.assertEqual(ctx['selected'], 'enrolled')
        self.assertTrue(ctx['public_view'])
        self.assertTrue(any('massive mailer to 2500' in w
                            for w in ctx['mailer_warnings']))
        self.assertFalse(MessageRequest.objects.exists())

    # ------------------------------------------------------------------
    # send_test_email
    # ------------------------------------------------------------------

    def test_send_test_email_goes_only_to_requesting_admin(self):
        self.login_as('admin')
        response = self.post_to_module('manage', 'send_test_email', {
            'from': 'director@learningu.org',
            'replyto': 'replies@learningu.org',
            'subject': 'Schedule update',
            'body': 'Hello {{ user.first_name }}',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(),
                         {'success': True, 'email': self.admin.email})

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, [self.admin.email])
        self.assertEqual(sent.subject, '[TEST] Schedule update')
        self.assertEqual(sent.from_email, 'director@learningu.org')
        self.assertEqual(sent.extra_headers['Reply-To'], 'replies@learningu.org')
        self.assertIn('Hello %s' % self.admin.first_name, sent.body)
        self.assertFalse(MessageRequest.objects.exists())

    def test_send_test_email_rejects_get(self):
        self.login_as('admin')
        response = self.client.get(
            self.get_module_url('manage', 'send_test_email'))
        self.assertEqual(response.status_code, 405)
        self.assertFalse(response.json()['success'])
        self.assertEqual(len(mail.outbox), 0)

    def test_send_test_email_reports_send_failure(self):
        self.login_as('admin')
        with self.assertLogs('esp.program.modules.handlers.commmodule',
                             level='ERROR'):
            response = self.post_to_module('manage', 'send_test_email', {
                'from': 'someone@gmail.com',
                'subject': 'Schedule update',
                'body': 'Hello',
            })
        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.json()['success'])
        # Only the server-error report to ADMINS may go out, never the test email.
        self.assertFalse([m for m in mail.outbox
                          if m.subject.startswith('[TEST]')
                          or self.admin.email in m.to])

    def test_send_test_email_rejects_unknown_template(self):
        self.login_as('admin')
        for template in ('nope', '../users/recovery'):
            with self.subTest(template=template):
                response = self.post_to_module('manage', 'send_test_email', {
                    'from': 'director@learningu.org',
                    'subject': 'Schedule update',
                    'body': 'Hello',
                    'template': template,
                })
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(),
                                 {'success': False, 'error': BAD_TEMPLATE_ERROR})
                self.assertEqual(len(mail.outbox), 0)


class CommModuleHelperTest(ProgramFrameworkTest):
    """Direct tests of CommModule's static helpers that need the database."""

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 3, 'num_teachers': 1})
        super().setUp(*args, **kwargs)
        self.filter = PersistentQueryFilter.create_from_Q(
            ESPUser, Q(id__in=[s.id for s in self.students]))

    def test_massive_mailer_threshold(self):
        def massive(listcount):
            return any('massive mailer' in w for w in CommModule.get_mailer_warnings(
                listcount, self.filter.id, MessageRequest.SEND_TO_SELF_REAL))
        self.assertFalse(massive(1999))
        self.assertTrue(massive(2000))
        self.assertTrue(massive('5000'))
        self.assertFalse(massive('not-a-number'))
        self.assertFalse(massive(None))

    def test_guardian_and_emergency_sendtos_warn(self):
        warned = [
            MessageRequest.SEND_TO_GUARDIAN,
            MessageRequest.SEND_TO_EMERGENCY,
            MessageRequest.SEND_TO_SELF_AND_GUARDIAN,
            MessageRequest.SEND_TO_SELF_AND_EMERGENCY,
            MessageRequest.SEND_TO_GUARDIAN_AND_EMERGENCY,
            MessageRequest.SEND_TO_SELF_AND_GUARDIAN_AND_EMERGENCY,
        ]
        for name in warned:
            with self.subTest(name):
                warnings = CommModule.get_mailer_warnings(3, self.filter.id, name)
                self.assertTrue(any(GUARDIAN_WARNING in w for w in warnings))
        for name in (MessageRequest.SEND_TO_SELF, MessageRequest.SEND_TO_SELF_REAL):
            with self.subTest(name):
                warnings = CommModule.get_mailer_warnings(3, self.filter.id, name)
                self.assertFalse(any(GUARDIAN_WARNING in w for w in warnings))

    def test_grade_filter_detection(self):
        no_grade = Q(id__in=[1, 2]) & Q(is_active=True)
        nested_grade = Q(is_active=True) & (
            Q(registrationprofile__student_info__graduation_year__lte=2230)
            | Q(id=1))
        self.assertFalse(CommModule._q_has_grade_filter(no_grade))
        self.assertTrue(CommModule._q_has_grade_filter(nested_grade))
        self.assertFalse(CommModule._q_has_grade_filter('not a Q'))

        graded = PersistentQueryFilter.create_from_Q(ESPUser, nested_grade)
        self.assertFalse(any(GRADE_WARNING in w for w in CommModule.get_mailer_warnings(
            3, graded.id, MessageRequest.SEND_TO_SELF_REAL)))
        self.assertTrue(any(GRADE_WARNING in w for w in CommModule.get_mailer_warnings(
            3, self.filter.id, MessageRequest.SEND_TO_SELF_REAL)))

    def test_get_valid_filter_or_error(self):
        self.assertEqual(CommModule.get_valid_filter_or_error(self.filter.id).id,
                         self.filter.id)
        for bad in (999999, 'abc', None):
            with self.subTest(bad=bad):
                with self.assertRaises(ESPError_Log):
                    CommModule.get_valid_filter_or_error(bad)

    def test_approx_num_of_recipients_scales_by_emails_per_user(self):
        self.assertEqual(
            CommModule.approx_num_of_recipients(self.filter, lambda u: [u.email]),
            3)
        self.assertEqual(
            CommModule.approx_num_of_recipients(
                self.filter, lambda u: [u.email, 'guardian@example.com']),
            6)
        # A sendto function returning nothing still counts each user once.
        self.assertEqual(
            CommModule.approx_num_of_recipients(self.filter, lambda u: []), 3)
        empty = PersistentQueryFilter.create_from_Q(
            ESPUser, Q(username='no-such-user-anywhere'))
        self.assertEqual(
            CommModule.approx_num_of_recipients(empty, lambda u: [u.email]), 0)

    def test_admin_search_entry_only_for_commpanel(self):
        self.assertIsNone(CommModule.get_admin_search_entry(
            self.program, 'manage', 'commprev', None))
        entry = CommModule.get_admin_search_entry(
            self.program, 'manage', 'commpanel', None)
        self.assertEqual(entry.url, '/manage/%s/commpanel' % self.program.getUrlBase())
        self.assertIn('email', entry.keywords)


class ProgramUrlsInTextTest(SimpleTestCase):
    def test_empty_inputs(self):
        self.assertEqual(_program_urls_in_text('', 'Splash/2025_Spring'), [])
        self.assertEqual(_program_urls_in_text('/learn/A/B', ''), [])
        self.assertEqual(_program_urls_in_text(None, 'Splash/2025_Spring'), [])

    def test_finds_other_programs_sorted_and_deduplicated(self):
        text = ('/learn/Splash/2025_Spring/catalog '
                '/TEACH/Splash/2024_Winter/makeaclass '
                '/volunteer/HSSP/2024_Fall/signup '
                '/learn/Splash/2024_Winter/studentreg '
                '/manage/Other/2020_Fall/main')
        self.assertEqual(_program_urls_in_text(text, 'Splash/2025_Spring/'),
                         ['HSSP/2024_Fall', 'Splash/2024_Winter'])
