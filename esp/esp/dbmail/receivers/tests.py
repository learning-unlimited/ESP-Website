"""
Unit tests for esp/dbmail/receivers/

Covers:
  - plainlist.py  → PlainList
  - useremail.py  → UserEmail
  - classlist.py  → ClassList
  - sectionlist.py → SectionList

Run with:
    python manage.py test esp.dbmail.receivers.tests --verbosity=2

Coverage:
    venv/bin/python -m coverage run --source=esp/dbmail/receivers manage.py test esp.dbmail.receivers.tests
    venv/bin/python -m coverage html -d coverage_report
    xdg-open coverage_report/index.html
"""

from unittest.mock import patch, MagicMock, PropertyMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model


# ---------------------------------------------------------------------------
# Helpers / shared mocks
# ---------------------------------------------------------------------------

def _make_user(username="testuser", email="test@example.com", is_teacher=False):
    """Return a lightweight mock that looks like an ESPUser."""
    user = MagicMock()
    user.username = username
    user.email = email
    user.isTeacher.return_value = is_teacher
    user.get_email_sendto_address.return_value = email
    return user


def _make_message(list_id=None):
    """Return a mock email message object."""
    msg = MagicMock()
    msg.__getitem__ = lambda self, key: list_id if key == "List-Id" else None
    msg.__setitem__ = MagicMock()
    msg.__delitem__ = MagicMock()
    return msg


# ===========================================================================
# PlainList tests
# ===========================================================================

class PlainListProcessTest(TestCase):
    """Tests for PlainList.process()"""

    def _get_handler(self, message=None):
        from esp.dbmail.receivers.plainlist import PlainList
        mock_message = message or _make_message()
        handler = PlainList(MagicMock(), mock_message)
        handler.send = False
        handler.recipients = []
        return handler

    @patch("esp.dbmail.receivers.plainlist.PlainRedirect.objects.filter")
    def test_process_no_redirect_found(self, mock_filter):
        """When no PlainRedirect matches, send stays False."""
        # Make len(redirects.values('id')[:1]) == 0
        mock_qs = MagicMock()
        mock_values = MagicMock()
        mock_slice = MagicMock()
        mock_slice.__len__ = MagicMock(return_value=0)
        mock_values.__getitem__ = MagicMock(return_value=mock_slice)
        mock_qs.values.return_value = mock_values
        mock_filter.return_value = mock_qs

        handler = self._get_handler()
        handler.process("nonexistent@example.com", None)

        self.assertFalse(handler.send)
        self.assertEqual(handler.recipients, [])

    @patch("esp.dbmail.receivers.plainlist.PlainRedirect.objects.filter")
    def test_process_single_redirect(self, mock_filter):
        """Single matching redirect → send=True, recipient set correctly."""
        redirect = MagicMock()
        redirect.destination = "dest@example.com"

        mock_qs = MagicMock()
        mock_values = MagicMock()
        mock_slice = MagicMock()
        mock_slice.__len__ = MagicMock(return_value=1)
        mock_values.__getitem__ = MagicMock(return_value=mock_slice)
        mock_qs.values.return_value = mock_values
        mock_qs.__iter__ = MagicMock(return_value=iter([redirect]))
        mock_filter.return_value = mock_qs

        handler = self._get_handler()
        handler.process("alias@example.com", None)

        self.assertTrue(handler.send)
        self.assertIn("dest@example.com", handler.recipients)

    @patch("esp.dbmail.receivers.plainlist.PlainRedirect.objects.filter")
    def test_process_multiple_redirects(self, mock_filter):
        """Multiple matching redirects → all destinations in recipients."""
        r1 = MagicMock(); r1.destination = "a@example.com"
        r2 = MagicMock(); r2.destination = "b@example.com"

        mock_qs = MagicMock()
        mock_values = MagicMock()
        mock_slice = MagicMock()
        mock_slice.__len__ = MagicMock(return_value=2)
        mock_values.__getitem__ = MagicMock(return_value=mock_slice)
        mock_qs.values.return_value = mock_values
        mock_qs.__iter__ = MagicMock(return_value=iter([r1, r2]))
        mock_filter.return_value = mock_qs

        handler = self._get_handler()
        handler.process("alias@example.com", None)

        self.assertTrue(handler.send)
        self.assertIn("a@example.com", handler.recipients)
        self.assertIn("b@example.com", handler.recipients)

    @patch("esp.dbmail.receivers.plainlist.PlainRedirect.objects.filter")
    def test_process_empty_redirects_list(self, mock_filter):
        """Empty redirect list → send stays False."""
        mock_qs = MagicMock()
        mock_values = MagicMock()
        mock_slice = MagicMock()
        mock_slice.__len__ = MagicMock(return_value=0)
        mock_values.__getitem__ = MagicMock(return_value=mock_slice)
        mock_qs.values.return_value = mock_values
        mock_filter.return_value = mock_qs

        handler = self._get_handler()
        handler.process("nobody@example.com", None)

        self.assertFalse(handler.send)


# ===========================================================================
# UserEmail tests
# ===========================================================================

class UserEmailProcessTest(TestCase):
    """Tests for UserEmail.process()"""

    def _get_handler(self, list_id=None):
        from esp.dbmail.receivers.useremail import UserEmail
        mock_message = _make_message(list_id=list_id)
        handler = UserEmail(MagicMock(), mock_message)
        handler.send = False
        handler.direct_send = False
        handler.recipients = []
        return handler

    @patch("esp.dbmail.receivers.useremail.ESPUser.objects.get")
    def test_process_user_does_not_exist(self, mock_get):
        """User does not exist → early return, nothing set."""
        from esp.users.models import ESPUser
        mock_get.side_effect = ESPUser.DoesNotExist

        handler = self._get_handler()
        handler.process("ghost", MagicMock())

        self.assertFalse(handler.send)
        self.assertFalse(handler.direct_send)

    @patch("esp.dbmail.receivers.useremail.ESPUser.objects.get")
    def test_process_teacher_gets_direct_send(self, mock_get):
        """User is a teacher → direct_send and send set to True."""
        user = _make_user(is_teacher=True, email="teacher@example.com")
        mock_get.return_value = user

        handler = self._get_handler()
        handler.process("teacheruser", MagicMock())

        self.assertTrue(handler.send)
        self.assertTrue(handler.direct_send)
        handler.message.__setitem__.assert_called_with("to", "teacher@example.com")

    @patch("esp.dbmail.receivers.useremail.ESPUser.objects.get")
    def test_process_non_teacher_with_list_id(self, mock_get):
        """User is NOT a teacher but List-Id present → direct_send set."""
        user = _make_user(is_teacher=False, email="student@example.com")
        mock_get.return_value = user

        msg = MagicMock()
        msg.__getitem__ = lambda self, k: "some-list-id" if k == "List-Id" else None
        msg.__setitem__ = MagicMock()
        msg.__delitem__ = MagicMock()

        from esp.dbmail.receivers.useremail import UserEmail
        handler = UserEmail(MagicMock(), msg)
        handler.send = False
        handler.direct_send = False

        handler.process("studentuser", MagicMock())

        self.assertTrue(handler.send)
        self.assertTrue(handler.direct_send)

    @patch("esp.dbmail.receivers.useremail.ESPUser.objects.get")
    def test_process_non_teacher_no_list_id(self, mock_get):
        """User is NOT a teacher and NO List-Id → nothing set."""
        user = _make_user(is_teacher=False, email="student@example.com")
        mock_get.return_value = user

        msg = MagicMock()
        msg.__getitem__ = lambda self, k: None
        msg.__setitem__ = MagicMock()
        msg.__delitem__ = MagicMock()

        from esp.dbmail.receivers.useremail import UserEmail
        handler = UserEmail(MagicMock(), msg)
        handler.send = False
        handler.direct_send = False

        handler.process("studentuser", MagicMock())

        self.assertFalse(handler.send)
        self.assertFalse(handler.direct_send)

    @patch("esp.dbmail.receivers.useremail.ESPUser.objects.get")
    def test_process_username_case_insensitive(self, mock_get):
        """Username lookup is case-insensitive."""
        user = _make_user(is_teacher=True, email="t@example.com")
        mock_get.return_value = user

        handler = self._get_handler()
        handler.process("TeacherUser", MagicMock())

        mock_get.assert_called_once_with(username__iexact="TeacherUser")


# ===========================================================================
# ClassList tests
# ===========================================================================

@override_settings(
    USE_MAILMAN=False,
    DEFAULT_EMAIL_ADDRESSES={
        'default': 'default@esp.edu',
        'mailman_moderator': 'mod@esp.edu',
    }
)
class ClassListProcessTest(TestCase):
    """Tests for ClassList.process()"""

    def _get_handler(self):
        from esp.dbmail.receivers.classlist import ClassList
        handler = ClassList(MagicMock(), _make_message())
        handler.send = False
        handler.recipients = []
        return handler

    def _make_cls(self, teachers=None, students=None):
        cls = MagicMock()
        cls.emailcode.return_value = "ESP1234"

        program = MagicMock()
        program.director_email = "director@esp.edu"
        program.niceName.return_value = "Splash 2024"
        cls.parent_program = program

        teacher_list = teachers or [_make_user("teacher1", "teacher1@esp.edu")]
        cls.get_teachers.return_value = teacher_list

        section = MagicMock()
        section.students.return_value = students or [_make_user("student1", "student1@esp.edu")]
        cls.sections.all.return_value = [section]

        return cls

    @patch("esp.dbmail.receivers.classlist.ESPUser.email_sendto_address", return_value="director@esp.edu")
    @patch("esp.dbmail.receivers.classlist.ClassSubject.objects.get")
    def test_process_nomailman_teachers(self, mock_get, mock_sendto):
        """user_type='teachers' → teachers added to recipients."""
        mock_get.return_value = self._make_cls()

        handler = self._get_handler()
        handler.process_nomailman(MagicMock(), 1, "teachers")

        self.assertTrue(handler.send)
        self.assertGreater(len(handler.recipients), 0)

    @patch("esp.dbmail.receivers.classlist.ESPUser.email_sendto_address", return_value="director@esp.edu")
    @patch("esp.dbmail.receivers.classlist.ClassSubject.objects.get")
    def test_process_nomailman_students(self, mock_get, mock_sendto):
        """user_type='students' → students added to recipients."""
        mock_get.return_value = self._make_cls()

        handler = self._get_handler()
        handler.process_nomailman(MagicMock(), 1, "students")

        self.assertTrue(handler.send)

    @patch("esp.dbmail.receivers.classlist.ESPUser.email_sendto_address", return_value="director@esp.edu")
    @patch("esp.dbmail.receivers.classlist.ClassSubject.objects.get")
    def test_process_nomailman_class_type(self, mock_get, mock_sendto):
        """user_type='class' → both teachers and students added."""
        mock_get.return_value = self._make_cls()

        handler = self._get_handler()
        handler.process_nomailman(MagicMock(), 1, "class")

        self.assertTrue(handler.send)
        self.assertGreaterEqual(len(handler.recipients), 3)

    @patch("esp.dbmail.receivers.classlist.ClassSubject.objects.get")
    def test_process_nomailman_class_not_found(self, mock_get):
        """DoesNotExist exception → early return, send stays False."""
        from esp.users.models import ESPUser
        mock_get.side_effect = ESPUser.DoesNotExist

        handler = self._get_handler()
        handler.process_nomailman(MagicMock(), 999, "teachers")

        self.assertFalse(handler.send)

    @override_settings(USE_MAILMAN=False)
    @patch("esp.dbmail.receivers.classlist.ESPUser.email_sendto_address", return_value="director@esp.edu")
    @patch("esp.dbmail.receivers.classlist.ClassSubject.objects.get")
    def test_process_routes_to_nomailman(self, mock_get, mock_sendto):
        """process() with USE_MAILMAN=False calls process_nomailman."""
        mock_get.return_value = self._make_cls()

        handler = self._get_handler()
        with patch.object(handler, "process_nomailman") as mock_nm:
            handler.process(MagicMock(), 1, "teachers")
            mock_nm.assert_called_once()

    @override_settings(USE_MAILMAN=True,
                       DEFAULT_EMAIL_ADDRESSES={'mailman_moderator': 'mod@esp.edu'})
    @patch("esp.dbmail.receivers.classlist.ESPUser.email_sendto_address", return_value="director@esp.edu")
    @patch("esp.dbmail.receivers.classlist.ClassSubject.objects.get")
    def test_process_routes_to_mailman(self, mock_get, mock_sendto):
        """process() with USE_MAILMAN=True calls process_mailman."""
        mock_get.return_value = self._make_cls()

        handler = self._get_handler()
        with patch.object(handler, "process_mailman") as mock_mm:
            handler.process(MagicMock(), 1, "teachers")
            mock_mm.assert_called_once()


# ===========================================================================
# SectionList tests
# ===========================================================================

@override_settings(
    USE_MAILMAN=False,
    DEFAULT_EMAIL_ADDRESSES={
        'default': 'default@esp.edu',
        'mailman_moderator': 'mod@esp.edu',
    }
)
class SectionListProcessTest(TestCase):
    """Tests for SectionList.process()"""

    def _get_handler(self):
        from esp.dbmail.receivers.sectionlist import SectionList
        handler = SectionList(MagicMock(), _make_message())
        handler.send = False
        handler.recipients = []
        return handler

    def _make_cls_with_section(self, section_index=1, teachers=None, students=None):
        cls = MagicMock()
        cls.emailcode.return_value = "ESP1234"

        program = MagicMock()
        program.director_email = "director@esp.edu"
        program.niceName.return_value = "Splash 2024"
        cls.parent_program = program

        section = MagicMock()
        section.index.return_value = section_index
        section.emailcode.return_value = "ESP1234s1"
        section.parent_class = cls
        section.parent_class.get_teachers.return_value = (
            teachers or [_make_user("teacher1", "teacher1@esp.edu")]
        )
        section.students.return_value = (
            students or [_make_user("student1", "student1@esp.edu")]
        )
        cls.sections.all.return_value = [section]
        cls.get_teachers.return_value = (
            teachers or [_make_user("teacher1", "teacher1@esp.edu")]
        )
        return cls, section

    @patch("esp.dbmail.receivers.sectionlist.ESPUser.email_sendto_address", return_value="director@esp.edu")
    @patch("esp.dbmail.receivers.sectionlist.ClassSubject.objects.get")
    def test_process_nomailman_teachers(self, mock_get, mock_sendto):
        """user_type='teachers' → teachers in recipients."""
        cls, _ = self._make_cls_with_section()
        mock_get.return_value = cls

        handler = self._get_handler()
        handler.process_nomailman(MagicMock(), 1, 1, "teachers")

        self.assertTrue(handler.send)

    @patch("esp.dbmail.receivers.sectionlist.ESPUser.email_sendto_address", return_value="director@esp.edu")
    @patch("esp.dbmail.receivers.sectionlist.ClassSubject.objects.get")
    def test_process_nomailman_students(self, mock_get, mock_sendto):
        """user_type='students' → students in recipients."""
        cls, _ = self._make_cls_with_section()
        mock_get.return_value = cls

        handler = self._get_handler()
        handler.process_nomailman(MagicMock(), 1, 1, "students")

        self.assertTrue(handler.send)

    @patch("esp.dbmail.receivers.sectionlist.ESPUser.email_sendto_address", return_value="director@esp.edu")
    @patch("esp.dbmail.receivers.sectionlist.ClassSubject.objects.get")
    def test_process_nomailman_class_type(self, mock_get, mock_sendto):
        """user_type='class' → both teachers and students added."""
        cls, _ = self._make_cls_with_section()
        mock_get.return_value = cls

        handler = self._get_handler()
        handler.process_nomailman(MagicMock(), 1, 1, "class")

        self.assertTrue(handler.send)
        self.assertGreaterEqual(len(handler.recipients), 3)

    @patch("esp.dbmail.receivers.sectionlist.ClassSubject.objects.get")
    def test_process_nomailman_section_not_found(self, mock_get):
        """Exception during lookup → early return, send stays False."""
        mock_get.side_effect = Exception("not found")

        handler = self._get_handler()
        handler.process_nomailman(MagicMock(), 999, 1, "teachers")

        self.assertFalse(handler.send)

    @override_settings(USE_MAILMAN=False)
    @patch("esp.dbmail.receivers.sectionlist.ESPUser.email_sendto_address", return_value="director@esp.edu")
    @patch("esp.dbmail.receivers.sectionlist.ClassSubject.objects.get")
    def test_process_routes_to_nomailman(self, mock_get, mock_sendto):
        """process() with USE_MAILMAN=False calls process_nomailman."""
        cls, _ = self._make_cls_with_section()
        mock_get.return_value = cls

        handler = self._get_handler()
        with patch.object(handler, "process_nomailman") as mock_nm:
            handler.process(MagicMock(), 1, 1, "teachers")
            mock_nm.assert_called_once()

    @override_settings(USE_MAILMAN=True,
                       DEFAULT_EMAIL_ADDRESSES={'mailman_moderator': 'mod@esp.edu'})
    @patch("esp.dbmail.receivers.sectionlist.ESPUser.email_sendto_address", return_value="director@esp.edu")
    @patch("esp.dbmail.receivers.sectionlist.ClassSubject.objects.get")
    def test_process_routes_to_mailman(self, mock_get, mock_sendto):
        """process() with USE_MAILMAN=True calls process_mailman."""
        cls, _ = self._make_cls_with_section()
        mock_get.return_value = cls

        handler = self._get_handler()
        with patch.object(handler, "process_mailman") as mock_mm:
            handler.process(MagicMock(), 1, 1, "teachers")
            mock_mm.assert_called_once()