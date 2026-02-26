from __future__ import absolute_import

from unittest.mock import patch

from django.test import override_settings

from esp.dbmail.receivers.classlist import ClassList
from esp.program.tests import ProgramFrameworkTest

from email.message import Message


def _make_handler(msg=None):
    if msg is None:
        msg = Message()
    return ClassList(handler=None, message=msg)


class ClassListTest(ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_teachers': 2,
            'classes_per_teacher': 1,
            'sections_per_class': 1,
            'num_students': 3,
        })
        super(ClassListTest, self).setUp(*args, **kwargs)
        self.add_user_profiles()
        self.schedule_randomly()
        self.classreg_students()

        self.cls = self.program.classes()[0]

    @override_settings(USE_MAILMAN=False)
    def test_process_routes_no_mailman(self):
        handler = _make_handler()
        with patch.object(handler, 'process_nomailman') as mock_nm, \
             patch.object(handler, 'process_mailman') as mock_m:
            handler.process(None, self.cls.id, 'class')
            mock_nm.assert_called_once_with(None, self.cls.id, 'class')
            mock_m.assert_not_called()

    @override_settings(USE_MAILMAN=True)
    def test_process_routes_mailman(self):
        handler = _make_handler()
        with patch.object(handler, 'process_nomailman') as mock_nm, \
             patch.object(handler, 'process_mailman') as mock_m:
            handler.process(None, self.cls.id, 'class')
            mock_m.assert_called_once_with(None, self.cls.id, 'class')
            mock_nm.assert_not_called()

    @override_settings(USE_MAILMAN=False)
    def test_invalid_class_id(self):
        handler = _make_handler()
        handler.process_nomailman(None, -9999, 'class')
        self.assertFalse(handler.send,
                         "send should remain False for an invalid class ID")

    @override_settings(USE_MAILMAN=False)
    def test_user_type_teachers(self):
        handler = _make_handler()
        handler.process_nomailman(None, self.cls.id, 'teachers')

        self.assertTrue(handler.send)

        recipient_strs = ' '.join(handler.recipients)
        self.assertIn(self.program.director_email, recipient_strs)

        teacher_emails = [t.email for t in self.cls.get_teachers()]
        self.assertTrue(any(email in recipient_strs for email in teacher_emails))

        student_emails = []
        for section in self.cls.sections.all():
            student_emails += [s.email for s in section.students()]
        for email in student_emails:
            self.assertNotIn(email, recipient_strs)

    @override_settings(USE_MAILMAN=False)
    def test_user_type_students(self):
        handler = _make_handler()
        handler.process_nomailman(None, self.cls.id, 'students')

        self.assertTrue(handler.send)

        recipient_strs = ' '.join(handler.recipients)
        self.assertIn(self.program.director_email, recipient_strs)

        teacher_emails = [t.email for t in self.cls.get_teachers()]
        for email in teacher_emails:
            self.assertNotIn(email, recipient_strs)

        student_emails = []
        for section in self.cls.sections.all():
            student_emails += [s.email for s in section.students()]
        if student_emails:
            self.assertTrue(any(email in recipient_strs for email in student_emails))

    @override_settings(USE_MAILMAN=False)
    def test_user_type_class(self):
        handler = _make_handler()
        handler.process_nomailman(None, self.cls.id, 'class')

        self.assertTrue(handler.send)

        recipient_strs = ' '.join(handler.recipients)
        self.assertIn(self.program.director_email, recipient_strs)

        teacher_emails = [t.email for t in self.cls.get_teachers()]
        self.assertTrue(any(email in recipient_strs for email in teacher_emails))

        student_emails = []
        for section in self.cls.sections.all():
            student_emails += [s.email for s in section.students()]
        if student_emails:
            self.assertTrue(any(email in recipient_strs for email in student_emails))

    @override_settings(USE_MAILMAN=False)
    def test_send_false_before_process(self):
        handler = _make_handler()
        self.assertFalse(handler.send)

    @override_settings(USE_MAILMAN=False)
    def test_emailcode_set(self):
        handler = _make_handler()
        handler.process_nomailman(None, self.cls.id, 'class')
        self.assertTrue(hasattr(handler, 'emailcode'))
        self.assertEqual(handler.emailcode, self.cls.emailcode())

    @override_settings(USE_MAILMAN=False)
    def test_user_type_case_insensitive(self):
        handler = _make_handler()
        handler.process_nomailman(None, self.cls.id, 'TEACHERS')
        self.assertTrue(handler.send)
        recipient_strs = ' '.join(handler.recipients)
        teacher_emails = [t.email for t in self.cls.get_teachers()]
        self.assertTrue(any(email in recipient_strs for email in teacher_emails))

    @override_settings(USE_MAILMAN=False)
    def test_user_type_with_whitespace(self):
        handler = _make_handler()
        handler.process_nomailman(None, self.cls.id, '  teachers  ')
        self.assertTrue(handler.send)
        recipient_strs = ' '.join(handler.recipients)
        teacher_emails = [t.email for t in self.cls.get_teachers()]
        self.assertTrue(any(email in recipient_strs for email in teacher_emails))

    @override_settings(USE_MAILMAN=True, DEFAULT_EMAIL_ADDRESSES={})
    def test_mailman_missing_moderator_config(self):
        handler = _make_handler()
        handler.process_mailman(None, self.cls.id, 'class')
        self.assertFalse(handler.send,
                         "send should remain False when mailman_moderator is not configured")

    @override_settings(USE_MAILMAN=True, DEFAULT_EMAIL_ADDRESSES={'mailman_moderator': 'mod@example.com'})
    def test_mailman_invalid_class_id(self):
        handler = _make_handler()
        handler.process_mailman(None, -9999, 'class')
        self.assertFalse(handler.send,
                         "send should remain False for invalid class ID in mailman mode")

    @override_settings(
        USE_MAILMAN=True,
        DEFAULT_EMAIL_ADDRESSES={
            'mailman_moderator': 'mod@example.com',
            'default': 'default@example.com',
            'archive': 'archive@example.com'
        }
    )
    @patch('esp.dbmail.receivers.classlist.create_list')
    @patch('esp.dbmail.receivers.classlist.load_list_settings')
    @patch('esp.dbmail.receivers.classlist.add_list_member')
    @patch('esp.dbmail.receivers.classlist.add_list_members')
    @patch('esp.dbmail.receivers.classlist.apply_list_settings')
    @patch('esp.dbmail.receivers.classlist.set_list_moderator_password')
    @patch('esp.dbmail.receivers.classlist.send_mail')
    @patch('esp.dbmail.receivers.classlist.Site')
    def test_mailman_students_list(self, mock_site, mock_send_mail, mock_set_pwd,
                                    mock_apply, mock_add_members, mock_add_member,
                                    mock_load, mock_create):
        mock_site.objects.get_current.return_value.domain = 'example.com'
        mock_set_pwd.return_value = 'test_password'

        handler = _make_handler()
        handler.process_mailman(None, self.cls.id, 'students')

        self.assertTrue(handler.send)
        expected_list_name = f"{self.cls.emailcode()}-students"
        
        mock_create.assert_called_once_with(expected_list_name, 'mod@example.com')
        mock_load.assert_called_once_with(expected_list_name, "lists/class_mailman.config")
        self.assertTrue(mock_add_members.called)
        self.assertTrue(mock_apply.called)
        mock_send_mail.assert_called_once()
        mock_add_member.assert_any_call(expected_list_name, 'archive@example.com')

    @override_settings(
        USE_MAILMAN=True,
        DEFAULT_EMAIL_ADDRESSES={
            'mailman_moderator': 'mod@example.com',
            'default': 'default@example.com'
        }
    )
    @patch('esp.dbmail.receivers.classlist.create_list')
    @patch('esp.dbmail.receivers.classlist.load_list_settings')
    @patch('esp.dbmail.receivers.classlist.add_list_member')
    @patch('esp.dbmail.receivers.classlist.add_list_members')
    @patch('esp.dbmail.receivers.classlist.apply_list_settings')
    @patch('esp.dbmail.receivers.classlist.Site')
    def test_mailman_teachers_list(self, mock_site, mock_apply, mock_add_members,
                                    mock_add_member, mock_load, mock_create):
        mock_site.objects.get_current.return_value.domain = 'example.com'

        handler = _make_handler()
        handler.process_mailman(None, self.cls.id, 'teachers')

        self.assertTrue(handler.send)
        expected_list_name = f"{self.cls.emailcode()}-teachers"
        
        mock_create.assert_called_once_with(expected_list_name, 'mod@example.com')
        
        apply_calls = [call[0][1] for call in mock_apply.call_args_list]
        self.assertTrue(any('default_member_moderation' in settings for settings in apply_calls))
        self.assertTrue(any('generic_nonmember_action' in settings for settings in apply_calls))
        self.assertTrue(any('acceptable_aliases' in settings for settings in apply_calls))

    @override_settings(
        USE_MAILMAN=True,
        DEFAULT_EMAIL_ADDRESSES={
            'mailman_moderator': 'mod@example.com',
            'default': 'default@example.com'
        }
    )
    @patch('esp.dbmail.receivers.classlist.create_list')
    @patch('esp.dbmail.receivers.classlist.load_list_settings')
    @patch('esp.dbmail.receivers.classlist.add_list_member')
    @patch('esp.dbmail.receivers.classlist.add_list_members')
    @patch('esp.dbmail.receivers.classlist.apply_list_settings')
    @patch('esp.dbmail.receivers.classlist.Site')
    def test_mailman_no_archive_address(self, mock_site, mock_apply, mock_add_members,
                                        mock_add_member, mock_load, mock_create):
        mock_site.objects.get_current.return_value.domain = 'example.com'

        handler = _make_handler()
        handler.process_mailman(None, self.cls.id, 'class')

        self.assertTrue(handler.send)
        
        archive_calls = [call for call in mock_add_member.call_args_list 
                        if 'archive' in str(call)]
        self.assertEqual(len(archive_calls), 0)
