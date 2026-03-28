import ast
import os
import re

from django.test import TestCase, SimpleTestCase
from django.contrib.auth.models import User
from esp.tagdict import all_global_tags, all_program_tags
from esp.tagdict.models import Tag
from esp.tagdict.validators import (
    ALL_HIDE_FIELDS_TAG_KEYS,
    get_valid_field_names_for_tag,
    validate_hide_fields_value,
)
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


class HideFieldsValidatorTest(SimpleTestCase):
    """Tests for the hide_fields tag validation utilities."""

    def test_non_hide_fields_tag_returns_none(self):
        """Tags that are not hide_fields tags should return None."""
        self.assertIsNone(validate_hide_fields_value('some_other_tag', 'value'))
        self.assertIsNone(get_valid_field_names_for_tag('some_other_tag'))

    def test_all_hide_fields_tags_return_valid_fields(self):
        """Every recognised hide_fields tag key should return a non-empty set of valid field names."""
        for tag_key in ALL_HIDE_FIELDS_TAG_KEYS:
            valid_fields = get_valid_field_names_for_tag(tag_key)
            self.assertIsNotNone(valid_fields, f"{tag_key} should be recognised")
            self.assertIsInstance(valid_fields, set)
            self.assertTrue(len(valid_fields) > 0, f"{tag_key} should have at least one valid field")

    def test_empty_value_is_valid(self):
        """An empty tag value should be accepted without errors."""
        for tag_key in ALL_HIDE_FIELDS_TAG_KEYS:
            valid, invalid, _valid_set = validate_hide_fields_value(tag_key, '')
            self.assertEqual(valid, [])
            self.assertEqual(invalid, [])

    def test_whitespace_only_value_is_valid(self):
        """A whitespace-only tag value should be accepted without errors."""
        for tag_key in ALL_HIDE_FIELDS_TAG_KEYS:
            valid, invalid, _valid_set = validate_hide_fields_value(tag_key, '   ')
            self.assertEqual(valid, [])
            self.assertEqual(invalid, [])

    def test_valid_field_names_are_accepted(self):
        """Known field names should appear in the valid list."""
        for tag_key in ALL_HIDE_FIELDS_TAG_KEYS:
            all_fields = get_valid_field_names_for_tag(tag_key)
            # Pick one field to test
            sample_field = sorted(all_fields)[0]
            valid, invalid, _valid_set = validate_hide_fields_value(tag_key, sample_field)
            self.assertIn(sample_field, valid)
            self.assertEqual(invalid, [])

    def test_invalid_field_names_are_rejected(self):
        """Non-existent field names should appear in the invalid list."""
        for tag_key in ALL_HIDE_FIELDS_TAG_KEYS:
            valid, invalid, _valid_set = validate_hide_fields_value(tag_key, 'not_a_real_field')
            self.assertEqual(valid, [])
            self.assertIn('not_a_real_field', invalid)

    def test_mixed_valid_and_invalid_fields(self):
        """A mix of valid and invalid field names should be split correctly."""
        for tag_key in ALL_HIDE_FIELDS_TAG_KEYS:
            all_fields = get_valid_field_names_for_tag(tag_key)
            sample_field = sorted(all_fields)[0]
            value = '%s,not_a_real_field' % sample_field
            valid, invalid, _valid_set = validate_hide_fields_value(tag_key, value)
            self.assertIn(sample_field, valid)
            self.assertIn('not_a_real_field', invalid)

    def test_whitespace_around_field_names_is_stripped(self):
        """Leading/trailing whitespace around field names should be ignored."""
        for tag_key in ALL_HIDE_FIELDS_TAG_KEYS:
            all_fields = get_valid_field_names_for_tag(tag_key)
            sample_field = sorted(all_fields)[0]
            value = '  %s , not_a_real_field  ' % sample_field
            valid, invalid, _valid_set = validate_hide_fields_value(tag_key, value)
            self.assertIn(sample_field, valid)
            self.assertIn('not_a_real_field', invalid)

    def test_trailing_comma_does_not_create_empty_entry(self):
        """A trailing comma should not produce an empty invalid field name."""
        for tag_key in ALL_HIDE_FIELDS_TAG_KEYS:
            all_fields = get_valid_field_names_for_tag(tag_key)
            sample_field = sorted(all_fields)[0]
            valid, invalid, _valid_set = validate_hide_fields_value(tag_key, sample_field + ',')
            self.assertIn(sample_field, valid)
            self.assertEqual(invalid, [])

    def test_case_insensitivity(self):
        """Field name matching should be case-insensitive (values are lowered)."""
        for tag_key in ALL_HIDE_FIELDS_TAG_KEYS:
            all_fields = get_valid_field_names_for_tag(tag_key)
            sample_field = sorted(all_fields)[0]
            # All declared field names are already lowercase in Django,
            # so an uppercased version should still resolve correctly
            # after the value is lowered by the validator.
            valid, invalid, _valid_set = validate_hide_fields_value(tag_key, sample_field.upper())
            self.assertIn(sample_field, valid)
            self.assertEqual(invalid, [])


class TagAdminFormValidationTest(TestCase):
    """Tests for the TagAdminForm used in the Django admin."""

    def test_admin_form_rejects_invalid_hide_fields(self):
        """Submitting an invalid field name via the admin form should fail validation."""
        from esp.tagdict.admin import TagAdminForm

        form = TagAdminForm(data={
            'key': 'student_profile_hide_fields',
            'value': 'not_a_real_field',
        })
        self.assertFalse(form.is_valid())
        # The error should mention the invalid field name
        error_text = str(form.errors)
        self.assertIn('not_a_real_field', error_text)

    def test_admin_form_accepts_valid_hide_fields(self):
        """Submitting valid field names via the admin form should pass validation."""
        from esp.tagdict.admin import TagAdminForm
        from esp.users.forms.user_profile import StudentProfileForm

        sample_field = sorted(StudentProfileForm.declared_fields.keys())[0]
        form = TagAdminForm(data={
            'key': 'student_profile_hide_fields',
            'value': sample_field,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_admin_form_accepts_empty_hide_fields(self):
        """An empty value for a hide_fields tag should be accepted."""
        from esp.tagdict.admin import TagAdminForm

        form = TagAdminForm(data={
            'key': 'student_profile_hide_fields',
            'value': '',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_admin_form_accepts_non_hide_fields_tags(self):
        """Non-hide-fields tags should not be affected by the validation."""
        from esp.tagdict.admin import TagAdminForm

        form = TagAdminForm(data={
            'key': 'some_random_tag',
            'value': 'any_value',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_admin_form_error_lists_valid_options(self):
        """The validation error should list the valid field names."""
        from esp.tagdict.admin import TagAdminForm
        from esp.users.forms.user_profile import TeacherProfileForm

        form = TagAdminForm(data={
            'key': 'teacher_profile_hide_fields',
            'value': 'bogus_field',
        })
        self.assertFalse(form.is_valid())
        error_text = str(form.errors)
        self.assertIn('bogus_field', error_text)
        # Should mention at least one valid field
        any_valid = sorted(TeacherProfileForm.declared_fields.keys())[0]
        self.assertIn(any_valid, error_text)
