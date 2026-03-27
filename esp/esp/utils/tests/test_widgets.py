import json
import datetime
from django.test import TestCase
from esp.utils.widgets import (
    ClassAttrMergingSelect, NullCheckboxSelect, DummyWidget,
    BlankSelectWidget, NullRadioSelect, ContactFieldsWidget,
    DateTimeWidget, SplitDateWidget, NavStructureWidget 
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

    def test_datetime_widget_parsing(self):
        """Test parsing of date strings into datetime objects."""
        widget = DateTimeWidget()
        # Using a standard format Django's DateTimeWidget expects
        data = {'event_date': '2026-03-27 09:00:00'}
        value = widget.value_from_datadict(data, {}, 'event_date')
        self.assertIsNotNone(value)

    def test_split_date_logic(self):
        """Test breaking a date into [Month, Day, Year]."""
        widget = SplitDateWidget()
        test_date = datetime.date(2026, 3, 27)
        # Verify it decompresses to the format expected by the widget
        self.assertEqual(widget.decompress(test_date), [3, 27, 2026])

    def test_nav_structure_json(self):
        """Test JSON encoding/decoding for navigation structures."""
        widget = NavStructureWidget()
        test_data = [{"header": "Home", "links": []}]
        result = widget.value_from_datadict({'nav': json.dumps(test_data)}, {}, 'nav')
        self.assertEqual(result[0]['header'], "Home")  