from __future__ import absolute_import

from esp.dbmail.receivers.useremail import UserEmail
from esp.tests.util import CacheFlushTestCase, user_role_setup
from esp.users.models import ESPUser

from email.message import Message


def _make_handler(msg=None):
    if msg is None:
        msg = Message()
    return UserEmail(handler=None, message=msg)


class UserEmailTest(CacheFlushTestCase):

    def setUp(self):
        user_role_setup()
        self.teacher, _ = ESPUser.objects.get_or_create(
            username='test_teacher_ue',
            defaults={
                'first_name': 'Test',
                'last_name': 'Teacher',
                'email': 'teacher@learningu.org',
            }
        )
        self.teacher.makeRole('Teacher')

        self.student, _ = ESPUser.objects.get_or_create(
            username='test_student_ue',
            defaults={
                'first_name': 'Test',
                'last_name': 'Student',
                'email': 'student@learningu.org',
            }
        )
        self.student.makeRole('Student')

    def test_user_not_found(self):
        handler = _make_handler()
        handler.process('nonexistent_user_xyz', None)
        self.assertFalse(handler.send)

    def test_teacher_user_sends(self):
        msg = Message()
        msg['to'] = 'original@learningu.org'

        handler = _make_handler(msg)
        handler.process(self.teacher.username, None)

        self.assertTrue(handler.send)
        self.assertTrue(handler.direct_send)
        self.assertEqual(handler.message['to'], self.teacher.email)

    def test_non_teacher_no_list_id(self):
        msg = Message()

        handler = _make_handler(msg)
        handler.process(self.student.username, None)

        self.assertFalse(handler.send)

    def test_non_teacher_with_list_id(self):
        msg = Message()
        msg['to'] = 'list@learningu.org'
        msg['List-Id'] = '<some-list.learningu.org>'

        handler = _make_handler(msg)
        handler.process(self.student.username, None)

        self.assertTrue(handler.send)
        self.assertTrue(handler.direct_send)
        self.assertEqual(handler.message['to'], self.student.email)

    def test_case_insensitive_username(self):
        msg = Message()
        msg['to'] = 'original@learningu.org'

        handler = _make_handler(msg)
        handler.process(self.teacher.username.upper(), None)

        self.assertTrue(handler.send)
        self.assertEqual(handler.message['to'], self.teacher.email)

    def test_to_header_deleted_and_rewritten(self):
        msg = Message()
        original_to = 'original@learningu.org'
        msg['to'] = original_to

        handler = _make_handler(msg)
        handler.process(self.teacher.username, None)

        self.assertNotEqual(handler.message['to'], original_to)
        self.assertEqual(handler.message['to'], self.teacher.email)

    def test_send_false_before_process(self):
        handler = _make_handler()
        self.assertFalse(handler.send)

    def test_direct_send_not_set_for_nonexistent_user(self):
        handler = _make_handler()
        handler.process('nonexistent_user', None)
        self.assertFalse(hasattr(handler, 'direct_send'))

    def test_admin_user_sends(self):
        admin_user, _ = ESPUser.objects.get_or_create(
            username='test_admin_ue',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'email': 'admin@learningu.org',
            }
        )
        admin_user.makeRole('Administrator')
        admin_user.makeRole('Teacher')

        msg = Message()
        msg['to'] = 'original@learningu.org'

        handler = _make_handler(msg)
        handler.process(admin_user.username, None)

        self.assertTrue(handler.send)
        self.assertTrue(handler.direct_send)
        self.assertEqual(handler.message['to'], admin_user.email)
