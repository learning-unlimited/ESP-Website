"""Tests for the "which From/director addresses are allowed" domain rule.

The rule is: the site's own domain, or learningu.org at any subdomain depth.
It is spelled out in the director_email help text and enforced by a model
validator; the HTML `pattern` attributes and the outgoing-mail guard are
separate copies of the same rule, so these tests check they all agree.
"""

import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings

from esp.dbmail.models import send_mail
from esp.middleware.esperrormiddleware import ESPError_Log
from esp.program.forms import ProgramCreationForm
from esp.program.models import Program
from esp.program.modules.forms.admincore import ProgramSettingsForm

SITE = settings.SITE_INFO[1]

ALLOWED = [
    "director@%s" % SITE,
    "web-team@learningu.org",
    "info@web.learningu.org",
    "info@a.b.learningu.org",
]

REJECTED = [
    "someone@example.com",
    "someone@notlearningu.org",
    "someone@learningu.org.example.com",
]


class DirectorEmailValidatorTest(SimpleTestCase):
    """Server-side enforcement, via the model field's validators."""

    def accepts(self, email):
        try:
            for validator in Program._meta.get_field("director_email").validators:
                validator(email)
        except ValidationError:
            return False
        return True

    def test_accepts_allowed_addresses(self):
        for email in ALLOWED:
            with self.subTest(email=email):
                self.assertTrue(self.accepts(email))

    def test_rejects_other_domains(self):
        for email in REJECTED:
            with self.subTest(email=email):
                self.assertFalse(self.accepts(email))


class DirectorEmailPatternTest(SimpleTestCase):
    """The browser hints must agree with the server-side validator."""

    def patterns(self):
        return {
            "ProgramCreationForm": ProgramCreationForm.base_fields[
                "director_email"
            ].widget.attrs["pattern"],
            "ProgramSettingsForm": ProgramSettingsForm.base_fields[
                "director_email"
            ].widget.attrs["pattern"],
        }

    def test_patterns_accept_allowed_addresses(self):
        for name, pattern in self.patterns().items():
            for email in ALLOWED:
                with self.subTest(form=name, email=email):
                    self.assertTrue(re.match(pattern, email))

    def test_patterns_reject_other_domains(self):
        for name, pattern in self.patterns().items():
            for email in REJECTED:
                with self.subTest(form=name, email=email):
                    self.assertFalse(re.match(pattern, email))


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SendMailFromAddressTest(SimpleTestCase):
    """send_mail guards the From address so DMARC does not reject the message."""

    def send_from(self, from_email):
        send_mail("subject", "body", from_email, ["someone@example.com"])

    def test_accepts_allowed_addresses(self):
        for email in ALLOWED:
            with self.subTest(from_email=email):
                self.send_from(email)

    def test_accepts_display_name_form(self):
        # The guard has separate alternations for bare and "Name <addr>" forms
        self.send_from("LU Directors <info@a.b.learningu.org>")

    def test_rejects_other_domains(self):
        for email in REJECTED:
            with self.subTest(from_email=email):
                with self.assertRaises(ESPError_Log) as caught:
                    self.send_from(email)
                self.assertIn("Invalid 'From' email address", str(caught.exception))
