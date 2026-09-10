"""Tests for the director_email validation pattern on ProgramCreationForm."""
import re

from django.conf import settings
from django.test import SimpleTestCase

from esp.program.forms import ProgramCreationForm


class DirectorEmailPatternTest(SimpleTestCase):
    """The pattern accepts the site's own domain plus any learningu.org host.

    It is an HTML `pattern` attribute, so it only guides the browser; these
    tests pin down which address shapes it is meant to allow.
    """

    def setUp(self):
        self.pattern = ProgramCreationForm.base_fields['director_email'].widget.attrs['pattern']
        self.site_domain = settings.SITE_INFO[1]

    def matches(self, email):
        return bool(re.match(self.pattern, email))

    def test_accepts_the_sites_own_domain(self):
        self.assertTrue(self.matches('director@%s' % self.site_domain))

    def test_accepts_learningu_org_at_any_depth(self):
        # The bare domain and one or more subdomain labels are all valid hosts
        for email in ('web-team@learningu.org',
                      'info@web.learningu.org',
                      'info@a.b.learningu.org'):
            with self.subTest(email=email):
                self.assertTrue(self.matches(email))

    def test_rejects_unrelated_domains(self):
        for email in ('someone@example.com',
                      'someone@notlearningu.org',
                      'someone@learningu.org.example.com'):
            with self.subTest(email=email):
                self.assertFalse(self.matches(email))
