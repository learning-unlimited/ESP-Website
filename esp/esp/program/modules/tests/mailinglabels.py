__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2024 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.users.models import ContactInfo


class MailingLabelsModuleTest(ProgramFrameworkTest):
    """Unit tests for the MailingLabels module, focusing on the badzips() view."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)

        m, _ = ProgramModule.objects.get_or_create(
            handler='MailingLabels',
            module_type='manage',
            defaults={
                'admin_title': 'Mailing Label Generation',
                'link_title': 'Generate Mailing Labels',
                'seq': 100,
                'choosable': 1,
            },
        )
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, m)

        base = self.program.getUrlBase()
        self.badzips_url = '/manage/%s/badzips' % base
        self.mailinglabel_url = '/manage/%s/mailinglabel/' % base

    def _login_admin(self):
        self.assertTrue(
            self.client.login(username=self.admins[0].username, password='password'),
            "Failed to log in as admin user.",
        )

    # ------------------------------------------------------------------
    # GET tests
    # ------------------------------------------------------------------

    def test_badzips_get_renders_form(self):
        """GET /badzips returns HTTP 200 and includes the ban-zips form."""
        self._login_admin()
        response = self.client.get(self.badzips_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_badzips_get_form_is_empty(self):
        """GET /badzips provides an unbound (empty) form."""
        self._login_admin()
        response = self.client.get(self.badzips_url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_bound)

    # ------------------------------------------------------------------
    # POST tests — valid zip code (>= 10 chars)
    # ------------------------------------------------------------------

    def test_badzips_post_valid_zip_redirects(self):
        """POST with a valid zip+4 entry redirects to the mailinglabel index."""
        self._login_admin()
        response = self.client.post(self.badzips_url, {'zips': '02139-4030'})
        self.assertRedirects(response, self.mailinglabel_url, fetch_redirect_response=False)

    def test_badzips_post_valid_zip_marks_contact_undeliverable(self):
        """
        POST with a valid zip+4 (>= 10 chars) marks matching ContactInfo records
        as undeliverable.

        The handler queries:
            ContactInfo.objects.filter(address_postal__contains="'<zip>'")
        so the fixture stores the zip wrapped in single quotes inside address_postal.
        """
        self._login_admin()

        zip_code = '02139-4030'
        contact = ContactInfo.objects.create(
            first_name='Test',
            last_name='User',
            # The handler searches for "'<zip>'" as a substring of address_postal
            address_postal="'%s'" % zip_code,
            undeliverable=False,
        )

        self.client.post(self.badzips_url, {'zips': zip_code})

        contact.refresh_from_db()
        self.assertTrue(
            contact.undeliverable,
            "ContactInfo should be marked undeliverable after its zip is banned.",
        )

    def test_badzips_post_valid_zip_does_not_affect_other_contacts(self):
        """Banning one zip must not affect ContactInfo records with different addresses."""
        self._login_admin()

        banned_zip = '02139-4030'
        other_zip  = '10001-1234'

        banned_contact = ContactInfo.objects.create(
            first_name='Banned',
            last_name='Contact',
            address_postal="'%s'" % banned_zip,
            undeliverable=False,
        )
        other_contact = ContactInfo.objects.create(
            first_name='Safe',
            last_name='Contact',
            address_postal="'%s'" % other_zip,
            undeliverable=False,
        )

        self.client.post(self.badzips_url, {'zips': banned_zip})

        banned_contact.refresh_from_db()
        other_contact.refresh_from_db()
        self.assertTrue(banned_contact.undeliverable, "Banned zip contact should be undeliverable.")
        self.assertFalse(other_contact.undeliverable, "Unrelated contact should remain deliverable.")

    # ------------------------------------------------------------------
    # POST tests — short / invalid zip lines (< 10 chars)
    # ------------------------------------------------------------------

    def test_badzips_post_short_zip_still_redirects(self):
        """
        POST with a zip shorter than 10 chars still redirects — the form is
        valid but the short entry is silently skipped by the handler.
        """
        self._login_admin()
        response = self.client.post(self.badzips_url, {'zips': '02139'})
        self.assertRedirects(response, self.mailinglabel_url, fetch_redirect_response=False)

    def test_badzips_post_short_zip_does_not_mark_undeliverable(self):
        """A zip shorter than 10 chars is skipped — no ContactInfo is changed."""
        self._login_admin()

        short_zip = '02139'  # 5 chars — below the 10-char threshold
        contact = ContactInfo.objects.create(
            first_name='Short',
            last_name='ZipUser',
            address_postal="'%s'" % short_zip,
            undeliverable=False,
        )

        self.client.post(self.badzips_url, {'zips': short_zip})

        contact.refresh_from_db()
        self.assertFalse(
            contact.undeliverable,
            "Short zip should be skipped; ContactInfo should remain deliverable.",
        )

    def test_badzips_post_exactly_nine_chars_skipped(self):
        """A zip of exactly 9 characters (one below threshold) must also be skipped."""
        self._login_admin()

        nine_char_zip = '123456789'  # 9 chars
        contact = ContactInfo.objects.create(
            first_name='Nine',
            last_name='CharZip',
            address_postal="'%s'" % nine_char_zip,
            undeliverable=False,
        )

        self.client.post(self.badzips_url, {'zips': nine_char_zip})

        contact.refresh_from_db()
        self.assertFalse(
            contact.undeliverable,
            "9-char zip should be skipped; ContactInfo should remain deliverable.",
        )

    # ------------------------------------------------------------------
    # POST tests — mixed input (some valid, some short)
    # ------------------------------------------------------------------

    def test_badzips_post_mixed_zips_only_valid_processed(self):
        """
        When the textarea contains both valid and short zips, only those >= 10
        chars are processed.  Short entries must not cause side effects.
        """
        self._login_admin()

        valid_zip = '02139-4030'
        short_zip = '02139'

        valid_contact = ContactInfo.objects.create(
            first_name='Valid',
            last_name='Contact',
            address_postal="'%s'" % valid_zip,
            undeliverable=False,
        )
        short_contact = ContactInfo.objects.create(
            first_name='Short',
            last_name='Contact',
            address_postal="'%s'" % short_zip,
            undeliverable=False,
        )

        zips_input = '%s\n%s' % (valid_zip, short_zip)
        response = self.client.post(self.badzips_url, {'zips': zips_input})

        self.assertRedirects(response, self.mailinglabel_url, fetch_redirect_response=False)

        valid_contact.refresh_from_db()
        short_contact.refresh_from_db()
        self.assertTrue(valid_contact.undeliverable, "Valid zip contact should be marked undeliverable.")
        self.assertFalse(short_contact.undeliverable, "Short zip contact should remain deliverable.")

    def test_badzips_post_multiple_valid_zips(self):
        """Multiple valid zips in one POST must all be processed."""
        self._login_admin()

        zip_a = '02139-4030'
        zip_b = '10001-1234'

        contact_a = ContactInfo.objects.create(
            first_name='Contact',
            last_name='A',
            address_postal="'%s'" % zip_a,
            undeliverable=False,
        )
        contact_b = ContactInfo.objects.create(
            first_name='Contact',
            last_name='B',
            address_postal="'%s'" % zip_b,
            undeliverable=False,
        )

        zips_input = '%s\n%s' % (zip_a, zip_b)
        self.client.post(self.badzips_url, {'zips': zips_input})

        contact_a.refresh_from_db()
        contact_b.refresh_from_db()
        self.assertTrue(contact_a.undeliverable, "contact_a should be marked undeliverable.")
        self.assertTrue(contact_b.undeliverable, "contact_b should be marked undeliverable.")

    # ------------------------------------------------------------------
    # Access control
    # ------------------------------------------------------------------

    def test_badzips_requires_login(self):
        """Unauthenticated requests to /badzips must not return 200."""
        response = self.client.get(self.badzips_url)
        # Should redirect to login or return 403 — either way, not 200.
        self.assertNotEqual(response.status_code, 200)

    def test_badzips_requires_admin(self):
        """Non-admin (student) users must not be able to access /badzips."""
        self.client.login(username=self.students[0].username, password='password')
        response = self.client.get(self.badzips_url)
        self.assertNotEqual(response.status_code, 200)
