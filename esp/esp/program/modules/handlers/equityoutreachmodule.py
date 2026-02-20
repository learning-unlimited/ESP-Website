from __future__ import absolute_import

import logging

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.utils.html import strip_tags

from esp.dbmail.models import MessageRequest
from esp.middleware import ESPError
from esp.program.models import EquityOutreachCampaign, EquityOutreachRecipient
from esp.program.modules.base import ProgramModuleObj, aux_call, main_call, needs_admin
from esp.program.modules.handlers.equityoutreach import EquityOutreachCohorts
from esp.program.modules.handlers.grouptextmodule import GroupTextModule
from esp.users.models import ContactInfo, ESPUser, PersistentQueryFilter
from esp.utils.web import render_to_response

from phonenumbers import PhoneNumberFormat, format_number
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client


logger = logging.getLogger(__name__)


class EquityOutreachModule(ProgramModuleObj):
    doc = """Targeted outreach dashboard for at-risk student cohorts."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Equity Outreach Navigator",
            "link_title": "Equity Outreach Navigator",
            "module_type": "manage",
            "seq": 35,
            "choosable": 0,
        }

    def _validate_cohort_or_raise(self, cohort_key):
        if cohort_key not in EquityOutreachCohorts.all_cohort_keys():
            raise ESPError("Unknown cohort: %s" % cohort_key, log=False)
        return cohort_key

    def _campaign_history(self):
        return EquityOutreachCampaign.objects.filter(program=self.program).order_by("-created_at")[:25]

    @main_call
    @needs_admin
    def equityoutreach(self, request, tl, one, two, module, extra, prog):
        context = {
            "program": prog,
            "cohorts": EquityOutreachCohorts.cohort_summaries(prog),
            "campaigns": self._campaign_history(),
        }
        return render_to_response(self.baseDir() + "dashboard.html", request, context)

    @aux_call
    @needs_admin
    def equityoutreach_preview(self, request, tl, one, two, module, extra, prog):
        cohort_key = self._validate_cohort_or_raise(request.GET.get("cohort", ""))
        users = EquityOutreachCohorts.users_for_cohort(prog, cohort_key).order_by("last_name", "first_name")

        context = {
            "program": prog,
            "cohort_key": cohort_key,
            "cohort_label": EquityOutreachCohorts.cohort_label(cohort_key),
            "num_recipients": users.count(),
            "sample_recipients": users[:100],
            "campaigns": self._campaign_history(),
        }
        return render_to_response(self.baseDir() + "preview.html", request, context)

    @aux_call
    @needs_admin
    def equityoutreach_compose(self, request, tl, one, two, module, extra, prog):
        cohort_key = self._validate_cohort_or_raise(request.GET.get("cohort", ""))
        users = EquityOutreachCohorts.users_for_cohort(prog, cohort_key)

        context = {
            "program": prog,
            "cohort_key": cohort_key,
            "cohort_label": EquityOutreachCohorts.cohort_label(cohort_key),
            "num_recipients": users.count(),
        }
        return render_to_response(self.baseDir() + "compose.html", request, context)

    @aux_call
    @needs_admin
    def equityoutreach_send(self, request, tl, one, two, module, extra, prog):
        if request.method != "POST":
            raise ESPError("Invalid request method for sending outreach.", log=False)

        cohort_key = self._validate_cohort_or_raise(request.POST.get("cohort_key", ""))
        channel = request.POST.get("channel", "email")
        if channel not in ("email", "sms"):
            raise ESPError("Invalid channel selected.", log=False)

        users = list(EquityOutreachCohorts.users_for_cohort(prog, cohort_key).distinct())
        if not users:
            raise ESPError("This cohort has no recipients right now.", log=False)

        subject = request.POST.get("subject", "").strip()
        body = request.POST.get("body", "").strip()
        if not body:
            raise ESPError("Message body cannot be empty.", log=False)
        if channel == "email" and not subject:
            raise ESPError("Email subject cannot be empty.", log=False)

        campaign = EquityOutreachCampaign.objects.create(
            program=prog,
            cohort_key=cohort_key,
            cohort_label=EquityOutreachCohorts.cohort_label(cohort_key),
            channel=channel,
            subject=subject,
            body=body,
            created_by=request.user,
            recipient_count=len(users),
        )

        if channel == "email":
            self._queue_email_campaign(campaign, users, request.user)
        else:
            override_preferences = "override_sms_preferences" in request.POST
            self._send_sms_campaign(campaign, users, override_preferences=override_preferences)

        campaign.sent_at = timezone.now()
        campaign.save(update_fields=["sent_at", "success_count", "failure_count", "message_request"])

        context = {
            "program": prog,
            "campaign": campaign,
            "recipients": campaign.recipients.select_related("user").order_by("user__last_name", "user__first_name"),
        }
        return render_to_response(self.baseDir() + "sent.html", request, context)

    def _queue_email_campaign(self, campaign, users, creator):
        user_ids = [user.id for user in users]
        q_filter = PersistentQueryFilter.getFilterFromQ(
            Q(id__in=user_ids),
            ESPUser,
            description="Equity outreach campaign #%d recipients" % campaign.id,
        )
        msg_request = MessageRequest.createRequest(
            var_dict={"user": creator, "program": campaign.program},
            subject=campaign.subject,
            msgtext=campaign.body,
            recipients=q_filter,
            sendto_fn_name=MessageRequest.SEND_TO_SELF_REAL,
            sender="%s <%s>" % (campaign.program.niceName(), campaign.program.director_email),
            creator=creator,
        )
        msg_request.save()

        recipients = [
            EquityOutreachRecipient(
                campaign=campaign,
                user=user,
                channel=EquityOutreachCampaign.CHANNEL_EMAIL,
                destination=user.email,
                status=EquityOutreachRecipient.STATUS_QUEUED,
            )
            for user in users
        ]
        EquityOutreachRecipient.objects.bulk_create(recipients)

        campaign.message_request = msg_request
        campaign.success_count = len(recipients)
        campaign.failure_count = 0
        logger.info(
            "Equity outreach email campaign queued: campaign_id=%s program=%s recipients=%s",
            campaign.id,
            campaign.program.id,
            len(recipients),
        )

    def _send_sms_campaign(self, campaign, users, override_preferences=False):
        if not GroupTextModule.is_configured():
            for user in users:
                EquityOutreachRecipient.objects.create(
                    campaign=campaign,
                    user=user,
                    channel=EquityOutreachCampaign.CHANNEL_SMS,
                    status=EquityOutreachRecipient.STATUS_FAILED,
                    error="Twilio is not configured for this site.",
                )
            campaign.success_count = 0
            campaign.failure_count = len(users)
            return

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        from_numbers = settings.TWILIO_ACCOUNT_NUMBERS
        number_index = 0

        success_count = 0
        failure_count = 0
        for user in users:
            contact_info = ContactInfo.objects.filter(user=user, as_user__isnull=False).order_by("-id").first()
            if not contact_info or not contact_info.phone_cell:
                EquityOutreachRecipient.objects.create(
                    campaign=campaign,
                    user=user,
                    channel=EquityOutreachCampaign.CHANNEL_SMS,
                    status=EquityOutreachRecipient.STATUS_SKIPPED,
                    error="No cell phone on file.",
                )
                continue

            if not contact_info.receive_txt_message and not override_preferences:
                EquityOutreachRecipient.objects.create(
                    campaign=campaign,
                    user=user,
                    channel=EquityOutreachCampaign.CHANNEL_SMS,
                    destination=str(contact_info.phone_cell),
                    status=EquityOutreachRecipient.STATUS_SKIPPED,
                    error="User opted out of text messages.",
                )
                continue

            destination = format_number(contact_info.phone_cell, PhoneNumberFormat.E164)
            status = EquityOutreachRecipient.STATUS_SENT
            error = ""
            try:
                client.messages.create(
                    body=strip_tags(campaign.body),
                    to=destination,
                    from_=from_numbers[number_index],
                )
                success_count += 1
            except TwilioRestException as twilio_error:
                status = EquityOutreachRecipient.STATUS_FAILED
                error = twilio_error.msg
                failure_count += 1
            except Exception as general_error:
                status = EquityOutreachRecipient.STATUS_FAILED
                error = str(general_error)
                failure_count += 1

            EquityOutreachRecipient.objects.create(
                campaign=campaign,
                user=user,
                channel=EquityOutreachCampaign.CHANNEL_SMS,
                destination=destination,
                status=status,
                error=error,
            )
            number_index = (number_index + 1) % len(from_numbers)

        campaign.success_count = success_count
        campaign.failure_count = failure_count
        logger.info(
            "Equity outreach SMS campaign completed: campaign_id=%s program=%s success=%s failure=%s override=%s",
            campaign.id,
            campaign.program.id,
            success_count,
            failure_count,
            override_preferences,
        )

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = "modules"

