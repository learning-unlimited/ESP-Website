"""
Tests for esp.miniblog.models
Source: esp/esp/miniblog/models.py

Tests AnnouncementLink, Entry, and Comment models.
"""
import datetime

from django.contrib.auth.models import Group

from esp.miniblog.models import AnnouncementLink, Comment, Entry
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class AnnouncementLinkTest(TestCase):
    def setUp(self):
        super().setUp()
        self.link = AnnouncementLink.objects.create(
            title='Test Announcement',
            category='news',
            href='https://example.com/test',
        )

    def test_str(self):
        result = str(self.link)
        self.assertIn('Test Announcement', result)
        self.assertIn('https://example.com/test', result)

    def test_get_absolute_url(self):
        self.assertEqual(self.link.get_absolute_url(), 'https://example.com/test')

    def test_makeUrl_alias(self):
        self.assertEqual(self.link.makeUrl(), self.link.get_absolute_url())

    def test_makeTitle(self):
        self.assertEqual(self.link.makeTitle(), 'Test Announcement')

    def test_content(self):
        result = self.link.content()
        self.assertIn('Click Here', result)
        self.assertIn('https://example.com/test', result)

    def test_html(self):
        result = self.link.html()
        self.assertIn('<a href=', result)
        self.assertIn('Test Announcement', result)


class EntryTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.entry = Entry.objects.create(
            title='Test Blog Entry',
            slug='test-entry',
            content='This is **bold** text.',
        )

    def test_str_with_slug(self):
        self.assertEqual(str(self.entry), 'test-entry')

    def test_str_without_slug(self):
        self.entry.slug = ''
        self.assertEqual(str(self.entry), 'Test Blog Entry')

    def test_html_renders_markdown(self):
        html = self.entry.html()
        self.assertIn('<strong>bold</strong>', html)

    def test_makeTitle(self):
        self.assertEqual(self.entry.makeTitle(), 'Test Blog Entry')

    def test_timestamp_auto_set(self):
        self.assertIsNotNone(self.entry.timestamp)

    def test_ordering_newest_first(self):
        older = Entry.objects.create(
            title='Older',
            slug='older',
            content='Old content',
        )
        # Force older timestamp
        Entry.objects.filter(pk=older.pk).update(
            timestamp=datetime.datetime(2020, 1, 1),
        )
        entries = list(Entry.objects.all())
        self.assertEqual(entries[0].pk, self.entry.pk)


class CommentTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.user = ESPUser.objects.create_user(
            username='commenter', password='password',
        )
        self.entry = Entry.objects.create(
            title='Commented Entry',
            slug='commented',
            content='Content here.',
        )
        self.comment = Comment.objects.create(
            author=self.user,
            entry=self.entry,
            subject='Nice post',
            content='Great work!',
        )

    def test_str(self):
        result = str(self.comment)
        self.assertIn('commenter', result)
        self.assertIn('commented', result)

    def test_ordering_newest_first(self):
        comment2 = Comment.objects.create(
            author=self.user,
            entry=self.entry,
            subject='Another',
            content='More thoughts.',
        )
        comments = list(Comment.objects.filter(entry=self.entry))
        self.assertEqual(comments[0].pk, comment2.pk)
