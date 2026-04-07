import ast
import os
import re

from django.test import TestCase, SimpleTestCase
from django.contrib.auth.models import User
from esp.tagdict import all_global_tags, all_program_tags
from esp.tagdict.models import Tag
from esp.program.tests import ProgramFrameworkTest

# Make test-only tags not raise warnings
all_global_tags['test'] = {
    'is_boolean': False,
    'help_text': '',
    'default': None,
    'category': 'manage',
    'is_setting': True,
}
all_program_tags['test'] = {
    'is_boolean': False,
    'help_text': '',
    'default': None,
    'category': 'manage',
    'is_setting': True,
}
all_global_tags['test_bool'] = {
    'is_boolean': True,
    'help_text': '',
    'default': False,
    'category': 'manage',
    'is_setting': True,
}
all_program_tags['test_bool'] = {
    'is_boolean': True,
    'help_text': '',
    'default': False,
    'category': 'manage',
    'is_setting': True,
}

class TagTest(TestCase):
    def testTagGetSet(self):
        """
        Test that the get and set methods for tags, work.
        Note that at this time, I assume that GenericForeignKeys work
        and are invoked correctly on this class.
        """
        # Dump any existing Tag cache
        Tag._getTag.delete_all()

        self.assertFalse(bool(Tag.getTag("test")), "Retrieved a tag for key 'test' but we haven't set one yet!")
        self.assertFalse(Tag.getTag("test"), "getTag() created a retrievable value for key 'test'!")
        self.assertEqual(Tag.getTag("test", default="the default"), "the default")
        self.assertEqual(Tag.getTag("test", default="the default"), "the default")

        Tag.setTag("test", value="frobbed")
        self.assertEqual(Tag.getTag("test"), "frobbed", "Failed to set tag 'test' to value 'frobbed'!")
        self.assertEqual(Tag.getTag("test"), "frobbed", "Tag was created, but didn't stick!")
        self.assertEqual(Tag.getTag("test", default="the default"), "frobbed", "Defaulting is borked!")
        self.assertEqual(Tag.getTag("test", default="the default"), "frobbed", "Defaulting is borked!")

        Tag.unSetTag("test")

        self.assertFalse(Tag.getTag("test"), "Retrieved a tag for key 'test' but we just deleted it!")
        self.assertFalse(Tag.getTag("test"), "unSetTag() deletes don't appear to be persistent!")
        self.assertEqual(Tag.getTag("test", default="the default"), "the default")
        self.assertEqual(Tag.getTag("test", default="the default"), "the default")

        Tag.setTag("test")
        self.assertTrue(Tag.getTag("test"), "Error:  Setting a tag with an unspecified value must yield a tag whose value evaluates to True!")
        self.assertNotEqual(Tag.getTag("test", default="the default"), "the default", "If the tag is set, even to EMPTY_TAG, we shouldn't return the default.")

    def testTagWithTarget(self):
        '''Test getting and setting of tags with targets.'''
        # Delete any existing tags that might interfere
        Tag.objects.filter(key="test").delete()
        # Dump any existing Tag cache
        Tag._getTag.delete_all()

        user, created = User.objects.get_or_create(username="TestUser123", email="test@example.com", password="")

        self.assertFalse(Tag.getTag("test", user), f"Retrieved a tag for key 'test' target '{user}', but we haven't set one yet!")
        Tag.setTag("test", user, "frobbed again")
        self.assertEqual(Tag.getTag("test", user), "frobbed again")
        Tag.setTag("test", user)
        self.assertEqual(Tag.getTag("test", user), Tag.EMPTY_TAG)
        Tag.unSetTag("test", user)
        self.assertFalse(Tag.getTag("test", user), "unSetTag() didn't work for per-row tags!")

    def testTagCaching(self):
        '''Test that tag values are being cached.'''
        # Delete any existing tags that might interfere
        Tag.objects.filter(key="test").delete()
        # Dump any existing Tag cache
        Tag._getTag.delete_all()

        user1, created = User.objects.get_or_create(username="TestUser1", email="test1@example.com", password="")
        user2, created = User.objects.get_or_create(username="TestUser2", email="test2@example.com", password="")

        for target in [None, user1, user2]:
            self.assertFalse(Tag.getTag("test", target=target))
            with self.assertNumQueries(0):
                self.assertFalse(Tag.getTag("test", target=target))
                self.assertFalse(Tag.getTag("test", target=target))


        Tag.setTag("test", value="tag value")

        for target in [user1, user2]:
            self.assertFalse(Tag.getTag("test", target=target)) #remove after Issue #866 is fixed
            with self.assertNumQueries(0):
                self.assertFalse(Tag.getTag("test", target=target))
                self.assertFalse(Tag.getTag("test", target=target))

        self.assertEqual(Tag.getTag("test"), "tag value")
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test"), "tag value")
            self.assertEqual(Tag.getTag("test"), "tag value")

        for target in [user1, user2]:
            self.assertFalse(Tag.getTag("test", target=target)) #remove after Issue #866 is fixed
            with self.assertNumQueries(0):
                self.assertFalse(Tag.getTag("test", target=target))
                self.assertFalse(Tag.getTag("test", target=target))


        Tag.setTag("test", value="tag value 2")

        for target in [user1, user2]:
            self.assertFalse(Tag.getTag("test", target=target)) #remove after Issue #866 is fixed
            with self.assertNumQueries(0):
                self.assertFalse(Tag.getTag("test", target=target))
                self.assertFalse(Tag.getTag("test", target=target))

        self.assertEqual(Tag.getTag("test"), "tag value 2")
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test"), "tag value 2")
            self.assertEqual(Tag.getTag("test"), "tag value 2")

        for target in [user1, user2]:
            self.assertFalse(Tag.getTag("test", target=target)) #remove after Issue #866 is fixed
            with self.assertNumQueries(0):
                self.assertFalse(Tag.getTag("test", target=target))
                self.assertFalse(Tag.getTag("test", target=target))


        Tag.setTag("test", target=user1, value="tag value user1")

        self.assertFalse(Tag.getTag("test", target=user2)) #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertFalse(Tag.getTag("test", target=user2))
            self.assertFalse(Tag.getTag("test", target=user2))

        self.assertEqual(Tag.getTag("test"), "tag value 2") #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test"), "tag value 2")
            self.assertEqual(Tag.getTag("test"), "tag value 2")

        self.assertEqual(Tag.getTag("test", target=user1), "tag value user1")
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test", target=user1), "tag value user1")
            self.assertEqual(Tag.getTag("test", target=user1), "tag value user1")

        self.assertEqual(Tag.getTag("test"), "tag value 2") #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test"), "tag value 2")
            self.assertEqual(Tag.getTag("test"), "tag value 2")

        self.assertFalse(Tag.getTag("test", target=user2)) #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertFalse(Tag.getTag("test", target=user2))
            self.assertFalse(Tag.getTag("test", target=user2))


        Tag.unSetTag("test")

        self.assertEqual(Tag.getTag("test", target=user1), "tag value user1") #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test", target=user1), "tag value user1")
            self.assertEqual(Tag.getTag("test", target=user1), "tag value user1")

        self.assertFalse(Tag.getTag("test", target=user2)) #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertFalse(Tag.getTag("test", target=user2))
            self.assertFalse(Tag.getTag("test", target=user2))

        self.assertFalse(Tag.getTag("test"))
        with self.assertNumQueries(0):
            self.assertFalse(Tag.getTag("test"))
            self.assertFalse(Tag.getTag("test"))

        self.assertEqual(Tag.getTag("test", target=user1), "tag value user1") #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test", target=user1), "tag value user1")
            self.assertEqual(Tag.getTag("test", target=user1), "tag value user1")

        self.assertFalse(Tag.getTag("test", target=user2)) #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertFalse(Tag.getTag("test", target=user2))
            self.assertFalse(Tag.getTag("test", target=user2))

class ProgramTagTest(ProgramFrameworkTest):
    def testProgramTag(self):
        '''Test the logic of getProgramTag in a bunch of different conditions.'''

        # Delete any existing tags that might interfere
        Tag.objects.filter(key="test").delete()
        # Dump any existing Tag cache
        Tag._getTag.delete_all()

        #Caching is hard, so what the hell, let's run every assertion twice.
        self.assertFalse(Tag.getProgramTag("test", program=self.program))
        self.assertFalse(Tag.getProgramTag("test", program=self.program))
        self.assertFalse(Tag.getProgramTag("test", program=None))
        self.assertFalse(Tag.getProgramTag("test", program=None))
        self.assertEqual(Tag.getProgramTag("test", program=self.program, default="the default"), "the default")
        self.assertEqual(Tag.getProgramTag("test", program=self.program, default="the default"), "the default")
        self.assertEqual(Tag.getProgramTag("test", program=None, default="the default"), "the default")
        self.assertEqual(Tag.getProgramTag("test", program=None, default="the default"), "the default")


        # Set the program-specific tag
        Tag.setTag("test", target=self.program, value="program tag value")

        self.assertFalse(Tag.getProgramTag("test", program=None))
        self.assertFalse(Tag.getProgramTag("test", program=None))
        self.assertEqual(Tag.getProgramTag("test", program=None, default="the default"), "the default")
        self.assertEqual(Tag.getProgramTag("test", program=None, default="the default"), "the default")
        self.assertEqual(Tag.getProgramTag("test", program=self.program), "program tag value")
        self.assertEqual(Tag.getProgramTag("test", program=self.program), "program tag value")
        self.assertEqual(Tag.getProgramTag("test", program=self.program, default="the default"), "program tag value")
        self.assertEqual(Tag.getProgramTag("test", program=self.program, default="the default"), "program tag value")


        # Now set the general tag
        Tag.setTag("test", target=None, value="general tag value")

        self.assertEqual(Tag.getProgramTag("test", program=None), "general tag value")
        self.assertEqual(Tag.getProgramTag("test", program=None), "general tag value")
        self.assertEqual(Tag.getProgramTag("test", program=None, default="the default"), "general tag value")
        self.assertEqual(Tag.getProgramTag("test", program=None, default="the default"), "general tag value")
        self.assertEqual(Tag.getProgramTag("test", program=self.program), "program tag value")
        self.assertEqual(Tag.getProgramTag("test", program=self.program), "program tag value")
        self.assertEqual(Tag.getProgramTag("test", program=self.program, default="the default"), "program tag value")
        self.assertEqual(Tag.getProgramTag("test", program=self.program, default="the default"), "program tag value")


        # Now unset the program-specific tag
        Tag.unSetTag("test", target=self.program)

        self.assertEqual(Tag.getProgramTag("test", program=None), "general tag value")
        self.assertEqual(Tag.getProgramTag("test", program=None), "general tag value")
        self.assertEqual(Tag.getProgramTag("test", program=None, default="the default"), "general tag value")
        self.assertEqual(Tag.getProgramTag("test", program=None, default="the default"), "general tag value")
        self.assertEqual(Tag.getProgramTag("test", program=self.program), "general tag value")
        self.assertEqual(Tag.getProgramTag("test", program=self.program), "general tag value")
        self.assertEqual(Tag.getProgramTag("test", program=self.program, default="the default"), "general tag value")
        self.assertEqual(Tag.getProgramTag("test", program=self.program, default="the default"), "general tag value")

        #just to clean up
        Tag.unSetTag("test", target=None)

        self.assertFalse(Tag.getProgramTag("test", program=self.program))
        self.assertFalse(Tag.getProgramTag("test", program=self.program))
        self.assertFalse(Tag.getProgramTag("test", program=None))
        self.assertFalse(Tag.getProgramTag("test", program=None))
        self.assertEqual(Tag.getProgramTag("test", program=self.program, default="the default"), "the default")
        self.assertEqual(Tag.getProgramTag("test", program=self.program, default="the default"), "the default")
        self.assertEqual(Tag.getProgramTag("test", program=None, default="the default"), "the default")
        self.assertEqual(Tag.getProgramTag("test", program=None, default="the default"), "the default")

    def testBooleanTag(self):
        '''Test the logic of getBooleanTag in a bunch of different conditions, assuming that the underlying getProgramTag works.'''
        # Dump any existing Tag cache
        Tag._getTag.delete_all()

        self.assertFalse(Tag.getBooleanTag("test_bool"))
        self.assertFalse(Tag.getBooleanTag("test_bool"))
        self.assertFalse(Tag.getBooleanTag("test_bool", program=None))
        self.assertFalse(Tag.getBooleanTag("test_bool", program=None))
        self.assertFalse(Tag.getBooleanTag("test_bool", program=self.program))
        self.assertFalse(Tag.getBooleanTag("test_bool", program=self.program))
        for b in [True, False]:
            self.assertEqual(Tag.getBooleanTag("test_bool", default=b), b)
            self.assertEqual(Tag.getBooleanTag("test_bool", default=b), b)
            self.assertEqual(Tag.getBooleanTag("test_bool", program=None, default=b), b)
            self.assertEqual(Tag.getBooleanTag("test_bool", program=None, default=b), b)
            self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program, default=b), b)
            self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program, default=b), b)

        for true_val in [True, "True", "true", "1", 1]:
            Tag.setTag("test_bool", target=self.program, value=true_val)

            self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program), True)
            self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program), True)
            for b in [True, False]:
                self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program, default=b), True)
                self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program, default=b), True)

        for false_val in [False, "False", "false", "0", 0]:
            Tag.setTag("test_bool", target=self.program, value=false_val)

            self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program), False)
            self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program), False)
            for b in [True, False]:
                self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program, default=b), False)
                self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program, default=b), False)


class GetNondefaultProgramTagsTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        # Remove any pre-existing test tags for this program
        Tag.objects.filter(key__in=["test", "test_bool"]).delete()

    def test_no_tags_set(self):
        '''When no program-specific tags exist, result should be empty.'''
        result = Tag.get_nondefault_program_tags(self.program)
        self.assertEqual(result, [])

    def test_program_tag_returned(self):
        '''A tag set for the program with is_setting=True appears in the result.'''
        Tag.setTag("test", target=self.program, value="hello")
        result = Tag.get_nondefault_program_tags(self.program)
        keys = [d['key'] for d in result]
        self.assertIn("test", keys)
        entry = next(d for d in result if d['key'] == "test")
        self.assertEqual(entry['value'], "hello")

    def test_global_tag_not_returned(self):
        '''A global tag (no target) is not included in program tag results.'''
        Tag.setTag("test", target=None, value="global")
        result = Tag.get_nondefault_program_tags(self.program)
        keys = [d['key'] for d in result]
        self.assertNotIn("test", keys)

    def test_non_setting_tag_excluded(self):
        '''A tag with is_setting=False is excluded from the result.'''
        # 'student_lottery_run' is in all_program_tags with is_setting=False
        Tag.setTag("student_lottery_run", target=self.program, value="True")
        result = Tag.get_nondefault_program_tags(self.program)
        keys = [d['key'] for d in result]
        self.assertNotIn("student_lottery_run", keys)

    def test_result_contains_help_text(self):
        '''Each entry in the result includes the help_text from the tag definition.'''
        Tag.setTag("test", target=self.program, value="x")
        result = Tag.get_nondefault_program_tags(self.program)
        entry = next((d for d in result if d['key'] == "test"), None)
        self.assertIsNotNone(entry)
        self.assertIn('help_text', entry)

    def test_tag_at_default_value_excluded(self):
        '''A tag stored in the DB but set to its default value is not shown in the banner.'''
        # 'test_bool' has default=False; setting it to its default should hide it
        all_program_tags['test_bool']['default'] = False
        Tag.setTag("test_bool", target=self.program, value="False")
        result = Tag.get_nondefault_program_tags(self.program)
        keys = [d['key'] for d in result]
        self.assertNotIn("test_bool", keys)

    def test_tag_at_nondefault_value_included(self):
        '''A tag stored with a value different from the default is shown in the banner.'''
        all_program_tags['test_bool']['default'] = False
        Tag.setTag("test_bool", target=self.program, value="True")
        result = Tag.get_nondefault_program_tags(self.program)
        keys = [d['key'] for d in result]
        self.assertIn("test_bool", keys)


class PageSpecificTagBannerTest(ProgramFrameworkTest):
    """
    Tests that _inject_active_program_tags only shows tags that were actually
    consulted (via getProgramTag) while handling the current request, not all
    non-default tags for the program.
    """

    def setUp(self):
        super().setUp()
        Tag.objects.filter(key__in=["test", "test_bool"]).delete()
        Tag._getTag.delete_all()

    def _make_mock_request(self, with_tracking=True):
        """Return a minimal mock request object."""
        from unittest.mock import MagicMock
        req = MagicMock()
        req.path = '/manage/%s/main' % self.program.url
        req.user = self.admins[0]
        if with_tracking:
            req._active_program_tag_keys = set()
            req._active_global_tag_keys = set()
        else:
            # Explicitly set to None so getattr() returns None (not a MagicMock),
            # simulating a request where the middleware never ran.
            req._active_program_tag_keys = None
            req._active_global_tag_keys = None
        return req

    def test_only_accessed_tag_shown(self):
        """Only the tag that getProgramTag was called for appears in the banner."""
        Tag.setTag("test", target=self.program, value="custom")
        Tag.setTag("test_bool", target=self.program, value="True")

        req = self._make_mock_request()
        # Simulate a view that only consults "test"
        req._active_program_tag_keys.add("test")

        from esp.utils.web import _inject_active_program_tags
        context = {}
        _inject_active_program_tags(req, context)

        shown_keys = [t['key'] for t in context.get('active_program_tags', [])]
        self.assertIn("test", shown_keys)
        self.assertNotIn("test_bool", shown_keys)

    def test_no_accessed_tags_shows_nothing(self):
        """If the view accessed no program tags, the banner is empty."""
        Tag.setTag("test", target=self.program, value="custom")

        req = self._make_mock_request()
        # _active_program_tag_keys is empty — no tags consulted

        from esp.utils.web import _inject_active_program_tags
        context = {}
        _inject_active_program_tags(req, context)

        self.assertNotIn('active_program_tags', context)

    def test_fallback_when_tracking_not_initialized(self):
        """Without tracking, all non-default tags are shown as a fallback."""
        Tag.setTag("test", target=self.program, value="custom")

        req = self._make_mock_request(with_tracking=False)

        from esp.utils.web import _inject_active_program_tags
        context = {}
        _inject_active_program_tags(req, context)

        shown_keys = [t['key'] for t in context.get('active_program_tags', [])]
        self.assertIn("test", shown_keys)

    def test_get_program_tag_records_access(self):
        """Calling getProgramTag with a program populates _active_program_tag_keys."""
        from esp.middleware.threadlocalrequest import _threading_local, clear_current_request
        # Simulate middleware having set up the request
        from unittest.mock import MagicMock
        req = MagicMock()
        req._active_program_tag_keys = set()
        req._active_global_tag_keys = set()
        _threading_local.request = req
        try:
            Tag.getProgramTag("test", program=self.program)
            self.assertIn("test", req._active_program_tag_keys)
        finally:
            clear_current_request()


class GetNondefaultGlobalTagsTest(TestCase):
    """Tests for Tag.get_nondefault_global_tags()."""

    def setUp(self):
        Tag.objects.filter(key__in=["test", "test_bool"]).delete()

    def test_no_tags_set(self):
        """When no global tags exist, the result is empty."""
        result = Tag.get_nondefault_global_tags()
        keys = [d['key'] for d in result]
        self.assertNotIn("test", keys)
        self.assertNotIn("test_bool", keys)

    def test_global_tag_returned(self):
        """A global tag (no target) with is_setting=True appears in the result."""
        Tag.setTag("test", target=None, value="hello")
        result = Tag.get_nondefault_global_tags()
        keys = [d['key'] for d in result]
        self.assertIn("test", keys)
        entry = next(d for d in result if d['key'] == "test")
        self.assertEqual(entry['value'], "hello")
        self.assertIn('help_text', entry)

    def test_targeted_tag_not_returned(self):
        """A tag with a non-null target is not included in global results."""
        # Setting a tag with any target row should be excluded by the
        # content_type__isnull / object_id__isnull filter on the query.
        user, _ = User.objects.get_or_create(
            username="GlobalTagTestUser", email="gtt@example.com", password="")
        Tag.setTag("test", target=user, value="targeted")
        result = Tag.get_nondefault_global_tags()
        keys = [d['key'] for d in result]
        self.assertNotIn("test", keys)

    def test_non_setting_tag_excluded(self):
        """A global tag with is_setting=False is excluded from the result."""
        # Pick a real global key registered with is_setting=False, if any.
        # Fall back to flipping our test tag's is_setting for the duration of
        # this test if no such key exists.
        original = all_global_tags['test'].get('is_setting', True)
        all_global_tags['test']['is_setting'] = False
        try:
            Tag.setTag("test", target=None, value="something")
            result = Tag.get_nondefault_global_tags()
            keys = [d['key'] for d in result]
            self.assertNotIn("test", keys)
        finally:
            all_global_tags['test']['is_setting'] = original

    def test_tag_at_default_value_excluded(self):
        """A global tag stored at its default value is hidden from the banner."""
        all_global_tags['test_bool']['default'] = False
        Tag.setTag("test_bool", target=None, value="False")
        result = Tag.get_nondefault_global_tags()
        keys = [d['key'] for d in result]
        self.assertNotIn("test_bool", keys)

    def test_tag_at_nondefault_value_included(self):
        """A global tag stored with a non-default value is shown."""
        all_global_tags['test_bool']['default'] = False
        Tag.setTag("test_bool", target=None, value="True")
        result = Tag.get_nondefault_global_tags()
        keys = [d['key'] for d in result]
        self.assertIn("test_bool", keys)


class PageSpecificGlobalTagBannerTest(ProgramFrameworkTest):
    """
    Tests that _inject_active_program_tags also injects ``active_global_tags``
    based on which global tag keys were consulted while handling the request,
    in addition to the existing program-tag behavior.
    """

    def setUp(self):
        super().setUp()
        Tag.objects.filter(key__in=["test", "test_bool"]).delete()
        Tag._getTag.delete_all()

    def _make_mock_request(self, with_tracking=True):
        from unittest.mock import MagicMock
        req = MagicMock()
        req.path = '/manage/%s/main' % self.program.url
        req.user = self.admins[0]
        if with_tracking:
            req._active_program_tag_keys = set()
            req._active_global_tag_keys = set()
        else:
            req._active_program_tag_keys = None
            req._active_global_tag_keys = None
        return req

    def test_only_accessed_global_tag_shown(self):
        """Only the global tag the view actually consulted appears in the banner."""
        Tag.setTag("test", target=None, value="global custom")
        Tag.setTag("test_bool", target=None, value="True")

        req = self._make_mock_request()
        # Simulate a view that only consults the global "test" tag.
        req._active_global_tag_keys.add("test")

        from esp.utils.web import _inject_active_program_tags
        context = {}
        _inject_active_program_tags(req, context)

        shown_keys = [t['key'] for t in context.get('active_global_tags', [])]
        self.assertIn("test", shown_keys)
        self.assertNotIn("test_bool", shown_keys)
        # Settings link should point to the global tag management page.
        self.assertEqual(context.get('active_global_tags_url'), '/manage/tags/')

    def test_no_accessed_global_tags_shows_nothing(self):
        """If the view accessed no global tags, the global banner is empty."""
        Tag.setTag("test", target=None, value="global custom")

        req = self._make_mock_request()
        # _active_global_tag_keys stays empty.

        from esp.utils.web import _inject_active_program_tags
        context = {}
        _inject_active_program_tags(req, context)

        self.assertNotIn('active_global_tags', context)

    def test_fallback_when_tracking_not_initialized(self):
        """Without tracking, all non-default global tags are shown as a fallback."""
        Tag.setTag("test", target=None, value="global custom")

        req = self._make_mock_request(with_tracking=False)

        from esp.utils.web import _inject_active_program_tags
        context = {}
        _inject_active_program_tags(req, context)

        shown_keys = [t['key'] for t in context.get('active_global_tags', [])]
        self.assertIn("test", shown_keys)

    def test_get_tag_records_global_access(self):
        """Calling Tag.getTag (no target) populates _active_global_tag_keys."""
        from esp.middleware.threadlocalrequest import _threading_local, clear_current_request
        from unittest.mock import MagicMock
        req = MagicMock()
        req._active_program_tag_keys = set()
        req._active_global_tag_keys = set()
        _threading_local.request = req
        try:
            Tag.getTag("test")
            self.assertIn("test", req._active_global_tag_keys)
        finally:
            clear_current_request()

    def test_get_program_tag_fallback_records_global_access(self):
        """
        getProgramTag falling back to the global lookup (because no
        program-specific value exists) also records the key into
        _active_global_tag_keys, so global non-default values can show up in
        the banner even when accessed through getProgramTag.
        """
        from esp.middleware.threadlocalrequest import _threading_local, clear_current_request
        from unittest.mock import MagicMock
        req = MagicMock()
        req._active_program_tag_keys = set()
        req._active_global_tag_keys = set()
        _threading_local.request = req
        try:
            # No program-specific tag; getProgramTag will fall through to the
            # global lookup branch and should record the key as a global hit.
            Tag.getProgramTag("test", program=self.program)
            self.assertIn("test", req._active_program_tag_keys)
            self.assertIn("test", req._active_global_tag_keys)
        finally:
            clear_current_request()



class TagRegistrationTest(SimpleTestCase):
    """
    Statically scan the codebase for Tag.getTag(), Tag.getProgramTag(), and
    Tag.getBooleanTag() calls and verify that every string-literal tag key
    is registered in all_global_tags or all_program_tags.
    """

    # Paths (relative to the esp/ root) to skip when scanning, because they
    # use test-only tags that are registered in the test module itself.
    _skip_paths = [
        os.path.join('esp', 'tagdict', 'tests.py'),
    ]

    # The set of all valid tag names from tagdict/__init__.py
    _all_known_tags = (set(all_global_tags.keys()) | set(all_program_tags.keys())) - {
        'test',
        'test_bool',
    }

    # ---- helpers for scanning Python files ----

    class _TagCallVisitor(ast.NodeVisitor):
        """AST visitor that collects string-literal first arguments to
        Tag.getTag(), Tag.getProgramTag(), and Tag.getBooleanTag()."""

        TARGET_METHODS = {'getTag', 'getProgramTag', 'getBooleanTag'}

        def __init__(self):
            self.found = []  # list of (tag_key, lineno)

        def visit_Call(self, node):
            if self._is_tag_call(node) and node.args:
                first_arg = node.args[0]
                tag_key = None
                if isinstance(first_arg, ast.Str):  # Python 3.7 compat
                    tag_key = first_arg.s
                elif isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):  # Python 3.8+ compat
                    tag_key = first_arg.value
                if tag_key is not None:
                    self.found.append((tag_key, node.lineno))
            self.generic_visit(node)

        @classmethod
        def _is_tag_call(cls, node):
            """Return True if *node* looks like Tag.<method>(...)."""
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in cls.TARGET_METHODS:
                if isinstance(func.value, ast.Name) and func.value.id == 'Tag':
                    return True
            return False

    @classmethod
    def _scan_python_file(cls, filepath):
        """Return [(tag_key, lineno), ...] found in *filepath*."""
        with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
            source = fh.read()
        try:
            tree = ast.parse(source, filename=filepath)
        except SyntaxError:
            return []
        visitor = cls._TagCallVisitor()
        visitor.visit(tree)
        return visitor.found

    # ---- helpers for scanning Django template files ----

    # Matches filter syntax:  "tag_name"|getBooleanTag, "tag_name"|getProgramTag, or "tag_name"|getTag
    _TEMPLATE_FILTER_RE = re.compile(
        r"""["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\|\s*(?:getBooleanTag|getProgramTag|getTag)"""
    )

    # Matches tag syntax:  {% getProgramTag "tag_name" ... %}, {% getBooleanTag "tag_name" ... %}, or {% getTag "tag_name" ... %}
    _TEMPLATE_TAG_RE = re.compile(
        r"""\{%\s*(?:getProgramTag|getBooleanTag|getTag)\s+["']([A-Za-z_][A-Za-z0-9_]*)["']"""
    )

    @classmethod
    def _scan_template_file(cls, filepath):
        """Return [(tag_key, lineno), ...] found in *filepath*."""
        results = []
        with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
            for lineno, line in enumerate(fh, start=1):
                for m in cls._TEMPLATE_FILTER_RE.finditer(line):
                    results.append((m.group(1), lineno))
                for m in cls._TEMPLATE_TAG_RE.finditer(line):
                    results.append((m.group(1), lineno))
        return results

    # ---- the actual test ----

    def test_all_tags_are_registered(self):
        """Every tag key used in the codebase must exist in tagdict."""
        esp_root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        )))  # …/esp

        undefined_tags = []  # [(filepath, lineno, tag_key), ...]

        for dirpath, _dirnames, filenames in os.walk(esp_root):
            for fname in filenames:
                filepath = os.path.join(dirpath, fname)
                relpath = os.path.relpath(filepath, esp_root)

                # Skip files in the exclusion list
                if relpath in self._skip_paths:
                    continue

                if fname.endswith('.py'):
                    for tag_key, lineno in self._scan_python_file(filepath):
                        if tag_key not in self._all_known_tags:
                            undefined_tags.append((relpath, lineno, tag_key))

                elif fname.endswith('.html'):
                    for tag_key, lineno in self._scan_template_file(filepath):
                        if tag_key not in self._all_known_tags:
                            undefined_tags.append((relpath, lineno, tag_key))

        if undefined_tags:
            tag_list = "\n".join(
                "  %s (line %d): %s" % (fp, ln, key)
                for fp, ln, key in sorted(undefined_tags)
            )
            self.fail(
                "The following tag(s) are used in code but not defined in "
                "esp.tagdict.__init__ (all_global_tags or all_program_tags):\n"
                + tag_list
            )
