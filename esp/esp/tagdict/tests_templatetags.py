from django.test import TestCase
from django.template import Context, Template
from esp.tagdict.models import Tag
from esp.tagdict import all_global_tags, all_program_tags

# Register test tags to avoid warnings
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

class GetProgramTagTemplateTagTest(TestCase):

    def setUp(self):
        Tag._getTag.delete_all()
        Tag.objects.filter(key='test').delete()

    def render(self, template_str, context=None):
        t = Template('{% load tagdict %}' + template_str)
        return t.render(Context(context or {}))

    def test_returns_value_when_tag_exists(self):
        Tag.setTag('test', value='hello')
        result = self.render('{% getProgramTag "test" %}')
        self.assertEqual(result, 'hello')

    def test_returns_none_string_when_tag_missing(self):
        result = self.render('{% getProgramTag "test" %}')
        self.assertEqual(result, 'None')

    def test_returns_default_when_tag_missing(self):
        result = self.render('{% getProgramTag "test" None "mydefault" %}')
        self.assertEqual(result, 'mydefault')


class GetBooleanTagTemplateTagTest(TestCase):

    def setUp(self):
        Tag._getTag.delete_all()
        Tag.objects.filter(key='test_bool').delete()

    def render(self, template_str, context=None):
        t = Template('{% load tagdict %}' + template_str)
        return t.render(Context(context or {}))

    def test_returns_false_when_tag_missing(self):
        result = self.render('{% getBooleanTag "test_bool" %}')
        self.assertEqual(result, 'false')

    def test_returns_true_when_tag_set_to_true(self):
        Tag.setTag('test_bool', value='true')
        result = self.render('{% getBooleanTag "test_bool" %}')
        self.assertEqual(result, 'true')

    def test_returns_false_when_tag_set_to_false(self):
        Tag.setTag('test_bool', value='false')
        result = self.render('{% getBooleanTag "test_bool" %}')
        self.assertEqual(result, 'false')
