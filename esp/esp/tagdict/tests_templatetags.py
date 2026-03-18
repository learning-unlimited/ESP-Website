from django.test import TestCase
from django.template import Context, Template
from esp.tagdict.models import Tag
from esp.tagdict import all_global_tags, all_program_tags

_TEST_PROGRAM_TAG_KEY = '_unit_test_tagdict_program_tag'
_TEST_BOOL_TAG_KEY = '_unit_test_tagdict_bool_tag'


class TagdictTemplateTagBase(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Register test tags to avoid warnings
        cls._saved_all_global_tags = {}
        cls._saved_all_program_tags = {}
        test_tag_configs = {
            _TEST_PROGRAM_TAG_KEY: {
                'is_boolean': False,
                'help_text': '',
                'default': None,
                'category': 'manage',
                'is_setting': True,
            },
            _TEST_BOOL_TAG_KEY: {
                'is_boolean': True,
                'help_text': '',
                'default': False,
                'category': 'manage',
                'is_setting': True,
            },
        }
        for key, config in test_tag_configs.items():
            cls._saved_all_global_tags[key] = all_global_tags.get(key, None)
            cls._saved_all_program_tags[key] = all_program_tags.get(key, None)
            all_global_tags[key] = config
            all_program_tags[key] = config

    @classmethod
    def tearDownClass(cls):
        try:
            for key, prev in cls._saved_all_global_tags.items():
                if prev is None:
                    all_global_tags.pop(key, None)
                else:
                    all_global_tags[key] = prev
            for key, prev in cls._saved_all_program_tags.items():
                if prev is None:
                    all_program_tags.pop(key, None)
                else:
                    all_program_tags[key] = prev
        finally:
            super().tearDownClass()

    def render(self, template_str, context=None):
        t = Template('{% load tagdict %}' + template_str)
        return t.render(Context(context or {}))


class GetProgramTagTemplateTagTest(TagdictTemplateTagBase):

    def setUp(self):
        Tag._getTag.delete_all()
        Tag.objects.filter(key=_TEST_PROGRAM_TAG_KEY).delete()

    def test_returns_value_when_tag_exists(self):
        Tag.setTag(_TEST_PROGRAM_TAG_KEY, value='hello')
        result = self.render('{% getProgramTag "' + _TEST_PROGRAM_TAG_KEY + '" %}')
        self.assertEqual(result, 'hello')

    def test_returns_none_when_tag_missing(self):
        result = self.render('{% getProgramTag "' + _TEST_PROGRAM_TAG_KEY + '" %}')
        self.assertEqual(result, 'None')

    def test_returns_default_when_tag_missing(self):
        result = self.render('{% getProgramTag "' + _TEST_PROGRAM_TAG_KEY + '" None "mydefault" %}')
        self.assertEqual(result, 'mydefault')


class GetBooleanTagTemplateTagTest(TagdictTemplateTagBase):

    def setUp(self):
        Tag._getTag.delete_all()
        Tag.objects.filter(key=_TEST_BOOL_TAG_KEY).delete()

    def test_returns_false_when_tag_missing(self):
        result = self.render('{% getBooleanTag "' + _TEST_BOOL_TAG_KEY + '" %}')
        self.assertEqual(result, 'false')

    def test_returns_true_when_tag_set_to_true(self):
        Tag.setTag(_TEST_BOOL_TAG_KEY, value='true')
        result = self.render('{% getBooleanTag "' + _TEST_BOOL_TAG_KEY + '" %}')
        self.assertEqual(result, 'true')

    def test_returns_false_when_tag_set_to_false(self):
        Tag.setTag(_TEST_BOOL_TAG_KEY, value='false')
        result = self.render('{% getBooleanTag "' + _TEST_BOOL_TAG_KEY + '" %}')
        self.assertEqual(result, 'false')