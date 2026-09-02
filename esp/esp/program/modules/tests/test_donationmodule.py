"""Tests for esp.program.modules.handlers.donationmodule"""
from django.test import SimpleTestCase, TestCase
from esp.program.modules.handlers.donationmodule import DonationModule, DonationForm
from esp.program.models import Program, ProgramModule
from esp.program.modules.base import ProgramModuleObj

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
    """Tests for DonationModule handler behavior."""

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
