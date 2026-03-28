from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.base import ProgramModule
from esp.program.modules.handlers.donationmodule import DonationModule
from esp.users.models import Record, RecordType
from esp.accounting.models import LineItemType


class DonationFormTest(ProgramFrameworkTest):
    """Tests for DonationForm validation logic"""

    def _settings(self):
        return {
            'donation_text': 'Donation to Learning Unlimited',
            'donation_options': [10, 20, 50],
        }

    def test_valid_preset_amount(self):
        form = DonationModule.get_form(
            settings=self._settings(),
            form_data={
                'amount_donation': '10',
                'custom_amount': ''
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_custom_amount_required_when_selected(self):
        form = DonationModule.get_form(
            settings=self._settings(),
            form_data={
                'amount_donation': '-1',
                'custom_amount': ''
            }
        )
        self.assertFalse(form.is_valid())

    def test_valid_custom_amount(self):
        form = DonationModule.get_form(
            settings=self._settings(),
            form_data={
                'amount_donation': '-1',
                'custom_amount': '25'
            }
        )
        self.assertTrue(form.is_valid(), form.errors)


class DonationModuleTest(ProgramFrameworkTest):
    """Tests for DonationModule behavior"""

    def setUp(self):
        super().setUp(modules=[
            ProgramModule.objects.get(handler='DonationModule')
        ])
        self.module = self.program.getModule('DonationModule')
        # Use the first student from ProgramFrameworkTest
        self.user = self.students[0]

    def test_apply_settings_default(self):
        settings = self.module.apply_settings()

        self.assertIn('donation_text', settings)
        self.assertIn('donation_options', settings)
        self.assertIsInstance(settings['donation_options'], list)

    def test_line_item_type_creation(self):
        item = self.module.line_item_type()

        self.assertIsNotNone(item)
        self.assertIsInstance(item, LineItemType)

    def test_line_item_type_reuse(self):
        item1 = self.module.line_item_type()
        item2 = self.module.line_item_type()

        self.assertEqual(item1.id, item2.id)

    def test_is_completed_false_initially(self):
        self.assertFalse(self.module.isCompleted(self.user))

    def test_is_completed_true_after_record(self):
        record_type = RecordType.objects.get(name=self.module.event)

        Record.objects.create(
            user=self.user,
            program=self.program,
            event=record_type
        )

        self.assertTrue(self.module.isCompleted(self.user))
