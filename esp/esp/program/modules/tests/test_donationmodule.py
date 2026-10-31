"""Tests for esp.program.modules.handlers.donationmodule"""
from django.test import SimpleTestCase, TestCase
from esp.accounting.models import Account, LineItemType, Transfer
from esp.program.modules.handlers.donationmodule import DonationModule, DonationForm
from esp.program.models import Program, ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.users.models import ESPUser

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

    def test_line_item_type_resolution(self):
        """Test that line_item_type correctly resolves or creates accounting records."""
        lit = self.module.line_item_type()
        self.assertIsNotNone(lit)

    def test_students_does_not_create_line_item(self):
        """Test that listing donors never creates a line item type."""
        self.module.students()
        self.assertFalse(LineItemType.objects.filter(program=self.prog).exists())

    def test_students_counts_donors_on_duplicate_line_items(self):
        """Test that donors are found even if past races duplicated the line item type."""
        text = self.module.get_setting('donation_text')
        source = Account.objects.create(name='source', description='')
        destination = Account.objects.create(name='destination', description='', program=self.prog)
        donors = []
        for i in range(2):
            lit = LineItemType.objects.create(program=self.prog, text=text)
            donor = ESPUser.objects.create(username='donor%d' % i)
            Transfer.objects.create(source=source, destination=destination, user=donor,
                                    line_item=lit, amount_dec=10)
            donors.append(donor)
        self.assertEqual(set(self.module.students()['donation']), set(donors))
