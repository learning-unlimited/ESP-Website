"""
Tests for the shared chapter email inbox feature (Issue #3831).

Covers:
- Model creation and constraints (8 tests)
- Inbox storage/threading module (7 tests)
- View functionality (12 tests)
- Security (4 tests)
- Notes, canned responses, bulk actions, labels, stats, export (31 tests)
- Scale tests: 1000+ threads, race conditions, exotic inputs (~30 tests)
"""

import json

import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from django.conf import settings
from django.contrib.auth.models import Group
from django.core import mail
from django.db import IntegrityError
from django.test import TestCase, Client, TransactionTestCase

from esp.dbmail.models import (
    InboundEmailThread, InboundEmail, InboundEmailAttachment,
    InboundEmailReadStatus, InboundEmailNote, InboxCannedResponse,
    InboxLabel, InboundEmailThreadLabel,
)
from esp.dbmail.inbox import (
    extract_sender, extract_body_parts, normalize_subject,
    find_or_create_thread, store_inbound_email, strip_bidi_chars,
)
from esp.users.models import ESPUser


def _make_simple_message(from_addr='alice@example.com', to_addr='info@test.learningu.org',
                          subject='Test Subject', body='Hello world',
                          message_id='<test-001@example.com>',
                          in_reply_to='', references=''):
    """Helper to create a simple email.message.Message for testing."""
    msg = MIMEText(body)
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg['Message-ID'] = message_id
    if in_reply_to:
        msg['In-Reply-To'] = in_reply_to
    if references:
        msg['References'] = references
    return msg


def _make_multipart_message(text_body='Text part', html_body='<p>HTML part</p>',
                             attachment_name='test.txt', attachment_data=b'file content',
                             from_addr='bob@example.com', subject='Multipart Test',
                             message_id='<multi-001@example.com>'):
    """Helper to create a multipart message with attachment."""
    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = 'info@test.learningu.org'
    msg['Subject'] = subject
    msg['Message-ID'] = message_id

    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    att = MIMEBase('application', 'octet-stream')
    att.set_payload(attachment_data)
    encoders.encode_base64(att)
    att.add_header('Content-Disposition', 'attachment', filename=attachment_name)
    msg.attach(att)

    return msg


class _AdminUserMixin:
    """Mixin that creates an admin user and logs in."""
    def _setup_admin(self):
        admin_group, _ = Group.objects.get_or_create(name='Administrator')
        self.admin_user = ESPUser.objects.create_user(
            username='inbox_admin',
            password='testpass123',
            email='admin@testserver.learningu.org',
        )
        self.admin_user.groups.add(admin_group)
        self.client = Client()
        self.client.login(username='inbox_admin', password='testpass123')


# ===========================================================================
# A. Model Tests (8 tests)
# ===========================================================================

class InboundEmailModelTest(TestCase):

    def test_thread_creation_defaults(self):
        thread = InboundEmailThread.objects.create(subject='Test Thread')
        self.assertEqual(thread.status, 'open')
        self.assertIsNone(thread.assigned_to)
        self.assertIsNotNone(thread.created_at)
        self.assertIsNotNone(thread.updated_at)

    def test_thread_ordering(self):
        t1 = InboundEmailThread.objects.create(subject='First')
        t2 = InboundEmailThread.objects.create(subject='Second')
        threads = list(InboundEmailThread.objects.all())
        # Most recently updated first
        self.assertEqual(threads[0].id, t2.id)
        self.assertEqual(threads[1].id, t1.id)

    def test_email_creation(self):
        thread = InboundEmailThread.objects.create(subject='Test')
        inbound = InboundEmail.objects.create(
            thread=thread,
            message_id='<test@example.com>',
            sender='Alice <alice@example.com>',
            sender_email='alice@example.com',
            recipient='info',
            subject='Hello',
            body_text='Test body',
        )
        self.assertEqual(inbound.thread, thread)
        self.assertFalse(inbound.is_outbound_reply)
        self.assertIsNotNone(inbound.received_at)

    def test_email_ordering(self):
        thread = InboundEmailThread.objects.create(subject='Test')
        e1 = InboundEmail.objects.create(
            thread=thread, message_id='<1@test>', sender='a',
            sender_email='a@test.com', recipient='info', subject='First',
        )
        e2 = InboundEmail.objects.create(
            thread=thread, message_id='<2@test>', sender='b',
            sender_email='b@test.com', recipient='info', subject='Second',
        )
        emails = list(thread.emails.all())
        self.assertEqual(emails[0].id, e1.id)
        self.assertEqual(emails[1].id, e2.id)

    def test_message_id_unique_constraint(self):
        thread = InboundEmailThread.objects.create(subject='Test')
        InboundEmail.objects.create(
            thread=thread, message_id='<unique@test>',
            sender='a', sender_email='a@test.com', recipient='info', subject='First',
        )
        with self.assertRaises(IntegrityError):
            InboundEmail.objects.create(
                thread=thread, message_id='<unique@test>',
                sender='b', sender_email='b@test.com', recipient='info', subject='Second',
            )

    def test_attachment_creation(self):
        thread = InboundEmailThread.objects.create(subject='Test')
        inbound = InboundEmail.objects.create(
            thread=thread, message_id='<att@test>',
            sender='a', sender_email='a@test.com', recipient='info', subject='Att test',
        )
        att = InboundEmailAttachment.objects.create(
            email=inbound, filename='report.pdf',
            content_type='application/pdf', size=1024,
        )
        self.assertEqual(att.email, inbound)
        self.assertTrue(inbound.has_attachments)

    def test_read_status_unique_together(self):
        thread = InboundEmailThread.objects.create(subject='Test')
        user = ESPUser.objects.create_user(username='reader', password='pass', email='r@test.com')
        InboundEmailReadStatus.objects.create(user=user, thread=thread)
        with self.assertRaises(IntegrityError):
            InboundEmailReadStatus.objects.create(user=user, thread=thread)

    def test_thread_email_count_property(self):
        thread = InboundEmailThread.objects.create(subject='Test')
        self.assertEqual(thread.email_count, 0)
        InboundEmail.objects.create(
            thread=thread, message_id='<c1@test>',
            sender='a', sender_email='a@test.com', recipient='info', subject='One',
        )
        InboundEmail.objects.create(
            thread=thread, message_id='<c2@test>',
            sender='b', sender_email='b@test.com', recipient='info', subject='Two',
        )
        self.assertEqual(thread.email_count, 2)


# ===========================================================================
# B. Inbox Module Tests (7 tests)
# ===========================================================================

class InboxModuleTest(TestCase):

    def test_store_inbound_email_basic(self):
        msg = _make_simple_message()
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        self.assertEqual(result.sender_email, 'alice@example.com')
        self.assertEqual(result.subject, 'Test Subject')
        self.assertEqual(result.body_text, 'Hello world')
        self.assertIsNotNone(result.thread)
        self.assertEqual(result.thread.subject, 'Test Subject')

    def test_store_inbound_email_multipart_with_attachments(self):
        msg = _make_multipart_message()
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        self.assertEqual(result.body_text, 'Text part')
        self.assertIn('HTML part', result.body_html)
        self.assertTrue(result.has_attachments)
        att = result.attachments.first()
        self.assertEqual(att.filename, 'test.txt')
        self.assertEqual(att.size, len(b'file content'))

    def test_store_inbound_email_html_only(self):
        msg = MIMEText('<h1>HTML Only</h1>', 'html')
        msg['From'] = 'html@example.com'
        msg['To'] = 'info@test.learningu.org'
        msg['Subject'] = 'HTML Email'
        msg['Message-ID'] = '<html-001@example.com>'
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        self.assertIn('HTML Only', result.body_html)
        self.assertEqual(result.body_text, '')

    def test_threading_by_in_reply_to(self):
        msg1 = _make_simple_message(message_id='<orig@example.com>', subject='Thread Test')
        result1 = store_inbound_email('info', msg1)

        msg2 = _make_simple_message(
            message_id='<reply@example.com>',
            subject='Re: Thread Test',
            in_reply_to='<orig@example.com>',
        )
        result2 = store_inbound_email('info', msg2)

        self.assertEqual(result1.thread.id, result2.thread.id)

    def test_threading_by_references(self):
        msg1 = _make_simple_message(message_id='<ref-orig@example.com>', subject='Ref Test')
        result1 = store_inbound_email('info', msg1)

        msg2 = _make_simple_message(
            message_id='<ref-reply@example.com>',
            subject='Re: Ref Test',
            references='<ref-orig@example.com>',
        )
        result2 = store_inbound_email('info', msg2)

        self.assertEqual(result1.thread.id, result2.thread.id)

    def test_threading_by_subject_fallback(self):
        msg1 = _make_simple_message(
            message_id='<subj-1@example.com>', subject='Subject Match Test',
        )
        result1 = store_inbound_email('info', msg1)

        msg2 = _make_simple_message(
            message_id='<subj-2@example.com>', subject='Re: Subject Match Test',
        )
        result2 = store_inbound_email('info', msg2)

        self.assertEqual(result1.thread.id, result2.thread.id)

    def test_duplicate_message_id_no_crash(self):
        msg1 = _make_simple_message(message_id='<dup@example.com>')
        result1 = store_inbound_email('info', msg1)
        self.assertIsNotNone(result1)

        msg2 = _make_simple_message(message_id='<dup@example.com>', subject='Duplicate')
        result2 = store_inbound_email('info', msg2)
        self.assertIsNone(result2)

        # Only one record exists
        self.assertEqual(InboundEmail.objects.filter(message_id='<dup@example.com>').count(), 1)


class ExtractSenderTest(TestCase):

    def test_extract_sender_normal(self):
        msg = _make_simple_message(from_addr='Alice <alice@example.com>')
        _, addr = extract_sender(msg)
        self.assertEqual(addr, 'alice@example.com')

    def test_extract_sender_bare(self):
        msg = _make_simple_message(from_addr='bob@example.com')
        _, addr = extract_sender(msg)
        self.assertEqual(addr, 'bob@example.com')

    def test_extract_sender_empty(self):
        msg = _make_simple_message()
        del msg['From']
        _, addr = extract_sender(msg)
        self.assertEqual(addr, '')


class NormalizeSubjectTest(TestCase):

    def test_strips_re_prefix(self):
        self.assertEqual(normalize_subject('Re: Hello'), 'Hello')

    def test_strips_multiple_prefixes(self):
        self.assertEqual(normalize_subject('Re: Fwd: Re: Test'), 'Test')

    def test_strips_fw_prefix(self):
        self.assertEqual(normalize_subject('FW: Important'), 'Important')

    def test_no_prefix(self):
        self.assertEqual(normalize_subject('Just a subject'), 'Just a subject')

    def test_empty_subject(self):
        self.assertEqual(normalize_subject(''), '')


# ===========================================================================
# C. View Tests (12 tests)
# ===========================================================================

class InboxViewTest(_AdminUserMixin, TestCase):

    def setUp(self):
        self._setup_admin()

    def test_inbox_requires_admin(self):
        client = Client()
        response = client.get('/manage/inbox/')
        # Should redirect to login
        self.assertIn(response.status_code, [301, 302])

    def test_inbox_list_empty(self):
        response = self.client.get('/manage/inbox/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your inbox is empty')

    def test_inbox_list_shows_threads(self):
        thread = InboundEmailThread.objects.create(subject='Test Thread Alpha')
        InboundEmail.objects.create(
            thread=thread, message_id='<view-1@test>',
            sender='alice@example.com', sender_email='alice@example.com',
            recipient='info', subject='Test Thread Alpha',
        )
        response = self.client.get('/manage/inbox/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Thread Alpha')

    def test_inbox_list_filter_by_status(self):
        t1 = InboundEmailThread.objects.create(subject='Open Thread', status='open')
        t2 = InboundEmailThread.objects.create(subject='Closed Thread', status='closed')
        response = self.client.get('/manage/inbox/?status=open')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Open Thread')
        self.assertNotContains(response, 'Closed Thread')

    def test_inbox_list_search(self):
        t1 = InboundEmailThread.objects.create(subject='Python Question')
        t2 = InboundEmailThread.objects.create(subject='Java Question')
        InboundEmail.objects.create(
            thread=t1, message_id='<s1@test>',
            sender='a', sender_email='a@test.com', recipient='info', subject='Python Question',
        )
        InboundEmail.objects.create(
            thread=t2, message_id='<s2@test>',
            sender='b', sender_email='b@test.com', recipient='info', subject='Java Question',
        )
        response = self.client.get('/manage/inbox/?q=Python')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python Question')
        self.assertNotContains(response, 'Java Question')

    def test_inbox_list_pagination(self):
        # Create more than 25 threads
        for i in range(30):
            InboundEmailThread.objects.create(subject='Thread %d' % i)
        response = self.client.get('/manage/inbox/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Page 1 of 2')
        response2 = self.client.get('/manage/inbox/?page=2')
        self.assertEqual(response2.status_code, 200)

    def test_thread_detail_shows_emails(self):
        thread = InboundEmailThread.objects.create(subject='Detail Test')
        InboundEmail.objects.create(
            thread=thread, message_id='<det@test>',
            sender='Alice <alice@example.com>', sender_email='alice@example.com',
            recipient='info', subject='Detail Test',
            body_text='Hello from detail test',
        )
        response = self.client.get('/manage/inbox/thread/%d/' % thread.id)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detail Test')
        self.assertContains(response, 'Hello from detail test')

    def test_thread_mark_read_ajax(self):
        thread = InboundEmailThread.objects.create(subject='Read Test')
        response = self.client.post('/manage/inbox/thread/%d/mark-read/' % thread.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            InboundEmailReadStatus.objects.filter(
                user=self.admin_user, thread=thread
            ).exists()
        )

    def test_thread_reply_sends_email(self):
        thread = InboundEmailThread.objects.create(subject='Reply Test')
        InboundEmail.objects.create(
            thread=thread, message_id='<reply-test@test>',
            sender='Alice <alice@example.com>', sender_email='alice@example.com',
            recipient='info', subject='Reply Test',
            body_text='Original message',
        )
        response = self.client.post(
            '/manage/inbox/thread/%d/' % thread.id,
            {'body': 'This is my reply'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reply sent successfully')
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('alice@example.com', mail.outbox[0].to)

    def test_thread_reply_creates_outbound_record(self):
        thread = InboundEmailThread.objects.create(subject='Record Test')
        InboundEmail.objects.create(
            thread=thread, message_id='<record-test@test>',
            sender='Bob <bob@example.com>', sender_email='bob@example.com',
            recipient='info', subject='Record Test',
            body_text='Original',
        )
        self.client.post(
            '/manage/inbox/thread/%d/' % thread.id,
            {'body': 'Reply text'},
        )
        replies = InboundEmail.objects.filter(thread=thread, is_outbound_reply=True)
        self.assertEqual(replies.count(), 1)
        reply = replies.first()
        self.assertEqual(reply.replied_by, self.admin_user)
        self.assertEqual(reply.in_reply_to, '<record-test@test>')

    def test_thread_update_status(self):
        thread = InboundEmailThread.objects.create(subject='Status Test')
        response = self.client.post(
            '/manage/inbox/thread/%d/update/' % thread.id,
            {'status': 'closed'},
        )
        self.assertEqual(response.status_code, 200)
        thread.refresh_from_db()
        self.assertEqual(thread.status, 'closed')

    def test_thread_update_assignment(self):
        thread = InboundEmailThread.objects.create(subject='Assign Test')
        response = self.client.post(
            '/manage/inbox/thread/%d/update/' % thread.id,
            {'assigned_to': str(self.admin_user.id)},
        )
        self.assertEqual(response.status_code, 200)
        thread.refresh_from_db()
        self.assertEqual(thread.assigned_to, self.admin_user)


# ===========================================================================
# D. Security Tests (4 tests)
# ===========================================================================

class InboxSecurityTest(_AdminUserMixin, TestCase):

    def setUp(self):
        self._setup_admin()

    def test_xss_in_subject_escaped(self):
        thread = InboundEmailThread.objects.create(subject='<script>alert(1)</script>')
        InboundEmail.objects.create(
            thread=thread, message_id='<xss@test>',
            sender='a', sender_email='a@test.com', recipient='info',
            subject='<script>alert(1)</script>',
            body_text='safe body',
        )
        response = self.client.get('/manage/inbox/')
        self.assertEqual(response.status_code, 200)
        # The raw <script> tag should NOT appear unescaped
        self.assertNotContains(response, '<script>alert(1)</script>')
        # But the escaped version should be present
        self.assertContains(response, '&lt;script&gt;')

    def test_html_body_in_sandboxed_iframe(self):
        thread = InboundEmailThread.objects.create(subject='Sandbox Test')
        InboundEmail.objects.create(
            thread=thread, message_id='<sandbox@test>',
            sender='a', sender_email='a@test.com', recipient='info',
            subject='Sandbox Test',
            body_html='<script>alert("xss")</script><p>Hello</p>',
        )
        response = self.client.get('/manage/inbox/thread/%d/' % thread.id)
        self.assertEqual(response.status_code, 200)
        # Should use sandboxed iframe
        self.assertContains(response, 'sandbox')
        self.assertContains(response, 'srcdoc=')

    def test_attachment_requires_admin(self):
        thread = InboundEmailThread.objects.create(subject='Att Auth Test')
        inbound = InboundEmail.objects.create(
            thread=thread, message_id='<att-auth@test>',
            sender='a', sender_email='a@test.com', recipient='info',
            subject='Att Auth Test',
        )
        att = InboundEmailAttachment.objects.create(
            email=inbound, filename='secret.txt',
            content_type='text/plain', size=10,
        )
        # Non-admin client
        client = Client()
        response = client.get('/manage/inbox/attachment/%d/' % att.id)
        self.assertIn(response.status_code, [301, 302])

    def test_csrf_protection_on_post(self):
        thread = InboundEmailThread.objects.create(subject='CSRF Test')
        # Create a client that doesn't enforce CSRF (to test the middleware)
        from django.test import Client as DjangoClient
        csrf_client = DjangoClient(enforce_csrf_checks=True)
        csrf_client.login(username='inbox_admin', password='testpass123')
        response = csrf_client.post(
            '/manage/inbox/thread/%d/mark-read/' % thread.id,
        )
        self.assertEqual(response.status_code, 403)


# ===========================================================================
# E. Notes Tests (7 tests)
# ===========================================================================

class InboxNoteTest(_AdminUserMixin, TestCase):

    def setUp(self):
        self._setup_admin()
        self.thread = InboundEmailThread.objects.create(subject='Note Thread')

    def test_add_note(self):
        response = self.client.post(
            '/manage/inbox/thread/%d/note/' % self.thread.id,
            {'note_text': 'This is a test note'},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['note']['note_text'], 'This is a test note')
        self.assertEqual(InboundEmailNote.objects.count(), 1)

    def test_add_note_empty_text_rejected(self):
        response = self.client.post(
            '/manage/inbox/thread/%d/note/' % self.thread.id,
            {'note_text': ''},
        )
        self.assertEqual(response.status_code, 400)

    def test_add_note_whitespace_only_rejected(self):
        response = self.client.post(
            '/manage/inbox/thread/%d/note/' % self.thread.id,
            {'note_text': '   '},
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_own_note(self):
        note = InboundEmailNote.objects.create(
            thread=self.thread, note_text='Delete me', created_by=self.admin_user,
        )
        response = self.client.post('/manage/inbox/note/%d/delete/' % note.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(InboundEmailNote.objects.count(), 0)

    def test_delete_other_user_note_forbidden(self):
        other_user = ESPUser.objects.create_user(
            username='other_admin', password='testpass', email='other@test.com',
        )
        note = InboundEmailNote.objects.create(
            thread=self.thread, note_text='Not yours', created_by=other_user,
        )
        response = self.client.post('/manage/inbox/note/%d/delete/' % note.id)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(InboundEmailNote.objects.count(), 1)

    def test_superuser_can_delete_any_note(self):
        other_user = ESPUser.objects.create_user(
            username='note_author', password='testpass', email='author@test.com',
        )
        note = InboundEmailNote.objects.create(
            thread=self.thread, note_text='Any note', created_by=other_user,
        )
        self.admin_user.is_superuser = True
        self.admin_user.save()
        response = self.client.post('/manage/inbox/note/%d/delete/' % note.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(InboundEmailNote.objects.count(), 0)

    def test_note_get_method_not_allowed(self):
        response = self.client.get(
            '/manage/inbox/thread/%d/note/' % self.thread.id,
        )
        self.assertEqual(response.status_code, 405)


# ===========================================================================
# F. Canned Responses Tests (5 tests)
# ===========================================================================

class InboxCannedResponseTest(_AdminUserMixin, TestCase):

    def setUp(self):
        self._setup_admin()

    def test_get_canned_responses_empty(self):
        response = self.client.get('/manage/inbox/canned-responses/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['responses'], [])

    def test_get_canned_responses_returns_active(self):
        InboxCannedResponse.objects.create(
            title='Welcome', body='Welcome to our program!',
            created_by=self.admin_user, is_active=True,
        )
        InboxCannedResponse.objects.create(
            title='Inactive', body='Should not appear',
            created_by=self.admin_user, is_active=False,
        )
        response = self.client.get('/manage/inbox/canned-responses/')
        data = json.loads(response.content)
        self.assertEqual(len(data['responses']), 1)
        self.assertEqual(data['responses'][0]['title'], 'Welcome')

    def test_canned_response_ordering(self):
        InboxCannedResponse.objects.create(
            title='B Response', body='B', created_by=self.admin_user, seq=2,
        )
        InboxCannedResponse.objects.create(
            title='A Response', body='A', created_by=self.admin_user, seq=1,
        )
        response = self.client.get('/manage/inbox/canned-responses/')
        data = json.loads(response.content)
        self.assertEqual(data['responses'][0]['title'], 'A Response')
        self.assertEqual(data['responses'][1]['title'], 'B Response')

    def test_canned_response_in_thread_view(self):
        InboxCannedResponse.objects.create(
            title='Test Template', body='Template body here',
            created_by=self.admin_user, is_active=True,
        )
        thread = InboundEmailThread.objects.create(subject='Canned Test')
        InboundEmail.objects.create(
            thread=thread, message_id='<canned@test>',
            sender='a@test.com', sender_email='a@test.com',
            recipient='info', subject='Canned Test',
        )
        response = self.client.get('/manage/inbox/thread/%d/' % thread.id)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Template body here')

    def test_canned_response_model_str(self):
        cr = InboxCannedResponse.objects.create(
            title='My Template', body='Body', created_by=self.admin_user,
        )
        self.assertEqual(str(cr), 'My Template')


# ===========================================================================
# G. Bulk Actions Tests (5 tests)
# ===========================================================================

class InboxBulkActionTest(_AdminUserMixin, TestCase):

    def setUp(self):
        self._setup_admin()
        self.t1 = InboundEmailThread.objects.create(subject='Bulk 1', status='open')
        self.t2 = InboundEmailThread.objects.create(subject='Bulk 2', status='open')
        self.t3 = InboundEmailThread.objects.create(subject='Bulk 3', status='in_progress')

    def test_bulk_close(self):
        response = self.client.post('/manage/inbox/bulk/', {
            'action': 'close',
            'thread_ids[]': [str(self.t1.id), str(self.t2.id)],
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['updated'], 2)
        self.t1.refresh_from_db()
        self.t2.refresh_from_db()
        self.assertEqual(self.t1.status, 'closed')
        self.assertEqual(self.t2.status, 'closed')

    def test_bulk_assign_me(self):
        response = self.client.post('/manage/inbox/bulk/', {
            'action': 'assign_me',
            'thread_ids[]': [str(self.t1.id)],
        })
        self.assertEqual(response.status_code, 200)
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.assigned_to, self.admin_user)
        self.assertEqual(self.t1.status, 'in_progress')

    def test_bulk_reopen(self):
        response = self.client.post('/manage/inbox/bulk/', {
            'action': 'open',
            'thread_ids[]': [str(self.t3.id)],
        })
        self.assertEqual(response.status_code, 200)
        self.t3.refresh_from_db()
        self.assertEqual(self.t3.status, 'open')

    def test_bulk_missing_action(self):
        response = self.client.post('/manage/inbox/bulk/', {
            'thread_ids[]': [str(self.t1.id)],
        })
        self.assertEqual(response.status_code, 400)

    def test_bulk_unknown_action(self):
        response = self.client.post('/manage/inbox/bulk/', {
            'action': 'delete_all',
            'thread_ids[]': [str(self.t1.id)],
        })
        self.assertEqual(response.status_code, 400)


# ===========================================================================
# H. Labels Tests (7 tests)
# ===========================================================================

class InboxLabelTest(_AdminUserMixin, TestCase):

    def setUp(self):
        self._setup_admin()
        self.thread = InboundEmailThread.objects.create(subject='Label Thread')
        self.label = InboxLabel.objects.create(name='Urgent', color='#e74c3c')

    def test_get_labels(self):
        response = self.client.get('/manage/inbox/labels/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['labels']), 1)
        self.assertEqual(data['labels'][0]['name'], 'Urgent')

    def test_add_label_to_thread(self):
        response = self.client.post(
            '/manage/inbox/thread/%d/labels/' % self.thread.id,
            {'action': 'add', 'label_id': str(self.label.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(InboundEmailThreadLabel.objects.count(), 1)
        tl = InboundEmailThreadLabel.objects.first()
        self.assertEqual(tl.thread, self.thread)
        self.assertEqual(tl.label, self.label)
        self.assertEqual(tl.added_by, self.admin_user)

    def test_add_duplicate_label_no_error(self):
        InboundEmailThreadLabel.objects.create(
            thread=self.thread, label=self.label, added_by=self.admin_user,
        )
        response = self.client.post(
            '/manage/inbox/thread/%d/labels/' % self.thread.id,
            {'action': 'add', 'label_id': str(self.label.id)},
        )
        self.assertEqual(response.status_code, 200)
        # Still just one
        self.assertEqual(InboundEmailThreadLabel.objects.count(), 1)

    def test_remove_label_from_thread(self):
        InboundEmailThreadLabel.objects.create(
            thread=self.thread, label=self.label, added_by=self.admin_user,
        )
        response = self.client.post(
            '/manage/inbox/thread/%d/labels/' % self.thread.id,
            {'action': 'remove', 'label_id': str(self.label.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(InboundEmailThreadLabel.objects.count(), 0)

    def test_remove_nonexistent_label_no_error(self):
        response = self.client.post(
            '/manage/inbox/thread/%d/labels/' % self.thread.id,
            {'action': 'remove', 'label_id': str(self.label.id)},
        )
        self.assertEqual(response.status_code, 200)

    def test_invalid_label_id(self):
        response = self.client.post(
            '/manage/inbox/thread/%d/labels/' % self.thread.id,
            {'action': 'add', 'label_id': '99999'},
        )
        self.assertEqual(response.status_code, 404)

    def test_labels_appear_in_thread_view(self):
        InboundEmailThreadLabel.objects.create(
            thread=self.thread, label=self.label, added_by=self.admin_user,
        )
        InboundEmail.objects.create(
            thread=self.thread, message_id='<label-view@test>',
            sender='a@test.com', sender_email='a@test.com',
            recipient='info', subject='Label Thread',
        )
        response = self.client.get('/manage/inbox/thread/%d/' % self.thread.id)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Urgent')
        self.assertContains(response, '#e74c3c')


# ===========================================================================
# I. Stats Tests (3 tests)
# ===========================================================================

class InboxStatsTest(_AdminUserMixin, TestCase):

    def setUp(self):
        self._setup_admin()

    def test_stats_endpoint(self):
        InboundEmailThread.objects.create(subject='S1', status='open')
        InboundEmailThread.objects.create(subject='S2', status='open')
        InboundEmailThread.objects.create(subject='S3', status='closed')
        response = self.client.get('/manage/inbox/stats/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['stats']['open'], 2)
        self.assertEqual(data['stats']['closed'], 1)
        self.assertEqual(data['stats']['in_progress'], 0)

    def test_stats_in_list_view(self):
        InboundEmailThread.objects.create(subject='S1', status='open')
        response = self.client.get('/manage/inbox/')
        self.assertEqual(response.status_code, 200)
        # Stats cards should be rendered
        self.assertContains(response, 'inbox-stat-card')

    def test_stats_empty(self):
        response = self.client.get('/manage/inbox/stats/')
        data = json.loads(response.content)
        self.assertEqual(data['stats']['open'], 0)
        self.assertEqual(data['stats']['in_progress'], 0)
        self.assertEqual(data['stats']['closed'], 0)


# ===========================================================================
# J. Export Tests (4 tests)
# ===========================================================================

class InboxExportTest(_AdminUserMixin, TestCase):

    def setUp(self):
        self._setup_admin()
        self.thread = InboundEmailThread.objects.create(subject='Export Thread')
        InboundEmail.objects.create(
            thread=self.thread, message_id='<export@test>',
            sender='Alice <alice@test.com>', sender_email='alice@test.com',
            recipient='info', subject='Export Thread',
            body_text='Message body for export',
        )

    def test_export_text_download(self):
        response = self.client.get(
            '/manage/inbox/thread/%d/export/' % self.thread.id,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/plain', response['Content-Type'])
        self.assertIn('attachment', response['Content-Disposition'])
        content = response.content.decode('utf-8')
        self.assertIn('Export Thread', content)
        self.assertIn('Message body for export', content)
        self.assertIn('alice@test.com', content)

    def test_export_includes_notes(self):
        InboundEmailNote.objects.create(
            thread=self.thread, note_text='Internal export note',
            created_by=self.admin_user,
        )
        response = self.client.get(
            '/manage/inbox/thread/%d/export/' % self.thread.id,
        )
        content = response.content.decode('utf-8')
        self.assertIn('Internal export note', content)
        self.assertIn('INTERNAL NOTES', content)

    def test_forward_thread(self):
        response = self.client.post(
            '/manage/inbox/thread/%d/forward/' % self.thread.id,
            {'email': 'forward@example.com'},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('forward@example.com', mail.outbox[0].to)
        self.assertIn('Fwd:', mail.outbox[0].subject)

    def test_forward_invalid_email(self):
        response = self.client.post(
            '/manage/inbox/thread/%d/forward/' % self.thread.id,
            {'email': 'not-an-email'},
        )
        self.assertEqual(response.status_code, 400)

    def test_forward_empty_email(self):
        response = self.client.post(
            '/manage/inbox/thread/%d/forward/' % self.thread.id,
            {'email': ''},
        )
        self.assertEqual(response.status_code, 400)


# ===========================================================================
# K. Enhanced Model Tests (4 tests)
# ===========================================================================

class InboxEnhancedModelTest(TestCase):

    def test_note_model_str(self):
        user = ESPUser.objects.create_user(
            username='noteuser', password='pass', email='n@test.com',
        )
        thread = InboundEmailThread.objects.create(subject='A very long subject for testing')
        note = InboundEmailNote.objects.create(
            thread=thread, note_text='Test note', created_by=user,
        )
        self.assertIn('noteuser', str(note))

    def test_label_model_str(self):
        label = InboxLabel.objects.create(name='Bug', color='#ff0000')
        self.assertEqual(str(label), 'Bug')

    def test_label_unique_name(self):
        InboxLabel.objects.create(name='Unique', color='#000')
        with self.assertRaises(IntegrityError):
            InboxLabel.objects.create(name='Unique', color='#fff')

    def test_thread_label_unique_together(self):
        user = ESPUser.objects.create_user(
            username='labeler', password='pass', email='l@test.com',
        )
        thread = InboundEmailThread.objects.create(subject='TL Test')
        label = InboxLabel.objects.create(name='Priority', color='#f00')
        InboundEmailThreadLabel.objects.create(
            thread=thread, label=label, added_by=user,
        )
        with self.assertRaises(IntegrityError):
            InboundEmailThreadLabel.objects.create(
                thread=thread, label=label, added_by=user,
            )


# ===========================================================================
# L. Scale Tests — 1000+ Threads (5 tests)
# ===========================================================================

class InboxScaleTest(_AdminUserMixin, TestCase):
    """Tests with large data volumes to ensure queries don't degrade."""

    def setUp(self):
        self._setup_admin()

    def test_list_view_with_1000_threads(self):
        """Inbox list should handle 1000+ threads via pagination."""
        threads = [
            InboundEmailThread(subject='Scale thread %d' % i, status='open')
            for i in range(1000)
        ]
        InboundEmailThread.objects.bulk_create(threads)
        self.assertEqual(InboundEmailThread.objects.count(), 1000)

        # First page should load fine
        response = self.client.get('/manage/inbox/')
        self.assertEqual(response.status_code, 200)
        # Should show 25 per page
        self.assertContains(response, 'Page 1 of 40')

        # Last page should also load
        response = self.client.get('/manage/inbox/?page=40')
        self.assertEqual(response.status_code, 200)

    def test_search_across_1000_threads(self):
        """Search should work across large datasets."""
        threads = [
            InboundEmailThread(subject='Bulk thread %d' % i)
            for i in range(500)
        ]
        threads.append(InboundEmailThread(subject='NEEDLE in haystack'))
        InboundEmailThread.objects.bulk_create(threads)

        # Create an email for the needle thread so search can find it
        needle = InboundEmailThread.objects.get(subject='NEEDLE in haystack')
        InboundEmail.objects.create(
            thread=needle, message_id='<needle@test>',
            sender='finder@test.com', sender_email='finder@test.com',
            recipient='info', subject='NEEDLE in haystack',
        )

        response = self.client.get('/manage/inbox/?q=NEEDLE')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NEEDLE in haystack')

    def test_thread_with_100_emails(self):
        """A thread with 100 emails should render without error."""
        thread = InboundEmailThread.objects.create(subject='Long conversation')
        emails = [
            InboundEmail(
                thread=thread,
                message_id='<scale-%d@test>' % i,
                sender='user%d@test.com' % (i % 10),
                sender_email='user%d@test.com' % (i % 10),
                recipient='info',
                subject='Re: Long conversation',
                body_text='Message number %d in this thread.' % i,
            )
            for i in range(100)
        ]
        InboundEmail.objects.bulk_create(emails)

        response = self.client.get('/manage/inbox/thread/%d/' % thread.id)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Message number 99')

    def test_export_thread_with_50_emails(self):
        """Export should handle threads with many emails without truncation."""
        thread = InboundEmailThread.objects.create(subject='Big Export')
        emails = [
            InboundEmail(
                thread=thread,
                message_id='<export-scale-%d@test>' % i,
                sender='sender%d@test.com' % i,
                sender_email='sender%d@test.com' % i,
                recipient='info',
                subject='Re: Big Export',
                body_text='Export email body %d with some content.' % i,
            )
            for i in range(50)
        ]
        InboundEmail.objects.bulk_create(emails)

        response = self.client.get(
            '/manage/inbox/thread/%d/export/' % thread.id,
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        # All 50 emails should appear — no truncation
        self.assertIn('Export email body 0', content)
        self.assertIn('Export email body 49', content)
        self.assertNotIn('[Content truncated]', content)

    def test_bulk_action_on_100_threads(self):
        """Bulk close should handle 100 threads at once."""
        threads = [
            InboundEmailThread(subject='Bulk scale %d' % i, status='open')
            for i in range(100)
        ]
        InboundEmailThread.objects.bulk_create(threads)
        all_ids = list(
            InboundEmailThread.objects.filter(
                subject__startswith='Bulk scale'
            ).values_list('id', flat=True)
        )
        self.assertEqual(len(all_ids), 100)

        response = self.client.post('/manage/inbox/bulk/', {
            'action': 'close',
            'thread_ids[]': [str(tid) for tid in all_ids],
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['updated'], 100)

        closed = InboundEmailThread.objects.filter(
            id__in=all_ids, status='closed'
        ).count()
        self.assertEqual(closed, 100)


# ===========================================================================
# M. Unicode / Bidi / Exotic Input Tests (8 tests)
# ===========================================================================

class InboxExoticInputTest(TestCase):
    """Tests for Unicode bidi attacks, special characters, and edge cases."""

    def test_bidi_chars_stripped_from_subject(self):
        """Unicode RLO/LRO/RLE/LRE chars should be stripped from subjects."""
        msg = _make_simple_message(
            subject=u'\u202eevil\u202c Safe Subject',
            message_id='<bidi-subj@test>',
        )
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        self.assertNotIn(u'\u202e', result.subject)
        self.assertNotIn(u'\u202c', result.subject)
        self.assertIn('Safe Subject', result.subject)

    def test_bidi_chars_stripped_from_sender(self):
        """Bidi control chars in From header should be stripped."""
        msg = _make_simple_message(
            from_addr=u'\u200fEvil\u200f <evil@test.com>',
            message_id='<bidi-from@test>',
        )
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        self.assertNotIn(u'\u200f', result.sender)

    def test_strip_bidi_chars_function(self):
        """Direct test of strip_bidi_chars utility."""
        self.assertEqual(strip_bidi_chars(u'hello\u202eworld'), 'helloworld')
        self.assertEqual(strip_bidi_chars(u'\u200e\u200f'), '')
        self.assertEqual(strip_bidi_chars(''), '')
        self.assertIsNone(strip_bidi_chars(None))

    def test_null_bytes_in_subject(self):
        """Null bytes in subject should be stripped, not crash storage."""
        msg = _make_simple_message(
            subject='Has\x00null\x00bytes',
            message_id='<null-subj@test>',
        )
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        self.assertNotIn('\x00', result.subject)
        self.assertIn('null', result.subject)

    def test_very_long_subject(self):
        """Subject of 10,000 chars should be truncated to fit DB field."""
        long_subject = 'A' * 10000
        msg = _make_simple_message(
            subject=long_subject,
            message_id='<long-subj@test>',
        )
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.thread)
        self.assertLessEqual(len(result.subject), 998)

    def test_emoji_in_subject(self):
        """Emoji characters in subject should be stored correctly."""
        msg = _make_simple_message(
            subject=u'Help needed \U0001f4e7\U0001f525',
            message_id='<emoji-subj@test>',
        )
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)

    def test_special_chars_in_sender_name(self):
        """Quotes, angle brackets, etc. in sender display name."""
        msg = _make_simple_message(
            from_addr='"O\'Brien, <Bob>" <bob@test.com>',
            message_id='<special-from@test>',
        )
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        self.assertEqual(result.sender_email, 'bob@test.com')

    def test_xss_in_note_text_escaped_in_template(self):
        """Script tags in note text should be escaped when rendered."""
        admin_group, _ = Group.objects.get_or_create(name='Administrator')
        user = ESPUser.objects.create_user(
            username='xss_tester', password='testpass', email='xss@test.com',
        )
        user.groups.add(admin_group)
        client = Client()
        client.login(username='xss_tester', password='testpass')

        thread = InboundEmailThread.objects.create(subject='XSS Note Test')
        InboundEmail.objects.create(
            thread=thread, message_id='<xss-note@test>',
            sender='a@test.com', sender_email='a@test.com',
            recipient='info', subject='XSS Note Test',
        )
        InboundEmailNote.objects.create(
            thread=thread,
            note_text='<script>alert("xss")</script>',
            created_by=user,
        )

        response = client.get('/manage/inbox/thread/%d/' % thread.id)
        self.assertEqual(response.status_code, 200)
        # Raw script tag must not appear
        self.assertNotContains(response, '<script>alert("xss")</script>')
        # Escaped version should be present
        self.assertContains(response, '&lt;script&gt;')


# ===========================================================================
# N. TOCTOU and Reply Edge Case Tests (6 tests)
# ===========================================================================

class InboxReplyEdgeCaseTest(_AdminUserMixin, TestCase):
    """Tests for reply behavior including TOCTOU auto-reopen."""

    def setUp(self):
        self._setup_admin()
        self.thread = InboundEmailThread.objects.create(subject='Reply Edge')
        InboundEmail.objects.create(
            thread=self.thread, message_id='<reply-edge@test>',
            sender='Alice <alice@test.com>', sender_email='alice@test.com',
            recipient='info', subject='Reply Edge',
            body_text='Original message',
        )

    def test_reply_to_closed_thread_reopens_it(self):
        """Replying to a closed thread should auto-reopen it."""
        self.thread.status = 'closed'
        self.thread.save()

        response = self.client.post(
            '/manage/inbox/thread/%d/' % self.thread.id,
            {'body': 'Reopening reply'},
        )
        self.assertEqual(response.status_code, 200)
        self.thread.refresh_from_db()
        # Should be in_progress, not closed
        self.assertEqual(self.thread.status, 'in_progress')

    def test_reply_to_closed_thread_creates_system_note(self):
        """Auto-reopen should leave a system note."""
        self.thread.status = 'closed'
        self.thread.save()

        self.client.post(
            '/manage/inbox/thread/%d/' % self.thread.id,
            {'body': 'Reopen reply'},
        )
        notes = InboundEmailNote.objects.filter(thread=self.thread)
        self.assertEqual(notes.count(), 1)
        self.assertIn('re-opened', notes.first().note_text)

    def test_reply_to_open_thread_moves_to_in_progress(self):
        """Replying to an open thread should set it to in_progress."""
        self.assertEqual(self.thread.status, 'open')

        self.client.post(
            '/manage/inbox/thread/%d/' % self.thread.id,
            {'body': 'First reply'},
        )
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.status, 'in_progress')

    def test_reply_to_in_progress_thread_stays_in_progress(self):
        """Replying to an in_progress thread should not change status."""
        self.thread.status = 'in_progress'
        self.thread.save()

        self.client.post(
            '/manage/inbox/thread/%d/' % self.thread.id,
            {'body': 'Follow-up reply'},
        )
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.status, 'in_progress')

    def test_reply_empty_body_rejected(self):
        """Empty reply body should be rejected."""
        response = self.client.post(
            '/manage/inbox/thread/%d/' % self.thread.id,
            {'body': ''},
        )
        self.assertEqual(response.status_code, 200)
        # No email sent
        self.assertEqual(len(mail.outbox), 0)

    def test_reply_creates_proper_threading_headers(self):
        """Reply should set In-Reply-To and References correctly."""
        self.client.post(
            '/manage/inbox/thread/%d/' % self.thread.id,
            {'body': 'Threaded reply'},
        )
        reply = InboundEmail.objects.filter(
            thread=self.thread, is_outbound_reply=True,
        ).first()
        self.assertIsNotNone(reply)
        self.assertEqual(reply.in_reply_to, '<reply-edge@test>')
        self.assertIn('<reply-edge@test>', reply.references)

    def test_reply_delivery_failure_still_records_email(self):
        """If email delivery fails, reply should still be recorded in DB."""
        from unittest.mock import patch
        with patch('esp.dbmail.views.send_mail', side_effect=Exception('SMTP connection refused')):
            response = self.client.post(
                '/manage/inbox/thread/%d/' % self.thread.id,
                {'body': 'Reply despite SMTP failure'},
            )
        self.assertEqual(response.status_code, 200)
        # Reply still recorded in DB
        reply = InboundEmail.objects.filter(
            thread=self.thread, is_outbound_reply=True,
        ).first()
        self.assertIsNotNone(reply)
        self.assertEqual(reply.body_text, 'Reply despite SMTP failure')
        # Warning shown to user
        self.assertContains(response, 'Reply recorded but email delivery failed')


# ===========================================================================
# O. Race Condition / Concurrent Operation Tests (5 tests)
# ===========================================================================

class InboxConcurrentOperationTest(_AdminUserMixin, TransactionTestCase):
    """Tests for concurrent/race-condition-like scenarios.

    Uses TransactionTestCase so each test has real DB transactions
    (not wrapped in a rollback savepoint), allowing us to test
    integrity constraints under concurrent-like conditions.
    """

    def setUp(self):
        self._setup_admin()

    def test_duplicate_message_id_concurrent_storage(self):
        """Two emails with the same Message-ID: first wins, second is skipped."""
        msg1 = _make_simple_message(
            message_id='<race-dup@test>',
            subject='Race 1',
            from_addr='a@test.com',
        )
        msg2 = _make_simple_message(
            message_id='<race-dup@test>',
            subject='Race 2',
            from_addr='b@test.com',
        )

        result1 = store_inbound_email('info', msg1)
        result2 = store_inbound_email('info', msg2)

        self.assertIsNotNone(result1)
        self.assertIsNone(result2)  # Duplicate should return None
        self.assertEqual(
            InboundEmail.objects.filter(message_id='<race-dup@test>').count(), 1
        )

    def test_concurrent_label_add_idempotent(self):
        """Adding the same label twice should not create duplicates."""
        thread = InboundEmailThread.objects.create(subject='Label Race')
        label = InboxLabel.objects.create(name='RaceLabel', color='#ff0000')

        # First add
        response1 = self.client.post(
            '/manage/inbox/thread/%d/labels/' % thread.id,
            {'action': 'add', 'label_id': str(label.id)},
        )
        self.assertEqual(response1.status_code, 200)

        # Second add (should be idempotent)
        response2 = self.client.post(
            '/manage/inbox/thread/%d/labels/' % thread.id,
            {'action': 'add', 'label_id': str(label.id)},
        )
        self.assertEqual(response2.status_code, 200)

        self.assertEqual(
            InboundEmailThreadLabel.objects.filter(
                thread=thread, label=label
            ).count(), 1
        )

    def test_concurrent_read_status_idempotent(self):
        """Marking a thread read multiple times should not error."""
        thread = InboundEmailThread.objects.create(subject='Read Race')

        # Mark read twice
        r1 = self.client.post(
            '/manage/inbox/thread/%d/mark-read/' % thread.id,
        )
        r2 = self.client.post(
            '/manage/inbox/thread/%d/mark-read/' % thread.id,
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)

        self.assertEqual(
            InboundEmailReadStatus.objects.filter(
                user=self.admin_user, thread=thread,
            ).count(), 1
        )

    def test_bulk_close_already_closed_threads(self):
        """Bulk close on already-closed threads should succeed gracefully."""
        t1 = InboundEmailThread.objects.create(subject='Already Closed', status='closed')
        t2 = InboundEmailThread.objects.create(subject='Still Open', status='open')

        response = self.client.post('/manage/inbox/bulk/', {
            'action': 'close',
            'thread_ids[]': [str(t1.id), str(t2.id)],
        })
        self.assertEqual(response.status_code, 200)
        t1.refresh_from_db()
        t2.refresh_from_db()
        self.assertEqual(t1.status, 'closed')
        self.assertEqual(t2.status, 'closed')

    def test_concurrent_note_add_and_delete(self):
        """Add a note then immediately delete it — both should succeed."""
        thread = InboundEmailThread.objects.create(subject='Note Race')

        # Add note
        response = self.client.post(
            '/manage/inbox/thread/%d/note/' % thread.id,
            {'note_text': 'Temporary note'},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        note_id = data['note']['id']

        # Delete it
        response = self.client.post(
            '/manage/inbox/note/%d/delete/' % note_id,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(InboundEmailNote.objects.filter(id=note_id).count(), 0)


# ===========================================================================
# P. Boundary Condition Tests (8 tests)
# ===========================================================================

class InboxBoundaryTest(_AdminUserMixin, TestCase):
    """Tests for boundary conditions and edge cases."""

    def setUp(self):
        self._setup_admin()

    def test_thread_with_no_emails_shows_gracefully(self):
        """Thread detail page should handle a thread with zero emails."""
        thread = InboundEmailThread.objects.create(subject='Empty Thread')
        response = self.client.get('/manage/inbox/thread/%d/' % thread.id)
        self.assertEqual(response.status_code, 200)

    def test_export_thread_with_no_emails(self):
        """Export of an empty thread should still return a valid download."""
        thread = InboundEmailThread.objects.create(subject='Empty Export')
        response = self.client.get(
            '/manage/inbox/thread/%d/export/' % thread.id,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/plain', response['Content-Type'])
        content = response.content.decode('utf-8')
        self.assertIn('Empty Export', content)

    def test_export_thread_with_attachment_only_email(self):
        """Export should list attachments even if email has no text body."""
        thread = InboundEmailThread.objects.create(subject='Att Only')
        email_obj = InboundEmail.objects.create(
            thread=thread, message_id='<att-only@test>',
            sender='a@test.com', sender_email='a@test.com',
            recipient='info', subject='Att Only',
            body_text='',  # No text body
        )
        InboundEmailAttachment.objects.create(
            email=email_obj, filename='report.pdf',
            content_type='application/pdf', size=1024,
        )
        response = self.client.get(
            '/manage/inbox/thread/%d/export/' % thread.id,
        )
        content = response.content.decode('utf-8')
        self.assertIn('[Attachment: report.pdf (application/pdf)]', content)

    def test_forward_thread_with_attachments_listed(self):
        """Forward should list attachment names in the forwarded body."""
        thread = InboundEmailThread.objects.create(subject='Fwd Att')
        email_obj = InboundEmail.objects.create(
            thread=thread, message_id='<fwd-att@test>',
            sender='a@test.com', sender_email='a@test.com',
            recipient='info', subject='Fwd Att',
            body_text='Has attachments',
        )
        InboundEmailAttachment.objects.create(
            email=email_obj, filename='data.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            size=2048,
        )
        response = self.client.post(
            '/manage/inbox/thread/%d/forward/' % thread.id,
            {'email': 'fwd@example.com'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('data.xlsx', mail.outbox[0].body)

    def test_no_subject_email_gets_placeholder(self):
        """Email with empty subject should get '(No Subject)' placeholder."""
        msg = _make_simple_message(
            subject='',
            message_id='<no-subj@test>',
        )
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        self.assertEqual(result.subject, '(No Subject)')
        self.assertEqual(result.thread.subject, '(No Subject)')

    def test_no_from_header_skips_storage(self):
        """Email with no From header should be skipped (returns None)."""
        msg = _make_simple_message(message_id='<no-from@test>')
        del msg['From']
        result = store_inbound_email('info', msg)
        self.assertIsNone(result)

    def test_missing_message_id_gets_generated(self):
        """Email without Message-ID should get a generated one."""
        msg = _make_simple_message(message_id='')
        del msg['Message-ID']
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        self.assertTrue(result.message_id.startswith('<generated-'))

    def test_pagination_invalid_page_defaults_to_first(self):
        """Invalid page number should not crash."""
        InboundEmailThread.objects.create(subject='Page Test')
        response = self.client.get('/manage/inbox/?page=abc')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/manage/inbox/?page=9999')
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# Q. Threading Algorithm Edge Cases (6 tests)
# ===========================================================================

class InboxThreadingEdgeCaseTest(TestCase):
    """Tests for edge cases in the email threading algorithm."""

    def test_threading_references_reverse_order(self):
        """References header should match most recent ref first."""
        msg1 = _make_simple_message(
            message_id='<chain-1@test>', subject='Chain',
        )
        result1 = store_inbound_email('info', msg1)

        msg2 = _make_simple_message(
            message_id='<chain-2@test>', subject='Re: Chain',
            in_reply_to='<chain-1@test>',
            references='<chain-1@test>',
        )
        result2 = store_inbound_email('info', msg2)

        # Third email references both, should find thread via chain-2 (most recent)
        msg3 = _make_simple_message(
            message_id='<chain-3@test>', subject='Re: Chain',
            references='<chain-1@test> <chain-2@test>',
        )
        result3 = store_inbound_email('info', msg3)

        self.assertEqual(result1.thread.id, result2.thread.id)
        self.assertEqual(result2.thread.id, result3.thread.id)

    def test_threading_broken_references(self):
        """References pointing to non-existent messages should fall back."""
        msg = _make_simple_message(
            message_id='<broken-ref@test>',
            subject='Broken Refs',
            references='<nonexistent-1@test> <nonexistent-2@test>',
        )
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        # Should create a new thread since no refs matched
        self.assertIsNotNone(result.thread)

    def test_threading_subject_match_ignores_case(self):
        """Subject-based threading should be case-insensitive for prefixes."""
        msg1 = _make_simple_message(
            message_id='<case-1@test>',
            subject='Case Test',
        )
        result1 = store_inbound_email('info', msg1)

        msg2 = _make_simple_message(
            message_id='<case-2@test>',
            subject='RE: Case Test',  # Uppercase RE
        )
        result2 = store_inbound_email('info', msg2)

        self.assertEqual(result1.thread.id, result2.thread.id)

    def test_threading_fw_prefix(self):
        """FW: prefix should be stripped for subject matching."""
        msg1 = _make_simple_message(
            message_id='<fw-1@test>',
            subject='Forward Test',
        )
        result1 = store_inbound_email('info', msg1)

        msg2 = _make_simple_message(
            message_id='<fw-2@test>',
            subject='FW: Forward Test',
        )
        result2 = store_inbound_email('info', msg2)

        self.assertEqual(result1.thread.id, result2.thread.id)

    def test_threading_multiple_re_fwd_prefixes(self):
        """Multiple stacked Re:/Fwd: prefixes should be stripped."""
        msg1 = _make_simple_message(
            message_id='<multi-pre-1@test>',
            subject='Multi Prefix',
        )
        result1 = store_inbound_email('info', msg1)

        msg2 = _make_simple_message(
            message_id='<multi-pre-2@test>',
            subject='Re: Fwd: Re: Multi Prefix',
        )
        result2 = store_inbound_email('info', msg2)

        self.assertEqual(result1.thread.id, result2.thread.id)

    def test_in_reply_to_takes_priority_over_subject(self):
        """In-Reply-To should win over subject-based matching."""
        msg1 = _make_simple_message(
            message_id='<priority-1@test>', subject='Same Subject',
        )
        result1 = store_inbound_email('info', msg1)

        msg2 = _make_simple_message(
            message_id='<priority-2@test>', subject='Different Topic',
        )
        result2 = store_inbound_email('info', msg2)

        # Reply to msg2 but with msg1's subject
        msg3 = _make_simple_message(
            message_id='<priority-3@test>',
            subject='Same Subject',
            in_reply_to='<priority-2@test>',
        )
        result3 = store_inbound_email('info', msg3)

        # Should be in msg2's thread (via In-Reply-To), not msg1's (via subject)
        self.assertEqual(result3.thread.id, result2.thread.id)
        self.assertNotEqual(result3.thread.id, result1.thread.id)


# ===========================================================================
# R. Multipart / Attachment Edge Cases (5 tests)
# ===========================================================================

class InboxAttachmentEdgeCaseTest(TestCase):
    """Tests for attachment parsing edge cases."""

    def test_oversized_attachment_skipped(self):
        """Attachments > 25MB should be skipped without crashing."""
        msg = MIMEMultipart()
        msg['From'] = 'big@test.com'
        msg['To'] = 'info@test.learningu.org'
        msg['Subject'] = 'Big Attachment'
        msg['Message-ID'] = '<big-att@test>'
        msg.attach(MIMEText('Has big file', 'plain'))

        att = MIMEBase('application', 'octet-stream')
        # 26MB payload
        att.set_payload(b'X' * (26 * 1024 * 1024))
        encoders.encode_base64(att)
        att.add_header('Content-Disposition', 'attachment', filename='huge.bin')
        msg.attach(att)

        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        # Attachment should be skipped
        self.assertFalse(result.has_attachments)

    def test_attachment_with_no_filename(self):
        """Attachment without a filename should get 'unnamed'."""
        msg = MIMEMultipart()
        msg['From'] = 'noname@test.com'
        msg['To'] = 'info@test.learningu.org'
        msg['Subject'] = 'No Name Att'
        msg['Message-ID'] = '<noname-att@test>'
        msg.attach(MIMEText('Has unnamed file', 'plain'))

        att = MIMEBase('application', 'octet-stream')
        att.set_payload(b'data')
        encoders.encode_base64(att)
        att.add_header('Content-Disposition', 'attachment')  # No filename
        msg.attach(att)

        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_attachments)
        self.assertEqual(result.attachments.first().filename, 'unnamed')

    def test_multipart_without_text_body(self):
        """Multipart email with only HTML part (no text/plain)."""
        msg = MIMEMultipart()
        msg['From'] = 'html-only@test.com'
        msg['To'] = 'info@test.learningu.org'
        msg['Subject'] = 'HTML Only Multi'
        msg['Message-ID'] = '<html-only-multi@test>'
        msg.attach(MIMEText('<p>Only HTML</p>', 'html'))

        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        self.assertEqual(result.body_text, '')
        self.assertIn('Only HTML', result.body_html)

    def test_body_truncation_at_1mb(self):
        """Bodies > 1MB should be truncated with marker."""
        large_body = 'X' * (1024 * 1024 + 100)
        msg = _make_simple_message(
            body=large_body,
            message_id='<large-body@test>',
        )
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        self.assertIn('[Content truncated]', result.body_text)
        self.assertTrue(len(result.body_text) <= 1024 * 1024 + 50)

    def test_long_attachment_filename_truncated(self):
        """Attachment filenames > 255 chars should be truncated."""
        long_name = 'a' * 300 + '.txt'
        msg = _make_multipart_message(
            attachment_name=long_name,
            message_id='<long-fname@test>',
        )
        result = store_inbound_email('info', msg)
        self.assertIsNotNone(result)
        att = result.attachments.first()
        self.assertLessEqual(len(att.filename), 255)


# ===========================================================================
# S. Filter and Assignment Edge Cases (4 tests)
# ===========================================================================

class InboxFilterEdgeCaseTest(_AdminUserMixin, TestCase):
    """Tests for filter combinations and assignment edge cases."""

    def setUp(self):
        self._setup_admin()

    def test_filter_assigned_to_me(self):
        """Filter by mine_only should only show my assigned threads."""
        InboundEmailThread.objects.create(
            subject='Mine', assigned_to=self.admin_user,
        )
        InboundEmailThread.objects.create(subject='Not mine')
        response = self.client.get('/manage/inbox/?mine_only=on')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mine')
        self.assertNotContains(response, 'Not mine')

    def test_assign_self_via_update(self):
        """Assigning to 'self' keyword should set current user."""
        thread = InboundEmailThread.objects.create(subject='Self Assign')
        response = self.client.post(
            '/manage/inbox/thread/%d/update/' % thread.id,
            {'assigned_to': 'self'},
        )
        self.assertEqual(response.status_code, 200)
        thread.refresh_from_db()
        self.assertEqual(thread.assigned_to, self.admin_user)

    def test_unassign_thread(self):
        """Setting assigned_to=0 should unassign the thread."""
        thread = InboundEmailThread.objects.create(
            subject='Unassign', assigned_to=self.admin_user,
        )
        response = self.client.post(
            '/manage/inbox/thread/%d/update/' % thread.id,
            {'assigned_to': '0'},
        )
        self.assertEqual(response.status_code, 200)
        thread.refresh_from_db()
        self.assertIsNone(thread.assigned_to)

    def test_combined_filters(self):
        """Multiple filters applied together."""
        InboundEmailThread.objects.create(
            subject='Open Mine', status='open', assigned_to=self.admin_user,
        )
        InboundEmailThread.objects.create(
            subject='Closed Mine', status='closed', assigned_to=self.admin_user,
        )
        InboundEmailThread.objects.create(
            subject='Open Other', status='open',
        )

        response = self.client.get(
            '/manage/inbox/?status=open&mine_only=on',
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Open Mine')
        self.assertNotContains(response, 'Closed Mine')
        self.assertNotContains(response, 'Open Other')
