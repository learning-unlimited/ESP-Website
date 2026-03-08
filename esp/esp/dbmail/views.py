
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
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
# Create your views here.

import base64
import json
import logging

from datetime import datetime, timezone

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from esp.dbmail.models import SendGridEvent, TextOfEmail

logger = logging.getLogger(__name__)


def _check_basic_auth(request):
    """Verify HTTP Basic Auth against SendGrid webhook credentials."""
    expected_user = getattr(settings, 'SENDGRID_WEBHOOK_USERNAME', '')
    expected_pass = getattr(settings, 'SENDGRID_WEBHOOK_PASSWORD', '')
    if not expected_user or not expected_pass:
        return False

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Basic '):
        return False

    try:
        decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
        username, password = decoded.split(':', 1)
        return username == expected_user and password == expected_pass
    except Exception:
        return False


@csrf_exempt
@require_POST
def sendgrid_webhook(request):
    """Receive and store SendGrid Event Webhook POST data.

    SendGrid sends batches of events as a JSON array in the request body.
    Authentication is via HTTP Basic Auth, configured in local_settings.py
    as SENDGRID_WEBHOOK_USERNAME and SENDGRID_WEBHOOK_PASSWORD.
    """
    if not _check_basic_auth(request):
        return HttpResponseForbidden('Invalid credentials')

    try:
        events = json.loads(request.body)
    except (ValueError, TypeError):
        logger.warning('SendGrid webhook: invalid JSON in request body')
        return HttpResponse(status=400)

    if not isinstance(events, list):
        events = [events]

    for event_data in events:
        try:
            sg_event_id = event_data.get('sg_event_id')
            if not sg_event_id:
                continue

            # Link back to TextOfEmail via unique_args injected in send()
            textofemail_id = event_data.get('textofemail_id')
            textofemail = None
            if textofemail_id:
                try:
                    textofemail = TextOfEmail.objects.get(id=int(textofemail_id))
                except (TextOfEmail.DoesNotExist, ValueError):
                    pass

            timestamp = datetime.fromtimestamp(
                event_data.get('timestamp', 0),
                tz=timezone.utc,
            )

            SendGridEvent.objects.get_or_create(
                sg_event_id=sg_event_id,
                defaults={
                    'textofemail': textofemail,
                    'email': event_data.get('email', ''),
                    'event_type': event_data.get('event', ''),
                    'timestamp': timestamp,
                    'sg_message_id': event_data.get('sg_message_id', ''),
                    'reason': event_data.get('reason', ''),
                    'response': event_data.get('response', ''),
                    'raw_event': json.dumps(event_data),
                },
            )
        except Exception:
            logger.exception(
                'SendGrid webhook: error processing event %s',
                event_data.get('sg_event_id', 'unknown')
            )

    return HttpResponse(status=200)

