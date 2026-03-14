"""
Tests for DonationModule.apply_settings() when the donation_settings Tag is
absent or set to an empty string.

Regression for: DonationModule.apply_settings() crashes with
json.JSONDecodeError on missing Tag (#5068).
"""

from esp.program.models import Program, ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.program.modules.handlers.donationmodule import DonationModule
from esp.tagdict.models import Tag
from esp.tests.util import CacheFlushTestCase as TestCase


def _get_donation_module(program):
    pm = ProgramModule.objects.get(handler='DonationModule')
    return ProgramModuleObj.getFromProgModule(program, pm)


class DonationModuleApplySettingsTest(TestCase):
    """apply_settings() must not crash when the Tag is absent or empty."""

    def setUp(self):
        super().setUp()
        self.program = Program.objects.create(
            url='donationtest', name='Donation Test Program',
            grade_min=7, grade_max=12,
        )

    def test_no_tag_returns_defaults(self):
        """apply_settings() returns only DEFAULTS when no tag is set."""
        module = _get_donation_module(self.program)
        settings = module.apply_settings()
        self.assertEqual(settings['donation_text'], 'Donation to Learning Unlimited')
        self.assertEqual(settings['donation_options'], [10, 20, 50])

    def test_empty_string_tag_returns_defaults(self):
        """apply_settings() does not raise when the Tag value is an empty string."""
        Tag.setTag('donation_settings', target=self.program, value='')
        module = _get_donation_module(self.program)
        settings = module.apply_settings()
        self.assertEqual(settings['donation_text'], 'Donation to Learning Unlimited')
        self.assertEqual(settings['donation_options'], [10, 20, 50])

    def test_valid_tag_overrides_defaults(self):
        """apply_settings() merges tag values over DEFAULTS."""
        Tag.setTag(
            'donation_settings', target=self.program,
            value='{"donation_options": [5, 25, 100]}',
        )
        module = _get_donation_module(self.program)
        settings = module.apply_settings()
        self.assertEqual(settings['donation_options'], [5, 25, 100])
        self.assertEqual(settings['donation_text'], 'Donation to Learning Unlimited')
