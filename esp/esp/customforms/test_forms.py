"""
Tests for the compound form fields and widgets in esp.customforms.forms.
"""

from collections import OrderedDict

from django.core.exceptions import ValidationError

from esp.customforms.forms import (
    AddressField, AddressWidget, NameField, NameWidget)
from esp.tests.util import CacheFlushTestCase as TestCase


class NameFieldTest(TestCase):

    def field(self, **kwargs):
        return NameField(name='question_5', **{'class': '', **kwargs})

    def test_answer_is_split_into_first_and_last_name(self):
        self.assertEqual(self.field().clean(['Ada', 'Lovelace']),
                         OrderedDict([('question_5_first_name', 'Ada'),
                                      ('question_5_last_name', 'Lovelace')]))

    def test_required_name_must_be_given(self):
        with self.assertRaises(ValidationError):
            self.field().clean(['', ''])

    def test_optional_name_may_be_left_blank(self):
        self.assertEqual(self.field(required=False).clean(['', '']), OrderedDict())

    def test_widget_shows_a_saved_name(self):
        widget = NameWidget()
        self.assertEqual(widget.decompress(OrderedDict([('first', 'Ada'), ('last', 'Lovelace')])),
                         ['Ada', 'Lovelace'])
        self.assertEqual(widget.decompress(None), [None, None])

    def test_hidden_widget_renders_hidden_inputs(self):
        html = self.field().hidden_widget().render('question_5', ['Ada', 'Lovelace'])
        self.assertEqual(html.count('type="hidden"'), 2)
        self.assertIn('value="Ada"', html)
        self.assertIn('value="Lovelace"', html)


class AddressFieldTest(TestCase):

    def field(self, **kwargs):
        return AddressField(name='question_7', **{'class': '', **kwargs})

    def test_answer_is_split_into_address_parts(self):
        self.assertEqual(self.field().clean(['1 Main St', 'Cambridge', 'MA', '02139']),
                         OrderedDict([('question_7_street', '1 Main St'),
                                      ('question_7_city', 'Cambridge'),
                                      ('question_7_state', 'MA'),
                                      ('question_7_zip', '02139')]))

    def test_state_must_be_a_us_state(self):
        with self.assertRaises(ValidationError):
            self.field().clean(['1 Main St', 'Cambridge', 'ZZ', '02139'])

    def test_zip_code_is_limited_to_five_characters(self):
        with self.assertRaises(ValidationError):
            self.field().clean(['1 Main St', 'Cambridge', 'MA', '021390'])

    def test_widget_shows_a_saved_address(self):
        widget = AddressWidget()
        saved = OrderedDict([('street', '1 Main St'), ('city', 'Cambridge'),
                             ('state', 'MA'), ('zip', '02139')])
        self.assertEqual(widget.decompress(saved), ['1 Main St', 'Cambridge', 'MA', '02139'])
        self.assertEqual(widget.decompress(None), [None, None, None, None])

    def test_hidden_widget_renders_hidden_inputs(self):
        html = self.field().hidden_widget().render('question_7', ['1 Main St', 'Cambridge', 'MA', '02139'])
        self.assertEqual(html.count('type="hidden"'), 4)
        self.assertIn('value="Cambridge"', html)

