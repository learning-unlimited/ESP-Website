"""Tests for the /manage/emails status page and get_email_data."""
import datetime

from django.db.models import Q

from esp.dbmail.models import MessageRequest, TextOfEmail
from esp.program.views import get_email_data
from esp.tests.factories import make_user
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser, PersistentQueryFilter


class EmailDataTest(TestCase):

    def setUp(self):
        super().setUp()
        self.admin = make_user('Administrator', username='emails_admin')
        self.students = [make_user('Student', username='emails_student_%d' % i)
                         for i in range(3)]
        self.recipients = PersistentQueryFilter.create_from_Q(
            ESPUser, Q(id__in=[s.id for s in self.students]))
        self.now = datetime.datetime.now()
        self.start_date = self.now - datetime.timedelta(days=30)

    def make_request(self, subject='Hello {{ user.first_name }}', days_ago=1,
                     processed=True, sender='info@learningu.org'):
        return MessageRequest.objects.create(
            subject=subject, msgtext='<html>Body</html>', recipients=self.recipients,
            sender=sender, creator=self.admin, processed=processed,
            created_at=self.now - datetime.timedelta(days=days_ago))

    def make_texts(self, req, sent_times):
        """Create one TextOfEmail per entry; None means not sent yet."""
        for i, sent in enumerate(sent_times):
            # Real TextOfEmails carry the per-recipient rendered subject and
            # may use a different From address than the request.
            TextOfEmail.objects.create(
                messagerequest=req, send_to='s%d@example.com' % i,
                send_from='Someone Else <other@learningu.org>',
                subject='Hello Student %d' % i, msgtext='Body',
                created_at=req.created_at, sent=sent)

    def get(self, req):
        return next(r for r in get_email_data(self.start_date) if r.id == req.id)

    def test_counts_use_the_message_request_not_subject_or_sender(self):
        req = self.make_request()
        sent = [self.now - datetime.timedelta(hours=h) for h in (3, 2, 1)]
        self.make_texts(req, sent)
        data = self.get(req)
        self.assertEqual(data.num_rec, 3)
        self.assertEqual(data.num_sent, 3)
        self.assertEqual(data.finished_at, max(sent))

    def test_partially_sent_request_is_not_finished(self):
        req = self.make_request()
        self.make_texts(req, [self.now, None, None])
        data = self.get(req)
        self.assertEqual((data.num_rec, data.num_sent), (3, 1))
        self.assertEqual(data.finished_at, "(Not finished)")

    def test_processed_request_with_no_recipients(self):
        req = self.make_request()
        data = self.get(req)
        self.assertEqual((data.num_rec, data.num_sent), (0, 0))
        self.assertEqual(data.finished_at, "(Not finished)")

    def test_unprocessed_request_estimates_recipients(self):
        req = self.make_request(processed=False)
        data = self.get(req)
        self.assertEqual(data.num_rec, len(self.students))
        self.assertEqual(data.num_sent, 0)
        self.assertEqual(data.finished_at, "(Not finished)")

    def test_filters_by_start_date_newest_first(self):
        old = self.make_request(days_ago=40)
        older = self.make_request(days_ago=5)
        newer = self.make_request(days_ago=1)
        ids = [r.id for r in get_email_data(self.start_date)]
        self.assertEqual(ids, [newer.id, older.id])
        self.assertNotIn(old.id, ids)

    def test_processed_requests_take_one_query(self):
        for days_ago in (1, 2, 3):
            req = self.make_request(days_ago=days_ago)
            self.make_texts(req, [self.now, None])
        with self.assertNumQueries(1):
            data = get_email_data(self.start_date)
            # The template shows each request's creator.
            creators = [r.creator.username for r in data]
        self.assertEqual(creators, ['emails_admin'] * 3)

    def test_view_renders_for_admin(self):
        req = self.make_request(subject='Status page subject')
        self.make_texts(req, [self.now])
        self.assertTrue(self.client.login(username='emails_admin', password='password'))
        response = self.client.get('/manage/emails/', {
            'start_date': self.start_date.strftime('%Y-%m-%d')})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Status page subject')
        self.assertEqual([r.id for r in response.context['requests']], [req.id])

    def test_view_requires_admin(self):
        self.assertTrue(self.client.login(username='emails_student_0', password='password'))
        response = self.client.get('/manage/emails/')
        self.assertNotEqual(response.status_code, 200)
