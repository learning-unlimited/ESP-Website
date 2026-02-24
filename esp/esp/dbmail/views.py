
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

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from esp.dbmail.models import MessageRequest, send_mail
from esp.users.models import ESPUser


@login_required
def preview_email(request, message_request_id):
    """
    Preview how an email will look before sending to all recipients.
    Shows the email rendered with a sample user's data.
    """
    msg_req = get_object_or_404(MessageRequest, id=message_request_id)
    
    # Get a sample user from the recipients list
    recipients = msg_req.recipients.getList(ESPUser)
    sample_user = recipients.first() if recipients.exists() else request.user
    
    # Render the email template with sample user data
    subject = msg_req.parseSmartText(msg_req.subject, sample_user)
    msgtext = msg_req.parseSmartText(msg_req.msgtext, sample_user)
    
    # Determine sender
    if msg_req.sender and len(msg_req.sender.strip()) > 0:
        send_from = msg_req.sender
    elif msg_req.creator:
        send_from = msg_req.creator.get_email_sendto_address()
    else:
        send_from = 'ESP Web Site <esp@mit.edu>'
    
    context = {
        'msg_req': msg_req,
        'subject': subject,
        'msgtext': msgtext,
        'send_from': send_from,
        'sample_user': sample_user,
        'recipient_count': recipients.count(),
    }
    
    return render(request, 'dbmail/preview_email.html', context)


@login_required
def send_test_email(request, message_request_id):
    """
    Send a test email to the logged-in admin's email address.
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('preview_email', message_request_id=message_request_id)
    
    msg_req = get_object_or_404(MessageRequest, id=message_request_id)
    admin_user = request.user
    
    # Render email with admin's data
    subject = msg_req.parseSmartText(msg_req.subject, admin_user)
    msgtext = msg_req.parseSmartText(msg_req.msgtext, admin_user)
    
    # Determine sender
    if msg_req.sender and len(msg_req.sender.strip()) > 0:
        send_from = msg_req.sender
    elif msg_req.creator:
        send_from = msg_req.creator.get_email_sendto_address()
    else:
        send_from = 'ESP Web Site <esp@mit.edu>'
    
    try:
        # Send test email
        send_mail(
            subject=subject,
            message=msgtext,
            from_email=send_from,
            recipient_list=[admin_user.email],
            fail_silently=False,
            extra_headers=msg_req.special_headers_dict,
            user=admin_user
        )
        messages.success(request, f'Test email sent successfully to {admin_user.email}')
    except Exception as e:
        messages.error(request, f'Failed to send test email: {str(e)}')
    
    return redirect('preview_email', message_request_id=message_request_id)
