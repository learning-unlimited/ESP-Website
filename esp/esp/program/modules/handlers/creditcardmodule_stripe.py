__author__ = "Individual contributors (see AUTHORS file)"
__date__ = "$DATE$"
__rev__ = "$REV$"
__license__ = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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

from decimal import Decimal
import json
import re

import stripe
from django.conf import settings
from django.contrib.sites.models import Site
from django.db import transaction
from django.db.models.query import Q
from django.template.loader import render_to_string

from esp.accounting.controllers import (
    IndividualAccountingController,
    ProgramAccountingController,
)
from esp.accounting.models import LineItemType
from esp.dbmail.models import send_mail
from esp.middleware import ESPError
from esp.middleware.threadlocalrequest import get_current_request
from esp.program.modules.admin_search import (
    AdminSearchEntry,
    SEARCH_CATEGORY_FINANCIAL,
)
from esp.program.modules.base import (
    ProgramModuleObj,
    aux_call,
    main_call,
    meets_cap,
    meets_deadline,
    needs_student_in_grade,
)
from esp.program.modules.handlers.donationmodule import DonationModule
from esp.tagdict.models import Tag
from esp.users.models import ESPUser
from esp.utils.web import render_to_response


class CreditCardModule_Stripe(ProgramModuleObj):
    doc = """Accept credit card payments via Stripe."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Credit Card Payment Module (Stripe)",
            "link_title": "Credit Card Payment",
            "module_type": "learn",
            "seq": 10000,
            "choosable": 0,
        }

    @classmethod
    def get_admin_search_entry(cls, program, tl, view_name, pmo):
        # The "Refunds" dashboard button is not a program-module view. It links to
        # the accounting app at /accounting/refund and is shown whenever this Stripe
        # module is attached. Surface the same admin tool in search.
        if view_name != "payonline":
            return None

        return AdminSearchEntry(
            id="manage_refund",
            url="/accounting/refund?program=%s" % program.id,
            title="Refunds",
            category=SEARCH_CATEGORY_FINANCIAL,
            keywords=[
                "refund",
                "refunds",
                "credit card",
                "payment",
                "accounting",
            ],
        )

    def apply_settings(self):
        if hasattr(self, "_settings_cache"):
            return self._settings_cache

        # Rather than using a model in module_ext.*, configure the module
        # from a Tag, which can be per-program or global, combining the
        # Tag's specifications with defaults in the code.
        defaults = {
            "offer_donation": True,
            "donation_text": "Donation to Learning Unlimited",
            "donation_options": [10, 20, 50],
            "invoice_prefix": settings.INSTITUTION_NAME.lower(),
        }

        defaults.update(settings.STRIPE_CONFIG)

        tag_data = Tag.getProgramTag("stripe_settings", self.program)
        if tag_data:
            defaults.update(json.loads(tag_data))

        self._settings_cache = defaults
        return self._settings_cache

    def get_setting(self, name, default=None):
        return self.apply_settings().get(name, default)

    def line_item_type(self):
        donate_type, created = LineItemType.objects.get_or_create(
            program=self.program,
            text=self.get_setting("donation_text"),
        )
        return donate_type

    def isCompleted(self, user=None):
        """Whether the user has fully paid for this program."""
        user = self._resolve_user(user)
        return IndividualAccountingController(
            self.program, user
        ).has_paid(in_full=True)

    have_paid = isCompleted

    def isRequired(self):
        """Conditionally require credit card payment when extra-cost items
        have been selected.

        Returns True if:
        - An admin explicitly marked the module as required, OR
        - The 'creditcard_required_for_extracosts' tag is set for the program,
          the student has selected matching extra-cost items, AND has an
          outstanding balance >= $0.50.

        The tag value controls which items trigger the requirement:
        - '*' means any extra-cost item, excluding program admission.
        - 'Meal Ticket,T-Shirt' means only those specific items.
        """
        if super(CreditCardModule_Stripe, self).isRequired():
            return True

        return self._extracost_requires_payment()

    def _extracost_requires_payment(self):
        """Check if the student selected extra-cost items requiring CC payment."""
        from esp.accounting.models import Transfer

        tag_value = Tag.getProgramTag(
            "creditcard_required_for_extracosts",
            program=self.program,
            default="",
        )

        if not tag_value:
            return False

        request = get_current_request()
        user = getattr(self, "user", request.user if request else None)

        if not user or not user.is_authenticated:
            return False

        iac = IndividualAccountingController(self.program, user)

        if iac.amount_due() < Decimal("0.50"):
            return False

        pac = ProgramAccountingController(self.program)

        extra_lits = pac.get_lineitemtypes(
            include_donations=False
        ).exclude(text__in=pac.admission_items)

        if tag_value.strip() != "*":
            item_names = [
                name.strip()
                for name in tag_value.split(",")
                if name.strip()
            ]
            extra_lits = extra_lits.filter(text__in=item_names)

        return Transfer.objects.filter(
            user=user,
            line_item__in=extra_lits,
        ).exists()

    def students(self, QObject=False):
        # This query represents students who have a payment transfer from outside.
        pac = ProgramAccountingController(self.program)

        q_obj = Q(
            transfer__source__isnull=True,
            transfer__line_item=pac.default_payments_lineitemtype(),
        )

        if QObject:
            return {"creditcard": q_obj}

        return {
            "creditcard": ESPUser.objects.filter(q_obj).distinct()
        }

    def studentDesc(self):
        return {
            "creditcard": (
                "Students who have filled out the credit card form"
            )
        }

    def check_setup(self):
        """Validate the keys specified in the stripe_settings Tag.

        If something is wrong, return False; otherwise return True.
        """
        self.apply_settings()

        # Check for a donation line-item type on this program, which we need.
        if self.get_setting("offer_donation"):
            LineItemType.objects.get_or_create(
                text=self.get_setting("donation_text"),
                program=self.program,
                required=False,
            )

        # A Stripe account comes with publishable and secret keys.
        valid_pk_re = r"pk_(test|live)_([A-Za-z0-9+/=]){24}"
        valid_sk_re = r"sk_(test|live)_([A-Za-z0-9+/=]){24}"

        publishable_key = self.get_setting("publishable_key")
        secret_key = self.get_setting("secret_key")

        if (
            not publishable_key
            or not secret_key
            or not re.match(valid_pk_re, publishable_key)
            or not re.match(valid_sk_re, secret_key)
        ):
            return False

        return True

    @main_call
    @needs_student_in_grade
    @meets_deadline("/Payment")
    @meets_cap
    def payonline(
        self,
        request,
        tl,
        one,
        two,
        module,
        extra,
        prog,
    ):
        # Check that the user has completed all required modules before
        # paying by credit card.
        modules = prog.getModules(request.user, tl)
        completed_all = True

        for module in modules:
            # Skip the credit card module itself to avoid circular blocking.
            if module.id == self.id:
                continue

            if (
                not module.isCompleted(request.user)
                and module.isRequired()
            ):
                completed_all = False

        if not completed_all and not request.user.isAdmin(prog):
            raise ESPError(
                "Please go back and ensure that you have completed all "
                "required steps of registration before paying by credit card.",
                log=False,
            )

        # Check Stripe setup.
        if not self.check_setup():
            raise ESPError(
                "The site has not yet been properly set up for credit card "
                "payments. Administrators should contact the "
                '<a href="mailto:{{settings.SUPPORT}}">websupport team</a> '
                "to get it set up.",
                True,
            )

        user = request.user
        iac = IndividualAccountingController(self.program, request.user)

        context = {
            "module": self,
            "program": prog,
            "user": user,
            "invoice_id": iac.get_id(),
            "identifier": iac.get_identifier(),
        }

        payment_type = iac.default_payments_lineitemtype()
        sibling_type = iac.default_siblingdiscount_lineitemtype()
        grant_type = iac.default_finaid_lineitemtype()

        offer_donation = self.get_setting("offer_donation")
        donate_type = (
            LineItemType.objects.get(
                program=self.program,
                text=self.get_setting("donation_text"),
            )
            if offer_donation
            else None
        )

        excluded_types = [
            item
            for item in [
                payment_type,
                sibling_type,
                grant_type,
                donate_type,
            ]
            if item
        ]

        context["itemizedcosts"] = (
            iac.get_transfers()
            .exclude(line_item__in=excluded_types)
            .order_by("-line_item__required")
        )

        context["itemizedcosttotal"] = iac.amount_due()

        # Stripe expects the amount in integer cents.
        context["totalcost_cents"] = int(
            context["itemizedcosttotal"] * 100
        )

        context["subtotal"] = iac.amount_requested()
        context["financial_aid"] = iac.amount_finaid()
        context["sibling_discount"] = iac.amount_siblingdiscount()
        context["amount_paid"] = iac.amount_paid()
        context["amount_refunded"] = iac.amount_refunded()

        # Load donation amount separately because client-side code needs it.
        donation_prefs = (
            iac.get_preferences([donate_type])
            if offer_donation
            else None
        )

        if donation_prefs:
            context["amount_donation"] = Decimal(donation_prefs[0][2])
            context["has_donation"] = True
            context["form"] = DonationModule.get_form(
                settings=self.apply_settings(),
                donation_initial=context["amount_donation"],
            )
        else:
            context["amount_donation"] = Decimal("0.00")
            context["has_donation"] = False
            context["form"] = DonationModule.get_form(
                settings=self.apply_settings(),
                donation_initial=None,
            )

        context["amount_without_donation"] = (
            context["itemizedcosttotal"]
            - context["amount_donation"]
        )

        if "HTTP_HOST" in request.META:
            context["hostname"] = request.META["HTTP_HOST"]
        else:
            context["hostname"] = Site.objects.get_current().domain

        context["institution"] = settings.INSTITUTION_NAME
        context["support_email"] = settings.DEFAULT_EMAIL_ADDRESSES[
            "support"
        ]

        return render_to_response(
            self.baseDir() + "cardpay.html",
            request,
            context,
        )

    def send_error_email(self, request, context):
        """Send an email to admins explaining the credit card error."""
        context["request"] = request
        context["program"] = self.program
        context["postdata"] = request.POST.copy()

        domain_name = Site.objects.get_current().domain

        msg_content = render_to_string(
            self.baseDir() + "error_email.txt",
            context,
        )

        msg_subject = (
            f"[ ESP CC ] Credit card error on {domain_name}: "
            f"{request.user.id} {request.user.name()}"
        )

        # This message could contain sensitive information. Send to the
        # confidential messages address, and don't bcc the archive list.
        send_mail(
            msg_subject,
            msg_content,
            settings.SERVER_EMAIL,
            [self.program.getDirectorConfidentialEmail()],
            bcc=None,
        )

    @aux_call
    @needs_student_in_grade
    def charge_payment(
        self,
        request,
        tl,
        one,
        two,
        module,
        extra,
        prog,
    ):
        # Check Stripe setup.
        if not self.check_setup():
            raise ESPError(
                "The site has not yet been properly set up for credit card "
                "payments. Administrators should contact the "
                '<a href="mailto:{{settings.SUPPORT}}">websupport team</a> '
                "to get it set up.",
                True,
            )

        context = {
            "postdata": request.POST.copy()
        }

        group_name = (
            Tag.getTag("full_group_name")
            or f"{settings.INSTITUTION_NAME} "
            f"{settings.ORGANIZATION_SHORT_NAME}"
        )

        iac = IndividualAccountingController(
            self.program,
            request.user,
        )

        # Set donation transfer.
        form = None

        if request.method == "POST":
            donation_type = self.line_item_type()
            current_donation_prefs = iac.get_preferences(
                [donation_type]
            )

            if current_donation_prefs:
                current_donation = Decimal(
                    current_donation_prefs[0][2]
                )
            else:
                current_donation = None

            form = DonationModule.get_form(
                settings=self.apply_settings(),
                donation_initial=current_donation,
                form_data=request.POST,
            )

            if form.is_valid():
                # Clear the existing donation transfer by specifying
                # quantity 0.
                iac.set_preference(
                    self.get_setting("donation_text"),
                    0,
                )

                if form.amount:
                    iac.set_preference(
                        self.get_setting("donation_text"),
                        1,
                        amount=form.amount,
                    )

        # Set Stripe key based on settings.
        stripe.api_key = self.get_setting("secret_key")

        # Keep the API version pinned if the legacy payment code requires it.
        stripe.api_version = "2014-03-13"

        if request.POST.get("ponumber", "") != iac.get_id():
            # Payment was submitted for the wrong PO.
            context["error_type"] = "inconsistent_po"
            context["error_info"] = {
                "request_po": request.POST.get("ponumber", ""),
                "user_po": iac.get_id(),
            }

        if "error_type" not in context:
            # Check the amount in POST against the amount in our records.
            amount_cents_post = Decimal(
                request.POST["totalcost_cents"]
            )

            amount_cents_iac = Decimal(
                iac.amount_due()
            ) * 100

            if amount_cents_post != amount_cents_iac:
                context["error_type"] = "inconsistent_amount"
                context["error_info"] = {
                    "amount_cents_post": amount_cents_post,
                    "amount_cents_iac": amount_cents_iac,
                }

        if "error_type" not in context:
            try:
                with transaction.atomic():
                    # Save a record of the charge if we can uniquely
                    # identify the user/program.
                    totalcost_dollars = (
                        Decimal(request.POST["totalcost_cents"]) / 100
                    )

                    transfer = iac.submit_payment(
                        totalcost_dollars,
                        "TBD",
                    )

                    # Create the charge on Stripe's servers.
                    charge = stripe.Charge.create(
                        amount=int(amount_cents_post),
                        currency="usd",
                        source=request.POST["stripeToken"],
                        description=(
                            f"Payment for {group_name} "
                            f"{prog.niceName()} - "
                            f"{request.user.name()}"
                        ),
                        statement_descriptor=group_name[:22],
                        metadata={
                            "ponumber": request.POST["ponumber"],
                        },
                    )

                    # Save Stripe's transaction ID.
                    transfer.transaction_id = charge.id
                    transfer.save()

            except stripe.error.CardError as e:
                context["error_type"] = "declined"
                context["error_info"] = e.json_body["error"]

            except stripe.error.InvalidRequestError:
                context["error_type"] = "invalid"

            except stripe.error.AuthenticationError:
                context["error_type"] = "auth"

            except stripe.error.APIConnectionError:
                context["error_type"] = "api"

            except stripe.error.StripeError:
                context["error_type"] = "generic"

        if "error_type" in context:
            # Send an email to admins and render the error page.
            self.send_error_email(request, context)

            return render_to_response(
                self.baseDir() + "failure.html",
                request,
                context,
            )

        # Render the success page.
        context["amount_paid"] = totalcost_dollars
        context["statement_descriptor"] = group_name[:22]
        context["can_confirm"] = self.deadline_met("/Confirm")

        return render_to_response(
            self.baseDir() + "success.html",
            request,
            context,
        )

    def isStep(self):
        return self.check_setup()

    class Meta:
        proxy = True
        app_label = "modules"
