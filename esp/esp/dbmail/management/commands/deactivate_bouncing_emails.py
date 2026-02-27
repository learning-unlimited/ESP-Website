
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2025 by the individual contributors
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

import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from esp.users.models import ESPUser

logger = logging.getLogger(__name__)

# Typical exact string matches for permanent failures, 
# although we heavily rely on the 5.x.x status code
HARD_BOUNCE_INDICATORS = [
    "user unknown",
    "inactive",
    "does not exist"
]

class Command(BaseCommand):
    help = 'Deactivates ESPUser accounts that have hard-bounced via SendGrid'

    @transaction.atomic
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
            status = str(bounce.get("status", "")).strip()

            if not email or email in processed_emails:
                continue
                
            processed_emails.add(email)

            # A 5.x.x status code is an explicit permanent failure (hard bounce).
            # Also fall back to strict exact wording if status is missing.
            is_hard_bounce = status.startswith("5.") or any(
                indicator in reason for indicator in HARD_BOUNCE_INDICATORS
            )
            
            if is_hard_bounce:
                # Find associated accounts and deactivate them using a bulk update
                users_to_deactivate = ESPUser.objects.filter(email__iexact=email, is_active=True)
                usernames = list(users_to_deactivate.values_list("username", flat=True))
                
                updated_count = users_to_deactivate.update(is_active=False)
                for username in usernames:
                    logger.info(f"deactivate_bouncing_emails: Deactivated account {username} due to hard bounce: [{status}] {reason}")
                deactivated_count += updated_count
            else:
                logger.debug(f"deactivate_bouncing_emails: Skipped soft bounce for {email}: [{status}] {reason}")

            # Delete the bounce from SendGrid's suppression list so we process the next batch safely
            try:
                sg.client.suppression.bounces._(email).delete()
            except Exception as e:
                logger.warning(f"deactivate_bouncing_emails: Failed to clear bounce for {email} from SendGrid: {e}")

        logger.info(f"deactivate_bouncing_emails: Complete. Deactivated {deactivated_count} accounts.")

