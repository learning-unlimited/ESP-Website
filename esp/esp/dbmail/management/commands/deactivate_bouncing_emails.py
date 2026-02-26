import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from esp.users.models import ESPUser

logger = logging.getLogger(__name__)

# Typical hard-bounce SMTP codes or reasons from SendGrid
HARD_BOUNCE_INDICATORS = [
    "5.1.1",
    "5.2.1",
    "user unknown",
    "inactive",
    "does not exist",
    "invalid",
    "disabled"
]

class Command(BaseCommand):
    help = 'Deactivates ESPUser accounts that have hard-bounced via SendGrid'

    def handle(self, *args, **options):
        # Gracefully exit if no SendGrid API key is configured
        api_key = getattr(settings, 'SENDGRID_API_KEY', None)
        if not api_key:
            logger.info("deactivate_bouncing_emails: No SENDGRID_API_KEY found in settings. Exiting.")
            return

        try:
            from sendgrid import SendGridAPIClient
        except ImportError:
            logger.warning("deactivate_bouncing_emails: sendgrid package is not installed. Exiting.")
            return

        logger.info("deactivate_bouncing_emails: Initializing SendGrid client and fetching bounces...")
        sg = SendGridAPIClient(api_key=api_key)

        try:
            # Fetch the global suppressions (bounces) from SendGrid
            # Using limit=500 to pull recent bounces
            response = sg.client.suppression.bounces.get(query_params={'limit': 500})
            if response.status_code != 200:
                logger.error(f"deactivate_bouncing_emails: Failed to fetch bounces from SendGrid. Status: {response.status_code}")
                return
            
            bounces = response.body
            import json
            if isinstance(bounces, (bytes, bytearray)):
                bounces = json.loads(bounces.decode('utf-8'))
            elif isinstance(bounces, str):
                bounces = json.loads(bounces)
                
        except Exception as e:
            logger.exception(f"deactivate_bouncing_emails: Exception while querying SendGrid API: {e}")
            return

        if not bounces:
            logger.info("deactivate_bouncing_emails: No bounces found.")
            return

        deactivated_count = 0
        processed_emails = set()

        for bounce in bounces:
            email = bounce.get("email")
            reason = str(bounce.get("reason", "")).lower()

            if not email or email in processed_emails:
                continue
                
            processed_emails.add(email)

            # Check if this is a hard bounce (e.g. inactive account, does not exist)
            is_hard_bounce = any(indicator in reason for indicator in HARD_BOUNCE_INDICATORS)
            
            if is_hard_bounce:
                # Find associated accounts and deactivate them
                users_to_deactivate = ESPUser.objects.filter(email__iexact=email, is_active=True)
                for user in users_to_deactivate:
                    user.is_active = False
                    user.save()
                    logger.info(f"deactivate_bouncing_emails: Deactivated account {user.username} due to hard bounce: {reason}")
                    deactivated_count += 1
            else:
                logger.debug(f"deactivate_bouncing_emails: Skipped soft bounce for {email}: {reason}")

        logger.info(f"deactivate_bouncing_emails: Complete. Deactivated {deactivated_count} accounts.")
