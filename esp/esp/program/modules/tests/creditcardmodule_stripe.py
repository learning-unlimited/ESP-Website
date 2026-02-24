__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2022 by the individual contributors
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
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.modules.handlers.creditcardmodule_stripe import CreditCardModule_Stripe


class CreditCardModuleStripeTest(ProgramFrameworkTest):
    """Tests for CreditCardModule_Stripe.

    Covers the fix for issue #3501: when the credit card module is marked as
    required, the payonline view must not count the module against itself in
    the required-completion check (since a user cannot have paid before
    reaching the payment page).
    """

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)

        # Retrieve the CreditCardModule_Stripe ProgramModuleObj for this program.
        cc_pm = ProgramModule.objects.get(handler='CreditCardModule_Stripe')
        self.cc_pmo = ProgramModuleObj.getFromProgModule(self.program, cc_pm)

        # Make every 'learn' module non-required.  We cast to ProgramModuleObj
        # before saving so that Django signals fire on the concrete model and
        # the getModules_cached cache is properly invalidated.
        for pmo in self.program.getModules(tl='learn'):
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        # Mark only the credit card module as required.
        self.cc_pmo.__class__ = ProgramModuleObj
        self.cc_pmo.required = True
        self.cc_pmo.save()

        # Log in as the first student so the view decorators are satisfied.
        self.student = self.students[0]
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
            "Could not log in as student %s" % self.student.username,
        )

    def _payonline_url(self):
        return '/learn/%s/payonline' % self.program.getUrlBase()

    def test_payonline_not_blocked_when_cc_module_is_required(self):
        """Regression test for #3501.

        When the credit card module is the only required module the payonline
        view must not raise the "complete required steps" ESPError.  The view
        must proceed past the required-module guard regardless of whether
        Stripe is configured in the current environment (the response may be
        200 with the payment form or a different error, but never the
        required-steps block).
        """
        response = self.client.get(self._payonline_url())

        # The "required steps" text must NOT appear in the response.  We do
        # not assert a specific status code here because the outcome after the
        # guard depends on whether Stripe is configured in the test environment
        # (200 if fully configured, 500 for Stripe-setup error otherwise).
        self.assertNotIn(
            "Please go back and ensure that you have completed all required steps",
            response.content.decode('utf-8'),
        )

    def test_payonline_still_blocked_by_other_incomplete_required_modules(self):
        """The payonline guard must still fire for genuinely incomplete modules.

        RegProfileModule is used as the blocking module because its
        isCompleted() predictably returns False when students have no
        registration profile, which is the case in the default
        ProgramFrameworkTest fixture.
        """
        # Retrieve the learn-type RegProfileModule and mark it required.
        reg_pm = ProgramModule.objects.get(
            handler='RegProfileModule', module_type='learn'
        )
        reg_pmo = ProgramModuleObj.getFromProgModule(self.program, reg_pm)
        reg_pmo.__class__ = ProgramModuleObj
        reg_pmo.required = True
        reg_pmo.save()

        response = self.client.get(self._payonline_url())

        # Students have no profiles, so RegProfileModule.isCompleted() is
        # False.  The required-module guard must raise the blocking ESPError.
        self.assertContains(
            response,
            "Please go back and ensure that you have completed all required steps",
            status_code=500,
        )
