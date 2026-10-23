"""Tests for esp.program.modules.handlers.donationmodule"""
from django.test import SimpleTestCase, TestCase
from esp.program.modules.handlers.donationmodule import DonationModule, DonationForm
from esp.program.models import Program, ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.tagdict.models import Tag

class DonationFormTest(SimpleTestCase):
    """Tests for DonationForm validation logic."""

    def test_donation_form_preset_amount(self):
        """Test form validates successfully with a preset amount."""
        settings = {
            'donation_text': 'Support us',
            'donation_options': [10, 20, 50],
        }
        form = DonationModule.get_form(settings=settings, form_data={'amount_donation': '20'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.amount, '20')

    def test_donation_form_custom_amount(self):
        """Test form validates successfully with a valid custom amount."""
        settings = {
            'donation_text': 'Support us',
            'donation_options': [10, 20, 50],
        }
        form = DonationModule.get_form(settings=settings, form_data={'amount_donation': '-1', 'custom_amount': '25'})
        self.assertTrue(form.is_valid())

    def test_donation_form_missing_custom_amount(self):
        """Test form validation fails when custom is selected but amount is missing."""
        settings = {
            'donation_text': 'Support us',
            'donation_options': [10, 20, 50],
        }
        form = DonationModule.get_form(settings=settings, form_data={'amount_donation': '-1', 'custom_amount': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('custom_amount', form.errors)


class DonationModuleTest(TestCase):
    """Comprehensive tests for DonationModule handler behavior, settings, and completion tracking."""

    def setUp(self):
        super().setUp()
        self.prog = Program.objects.create(
            name="Test Program",
            url="test-prog",
            grade_min=7,
            grade_max=12,
        )
        self.pm = ProgramModule.objects.create(
            admin_title="Donation Module",
            link_title="Make a Donation",
            module_type="learn",
            handler="DonationModule",
            seq=10,
        )
        self.prog.program_modules.add(self.pm)
        self.prog.save()
        self.module = ProgramModuleObj.getFromProgModule(self.prog, self.pm)

    def test_module_properties(self):
        """Test module_properties returns correct configuration metadata."""
        props = DonationModule.module_properties()
        self.assertEqual(props.get("admin_title"), "Donation Module")
        self.assertEqual(props.get("module_type"), "learn")

    def test_apply_settings_defaults(self):
        """Test apply_settings sets up expected default configurations."""
        settings = self.module.apply_settings()
        self.assertIn('donation_text', settings)
        self.assertIn('donation_options', settings)
        self.assertIsInstance(settings['donation_options'], list)

    def test_apply_settings_valid_tag_overrides_defaults(self):
        """Test a valid donation_settings tag is merged over the defaults."""
        Tag.setTag('donation_settings', target=self.prog, value='{"donation_options": [5, 25, 100]}')
        settings = self.module.apply_settings()
        self.assertEqual(settings['donation_options'], [5, 25, 100])
        self.assertEqual(settings['donation_text'], 'Donation to Learning Unlimited')

    def test_apply_settings_bad_tag_falls_back_to_defaults(self):
        """Test apply_settings ignores empty, malformed, or non-dict tag values (#5068)."""
        for value in ['', 'not json', 'null', '[10, 20]', '"text"']:
            with self.subTest(value=value):
                Tag.setTag('donation_settings', target=self.prog, value=value)
                settings = self.module.apply_settings()
                self.assertEqual(settings['donation_text'], 'Donation to Learning Unlimited')
                self.assertEqual(settings['donation_options'], [10, 20, 50])

    def test_line_item_type_resolution(self):
        """Test that line_item_type correctly resolves or creates accounting records."""
        lit = self.module.line_item_type()
        self.assertIsNotNone(lit)
