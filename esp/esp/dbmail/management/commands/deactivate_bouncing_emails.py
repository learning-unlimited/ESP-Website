import logging
import time
import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from esp.dbmail.models import EmailBounceRecord
from esp.tagdict.models import Tag

try:
    from sendgrid import SendGridAPIClient
except ImportError:
    SendGridAPIClient = None

logger = logging.getLogger('esp.dbmail_cron.bounces')

class Command(BaseCommand):
    help = 'Fetches hard bounces from SendGrid and disables emailing for those addresses'

    def handle(self, *args, **options):
        api_key = getattr(settings, 'SENDGRID_API_KEY', None)
        if not api_key or not SendGridAPIClient:
            logger.info("SENDGRID_API_KEY not configured or sendgrid package not installed. Skipping bounce polling.")
            return

        sg = SendGridAPIClient(api_key)

        # Default to checking the last 7 days if no tag is set
        default_start = int((datetime.now() - timedelta(days=7)).timestamp())
        last_poll_str = Tag.getTag('last_sendgrid_bounce_poll_time', default=str(default_start))
        
        try:
            start_time = int(last_poll_str)
        except (ValueError, TypeError):
            start_time = default_start

        current_time = int(time.time())

        # Poll SendGrid API
        try:
            response = sg.client.suppression.bounces.get(query_params={'start_time': start_time})
        except Exception as e:
            logger.error(f"Failed to fetch bounces from SendGrid: {e}")
            return

        if response.status_code != 200:
            logger.error(f"SendGrid API returned status {response.status_code}")
            return
            
        try:
            bounces = json.loads(response.body)
        except Exception:
            bounces = []

        if not isinstance(bounces, list):
            logger.error("SendGrid API returned unexpected format.")
            return

        for bounce in bounces:
            email = bounce.get('email')
            status = str(bounce.get('status', ''))
            reason = str(bounce.get('reason', ''))
            
            if not email:
                continue
                
            # Filter for hard bounces (status codes starting with 5)
            if status.startswith('5') or '5.' in status or 'does not exist' in reason.lower() or 'invalid' in reason.lower() or 'inactive' in reason.lower():
                record, created = EmailBounceRecord.objects.get_or_create(email=email)
                if not created:
                    record.bounce_count += 1
                
                bounce_timestamp = bounce.get('created')
                if bounce_timestamp:
                    record.last_bounced_at = datetime.fromtimestamp(bounce_timestamp)
                else:
                    record.last_bounced_at = datetime.now()
                
                record.status_code = status[:10]
                record.reason = reason
                record.disabled = True
                record.save()
                
        # Update the tag
        Tag.setTag('last_sendgrid_bounce_poll_time', value=str(current_time))
        logger.info(f"Processed {len(bounces)} bounces from SendGrid.")
