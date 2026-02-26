from __future__ import absolute_import

from esp.dbmail.models import PlainRedirect
from esp.dbmail.receivers.plainlist import PlainList
from esp.tests.util import CacheFlushTestCase

from email.message import Message


def _make_handler(msg=None):
    if msg is None:
        msg = Message()
    return PlainList(handler=None, message=msg)


class PlainListTest(CacheFlushTestCase):

    def setUp(self):
        PlainRedirect.objects.all().delete()

    def test_no_redirect_match(self):
        handler = _make_handler()
        handler.process('nobody', None)
        self.assertFalse(handler.send)
        self.assertFalse(hasattr(handler, 'recipients'))

    def test_single_redirect(self):
        PlainRedirect.objects.create(original='directors', destination='dir@learningu.org')

        handler = _make_handler()
        handler.process('directors', None)

        self.assertTrue(handler.send)
        self.assertEqual(handler.recipients, ['dir@learningu.org'])

    def test_multiple_redirects(self):
        PlainRedirect.objects.create(original='splash', destination='a@learningu.org')
        PlainRedirect.objects.create(original='splash', destination='b@learningu.org')

        handler = _make_handler()
        handler.process('splash', None)

        self.assertTrue(handler.send)
        self.assertIn('a@learningu.org', handler.recipients)
        self.assertIn('b@learningu.org', handler.recipients)
        self.assertEqual(len(handler.recipients), 2)

    def test_case_insensitive_match(self):
        PlainRedirect.objects.create(original='Directors', destination='dir@learningu.org')

        handler = _make_handler()
        handler.process('directors', None)

        self.assertTrue(handler.send)
        self.assertIn('dir@learningu.org', handler.recipients)

    def test_send_false_before_process(self):
        handler = _make_handler()
        self.assertFalse(handler.send)

    def test_empty_user_match(self):
        PlainRedirect.objects.create(original='test', destination='test@example.com')
        
        handler = _make_handler()
        handler.process('', None)
        
        self.assertFalse(handler.send)

    def test_recipients_list_structure(self):
        PlainRedirect.objects.create(original='test', destination='a@example.com')
        PlainRedirect.objects.create(original='test', destination='b@example.com')
        
        handler = _make_handler()
        handler.process('test', None)
        
        self.assertIsInstance(handler.recipients, list)
        self.assertEqual(len(handler.recipients), 2)
        self.assertIn('a@example.com', handler.recipients)
        self.assertIn('b@example.com', handler.recipients)
