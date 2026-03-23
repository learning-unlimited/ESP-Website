import json
from django.test import TestCase
from esp.utils.widgets import (
    ClassAttrMergingSelect, NullCheckboxSelect, DummyWidget,
    BlankSelectWidget, NullRadioSelect, ContactFieldsWidget
)

class UtilsWidgetsTests(TestCase):
    
    def test_class_attr_merging_select(self):
        """Test that extra 'class' attributes are merged, not overwritten."""
        widget = ClassAttrMergingSelect()
        base_attrs = {'class': 'base-class', 'id': 'my-id'}
        extra_attrs = {'class': 'extra-class', 'name': 'test-name'}
        
        merged = widget.build_attrs(base_attrs, extra_attrs)
        
        self.assertEqual(merged['class'], 'base-class extra-class')
        self.assertEqual(merged['id'], 'my-id')
        self.assertEqual(merged['name'], 'test-name')

    def test_null_checkbox_select_logic(self):
        """Test that 'on', 'true', and 'false' strings are parsed to booleans."""
        widget = NullCheckboxSelect()
        
        self.assertTrue(widget.value_from_datadict({'my_field': 'on'}, {}, 'my_field'))
        self.assertTrue(widget.value_from_datadict({'my_field': 'true'}, {}, 'my_field'))
        self.assertFalse(widget.value_from_datadict({'my_field': 'false'}, {}, 'my_field'))
        self.assertFalse(widget.value_from_datadict({}, {}, 'my_field'))

    def test_dummy_widget(self):
        """Test that DummyWidget always returns True for data."""
        widget = DummyWidget()
        self.assertTrue(widget.value_from_datadict({'random_key': 'data'}, {}, 'random_key'))

    def test_blank_select_widget_init(self):
        """Test that BlankSelectWidget initializes with correct blank choices."""
        widget = BlankSelectWidget(blank_choice=('empty_val', 'Empty Label'))
        self.assertEqual(widget.blank_value, 'empty_val')
        self.assertEqual(widget.blank_label, 'Empty Label')
        
        default_widget = BlankSelectWidget()
        self.assertEqual(default_widget.blank_value, '')
        self.assertEqual(default_widget.blank_label, '')

    def test_null_radio_select_init(self):
        """Test that NullRadioSelect forces choices to Yes/No booleans."""
        widget = NullRadioSelect()
        self.assertEqual(list(widget.choices), [(True, 'Yes'), (False, 'No')])

    def test_contact_fields_widget_datadict(self):
        """Test JSON parsing in ContactFieldsWidget."""
        widget = ContactFieldsWidget()
        test_json = '{"icon": "envelope", "link": "/contact", "text": "email us"}'
        test_data = {'contact_data': test_json}
        
        result = widget.value_from_datadict(test_data, {}, 'contact_data')
        self.assertEqual(result, {"icon": "envelope", "link": "/contact", "text": "email us"})