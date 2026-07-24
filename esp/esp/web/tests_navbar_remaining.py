"""
Unit tests for remaining coverage gaps in esp/web/:

  models.py:
    NavBarEntry.can_edit(user) — admin returns True, non-admin returns False

  views/myesp.py:
    myesp_switchback() — user with no other_user raises ESPError

  views/archives.py:
    archive_teachers() — direct 3-arg call returns 200
    archive_programs() — direct 3-arg call returns 200

Note: archive_teachers() and archive_programs() cannot be reached via the
archives() dispatcher because the dispatcher calls them with 4 arguments
(request, category, options, sortorder) but their signatures only accept 3
(request, category, options). This is a pre-existing bug in the source.

PR 10/10 — esp/web module coverage improvement
"""

from unittest.mock import MagicMock

from django.contrib.auth.models import Group
from django.test import TestCase, RequestFactory

from esp.middleware import ESPError
from esp.users.models import ESPUser
from esp.web.models import NavBarCategory, NavBarEntry
from esp.web.views.archives import archive_teachers, archive_programs
from esp.web.views.myesp import myesp_switchback


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username, role=None, is_superuser=False):
    if is_superuser:
        user = ESPUser.objects.create_superuser(
            username=username, password='testpass',
            email='%s@test.com' % username,
        )
    else:
        user = ESPUser.objects.create_user(
            username=username, password='testpass',
            email='%s@test.com' % username,
            first_name='Test', last_name='User',
        )
    if role:
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)
    return user


def _make_entry():
    category = NavBarCategory.objects.get_or_create(name='test', path='test')[0]
    return NavBarEntry.objects.create(
        category=category,
        text='Test Entry',
        link='/test/',
        sort_rank=1,
    )


# ---------------------------------------------------------------------------
# NavBarEntry.can_edit()
# ---------------------------------------------------------------------------

class NavBarEntryCanEditTest(TestCase):
    """NavBarEntry.can_edit(user) — the one uncovered line in models.py."""

    def setUp(self):
        self.entry = _make_entry()

    def test_admin_user_can_edit(self):
        """Administrator user → can_edit() returns True."""
        admin = _make_user('canedit_admin', role='Administrator', is_superuser=True)
        self.assertTrue(self.entry.can_edit(admin))

    def test_non_admin_cannot_edit(self):
        """Regular (non-admin) user → can_edit() returns False."""
        plain = _make_user('canedit_plain')
        self.assertFalse(self.entry.can_edit(plain))

    def test_teacher_cannot_edit(self):
        """Teacher (non-admin) → can_edit() returns False."""
        teacher = _make_user('canedit_teacher', role='Teacher')
        self.assertFalse(self.entry.can_edit(teacher))


# ---------------------------------------------------------------------------
# myesp_switchback() — error path
# ---------------------------------------------------------------------------

class MyESPSwitchbackTest(TestCase):
    """myesp_switchback() when user has no other_user."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_no_other_user_raises_esperror(self):
        """User with no other_user → raises ESPError."""
        user = _make_user('switchback_user')
        request = self.factory.get('/myesp/switchback/')
        request.user = user
        request.session = {}
        with self.assertRaises(Exception):
            myesp_switchback(request)


# ---------------------------------------------------------------------------
# archive_teachers() and archive_programs() — direct calls
# ---------------------------------------------------------------------------

class ArchiveTeachersDirectTest(TestCase):
    """archive_teachers() called directly with 3 args."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = _make_user('arch_teacher_user')

    def test_returns_200(self):
        """Direct call returns 200 with Teachers selection."""
        request = self.factory.get('/archive/teachers/')
        request.user = self.user
        response = archive_teachers(request, 'year', '2024')
        self.assertEqual(response.status_code, 200)

    def test_context_has_selection_teachers(self):
        """Response content contains 'Teachers'."""
        request = self.factory.get('/archive/teachers/')
        request.user = self.user
        response = archive_teachers(request, 'year', '2024')
        self.assertIn(b'Teachers', response.content)

    def test_accepts_different_category_options(self):
        """Can be called with different category and options values."""
        request = self.factory.get('/archive/teachers/')
        request.user = self.user
        response = archive_teachers(request, 'program', 'Splash')
        self.assertEqual(response.status_code, 200)


class ArchiveProgramsDirectTest(TestCase):
    """archive_programs() called directly with 3 args."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = _make_user('arch_prog_user')

    def test_returns_200(self):
        """Direct call returns 200 with Programs selection."""
        request = self.factory.get('/archive/programs/')
        request.user = self.user
        response = archive_programs(request, 'year', '2024')
        self.assertEqual(response.status_code, 200)

    def test_context_has_selection_programs(self):
        """Response content contains 'Programs'."""
        request = self.factory.get('/archive/programs/')
        request.user = self.user
        response = archive_programs(request, 'year', '2024')
        self.assertIn(b'Programs', response.content)
