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

"""
Views for the shared chapter email inbox (Issue #3831).

Provides a web UI at /manage/inbox/ for chapter administrators to view,
reply to, and manage inbound emails.
"""

import json
import logging
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.validators import validate_email
from django.db.models import Q, Max, Count
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseForbidden
from django.shortcuts import get_object_or_404

from esp.dbmail.forms import InboxReplyForm, InboxFilterForm, InboxNoteForm
from esp.dbmail.models import (
    InboundEmailThread, InboundEmail, InboundEmailAttachment,
    InboundEmailReadStatus, InboundEmailNote, InboxCannedResponse,
    InboxLabel, InboundEmailThreadLabel, send_mail,
)
from esp.users.models import admin_required, ESPUser
from esp.utils.web import render_to_response

logger = logging.getLogger(__name__)

THREADS_PER_PAGE = 25


@admin_required
def inbox(request):
    """
    GET /manage/inbox/
    List view showing all email threads with filters and pagination.
    """
    filter_form = InboxFilterForm(request.GET or None)
    threads = InboundEmailThread.objects.all()

    if filter_form.is_valid():
        q = filter_form.cleaned_data.get('q')
        status = filter_form.cleaned_data.get('status')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        mine_only = filter_form.cleaned_data.get('mine_only')

        if q:
            threads = threads.filter(
                Q(subject__icontains=q) |
                Q(emails__sender_email__icontains=q) |
                Q(emails__sender__icontains=q)
            ).distinct()
        if status:
            threads = threads.filter(status=status)
        if date_from:
            threads = threads.filter(updated_at__date__gte=date_from)
        if date_to:
            threads = threads.filter(updated_at__date__lte=date_to)
        if mine_only:
            threads = threads.filter(assigned_to=request.user)

    # Annotate with email count, prefetch labels to avoid N+1
    threads = threads.annotate(
        email_count_ann=Count('emails'),
        latest_email_date=Max('emails__received_at'),
    ).prefetch_related('thread_labels__label')

    # Get read status for current user
    read_statuses = dict(
        InboundEmailReadStatus.objects.filter(
            user=request.user,
        ).values_list('thread_id', 'read_at')
    )

    # Build thread data for template (cache latest_email to avoid N+1)
    thread_list = []
    for thread in threads:
        latest = thread.latest_email
        is_read = (thread.id in read_statuses and
                   read_statuses[thread.id] >= thread.updated_at)
        # Cache snippet to avoid extra query in template
        snippet = ''
        if latest and latest.body_text:
            snippet = re.sub(r'<[^>]+>', '', latest.body_text)[:80]
        thread_list.append({
            'thread': thread,
            'email_count': thread.email_count_ann,
            'latest_sender': latest.sender_email if latest else '',
            'snippet': snippet,
            'is_read': is_read,
        })

    # Pagination
    paginator = Paginator(thread_list, THREADS_PER_PAGE)
    page = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Stats for dashboard cards
    all_threads = InboundEmailThread.objects.all()
    stats = {
        'open': all_threads.filter(status='open').count(),
        'in_progress': all_threads.filter(status='in_progress').count(),
        'closed': all_threads.filter(status='closed').count(),
    }

    # All labels for filter/display
    all_labels = list(InboxLabel.objects.all().values('id', 'name', 'color'))

    context = {
        'filter_form': filter_form,
        'page_obj': page_obj,
        'threads': page_obj.object_list,
        'total_count': paginator.count,
        'stats': stats,
        'all_labels': json.dumps(all_labels),
    }
    return render_to_response('admin/inbox.html', request, context)


@admin_required
def inbox_thread(request, thread_id):
    """
    GET /manage/inbox/thread/<id>/ — Thread detail view.
    POST /manage/inbox/thread/<id>/ — Submit a reply.
    """
    thread = get_object_or_404(InboundEmailThread, id=thread_id)
    emails = thread.emails.select_related('replied_by').prefetch_related('attachments').all()
    reply_form = InboxReplyForm()
    reply_error = ''
    reply_success = False

    if request.method == 'POST':
        reply_form = InboxReplyForm(request.POST)
        if reply_form.is_valid():
            body = reply_form.cleaned_data['body']
            try:
                delivery_warning = _send_reply(request.user, thread, body)
                reply_success = True
                reply_form = InboxReplyForm()
                emails = thread.emails.select_related('replied_by').prefetch_related('attachments').all()
                if delivery_warning:
                    reply_error = delivery_warning
            except Exception as e:
                logger.error("Failed to send reply for thread %d: %s", thread.id, e)
                reply_error = 'Failed to send reply: %s' % str(e)

    # Get admin users for assignment dropdown
    from django.contrib.auth.models import Group
    admin_group = Group.objects.filter(name='Administrator').first()
    admin_users = ESPUser.objects.filter(groups=admin_group) if admin_group else ESPUser.objects.none()

    # Notes, labels, canned responses for enhanced UI
    notes = thread.notes.select_related('created_by').all()
    note_form = InboxNoteForm()
    thread_labels = thread.thread_labels.select_related('label').all()
    all_labels = list(InboxLabel.objects.all().values('id', 'name', 'color'))
    canned_responses = list(
        InboxCannedResponse.objects.filter(is_active=True).values('id', 'title', 'body')
    )

    # Build combined timeline (emails + notes) sorted by date
    timeline = []
    for e in emails:
        timeline.append({'type': 'email', 'obj': e, 'date': e.received_at})
    for n in notes:
        timeline.append({'type': 'note', 'obj': n, 'date': n.created_at})
    timeline.sort(key=lambda x: x['date'])

    # Reply-to address
    latest_inbound = thread.emails.filter(is_outbound_reply=False).order_by('-received_at').first()
    reply_to_email = latest_inbound.sender_email if latest_inbound else ''

    context = {
        'thread': thread,
        'emails': emails,
        'timeline': timeline,
        'notes': notes,
        'note_form': note_form,
        'reply_form': reply_form,
        'reply_error': reply_error,
        'reply_success': reply_success,
        'reply_to_email': reply_to_email,
        'admin_users': admin_users,
        'thread_labels': thread_labels,
        'all_labels_json': json.dumps(all_labels),
        'canned_responses_json': json.dumps(canned_responses),
    }
    return render_to_response('admin/inbox_thread.html', request, context)


@admin_required
def inbox_mark_read(request, thread_id):
    """
    POST /manage/inbox/thread/<id>/mark-read/
    AJAX endpoint to mark a thread as read for the current user.
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    thread = get_object_or_404(InboundEmailThread, id=thread_id)
    InboundEmailReadStatus.objects.update_or_create(
        user=request.user,
        thread=thread,
        defaults={},
    )
    return HttpResponse(
        json.dumps({'status': 'ok'}),
        content_type='application/json',
    )


@admin_required
def inbox_update_thread(request, thread_id):
    """
    POST /manage/inbox/thread/<id>/update/
    AJAX endpoint to update thread status or assignment.
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    thread = get_object_or_404(InboundEmailThread, id=thread_id)

    new_status = request.POST.get('status')
    assigned_to_id = request.POST.get('assigned_to')

    if new_status and new_status in dict(InboundEmailThread.STATUS_CHOICES):
        thread.status = new_status

    if assigned_to_id is not None:
        if assigned_to_id == '' or assigned_to_id == '0':
            thread.assigned_to = None
        elif assigned_to_id == 'self':
            thread.assigned_to = request.user
        else:
            try:
                thread.assigned_to = ESPUser.objects.get(id=int(assigned_to_id))
            except (ESPUser.DoesNotExist, ValueError):
                return HttpResponse(
                    json.dumps({'status': 'error', 'message': 'User not found'}),
                    content_type='application/json',
                    status=400,
                )

    thread.save()

    return HttpResponse(
        json.dumps({
            'status': 'ok',
            'thread_status': thread.status,
            'assigned_to': thread.assigned_to.username if thread.assigned_to else None,
        }),
        content_type='application/json',
    )


@admin_required
def inbox_attachment(request, attachment_id):
    """
    GET /manage/inbox/attachment/<id>/
    Serve an attachment file with Content-Disposition: attachment.
    """
    attachment = get_object_or_404(InboundEmailAttachment, id=attachment_id)
    response = HttpResponse(attachment.file.read(), content_type=attachment.content_type)
    response['Content-Disposition'] = 'attachment; filename="%s"' % attachment.filename
    return response


@admin_required
def inbox_add_note(request, thread_id):
    """POST /manage/inbox/thread/<id>/note/ — Add internal note to thread."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    thread = get_object_or_404(InboundEmailThread, id=thread_id)
    note_text = request.POST.get('note_text', '').strip()
    if not note_text:
        return HttpResponse(
            json.dumps({'status': 'error', 'message': 'Note text is required'}),
            content_type='application/json', status=400,
        )

    note = InboundEmailNote.objects.create(
        thread=thread,
        note_text=note_text,
        created_by=request.user,
    )
    return HttpResponse(
        json.dumps({
            'status': 'ok',
            'note': {
                'id': note.id,
                'note_text': note.note_text,
                'created_by': request.user.username,
                'created_at': note.created_at.strftime('%b %d, %Y %I:%M %p'),
            },
        }),
        content_type='application/json',
    )


@admin_required
def inbox_delete_note(request, note_id):
    """POST /manage/inbox/note/<id>/delete/ — Delete a note (creator or superuser only)."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    note = get_object_or_404(InboundEmailNote, id=note_id)
    if note.created_by_id != request.user.id and not request.user.is_superuser:
        return HttpResponseForbidden(
            json.dumps({'status': 'error', 'message': 'Permission denied'}),
            content_type='application/json',
        )

    note.delete()
    return HttpResponse(
        json.dumps({'status': 'ok'}),
        content_type='application/json',
    )


@admin_required
def inbox_get_canned_responses(request):
    """GET /manage/inbox/canned-responses/ — Return active canned responses as JSON."""
    responses = list(
        InboxCannedResponse.objects.filter(is_active=True).values('id', 'title', 'body')
    )
    return HttpResponse(
        json.dumps({'status': 'ok', 'responses': responses}),
        content_type='application/json',
    )


@admin_required
def inbox_bulk_action(request):
    """POST /manage/inbox/bulk/ — Bulk close or assign threads."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    action = request.POST.get('action', '')
    thread_ids = request.POST.getlist('thread_ids[]')
    if not thread_ids:
        thread_ids = request.POST.getlist('thread_ids')

    if not thread_ids or not action:
        return HttpResponse(
            json.dumps({'status': 'error', 'message': 'Missing action or thread_ids'}),
            content_type='application/json', status=400,
        )

    try:
        thread_ids = [int(tid) for tid in thread_ids]
    except (ValueError, TypeError):
        return HttpResponse(
            json.dumps({'status': 'error', 'message': 'Invalid thread IDs'}),
            content_type='application/json', status=400,
        )

    threads = InboundEmailThread.objects.filter(id__in=thread_ids)
    updated = 0

    if action == 'close':
        updated = threads.update(status='closed')
    elif action == 'assign_me':
        updated = threads.update(assigned_to=request.user, status='in_progress')
    elif action == 'open':
        updated = threads.update(status='open')
    else:
        return HttpResponse(
            json.dumps({'status': 'error', 'message': 'Unknown action: %s' % action}),
            content_type='application/json', status=400,
        )

    return HttpResponse(
        json.dumps({'status': 'ok', 'updated': updated}),
        content_type='application/json',
    )


@admin_required
def inbox_manage_labels(request, thread_id):
    """POST /manage/inbox/thread/<id>/labels/ — Add or remove a label on a thread."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    thread = get_object_or_404(InboundEmailThread, id=thread_id)
    action = request.POST.get('action', '')
    label_id = request.POST.get('label_id', '')

    if not label_id or not action:
        return HttpResponse(
            json.dumps({'status': 'error', 'message': 'Missing action or label_id'}),
            content_type='application/json', status=400,
        )

    try:
        label = InboxLabel.objects.get(id=int(label_id))
    except (InboxLabel.DoesNotExist, ValueError):
        return HttpResponse(
            json.dumps({'status': 'error', 'message': 'Label not found'}),
            content_type='application/json', status=404,
        )

    if action == 'add':
        InboundEmailThreadLabel.objects.get_or_create(
            thread=thread, label=label,
            defaults={'added_by': request.user},
        )
    elif action == 'remove':
        InboundEmailThreadLabel.objects.filter(thread=thread, label=label).delete()
    else:
        return HttpResponse(
            json.dumps({'status': 'error', 'message': 'Unknown action'}),
            content_type='application/json', status=400,
        )

    # Return updated labels for this thread
    labels = list(thread.thread_labels.select_related('label').values(
        'label__id', 'label__name', 'label__color',
    ))
    return HttpResponse(
        json.dumps({'status': 'ok', 'labels': labels}),
        content_type='application/json',
    )


@admin_required
def inbox_get_labels(request):
    """GET /manage/inbox/labels/ — Return all labels as JSON."""
    labels = list(InboxLabel.objects.all().values('id', 'name', 'color', 'description'))
    return HttpResponse(
        json.dumps({'status': 'ok', 'labels': labels}),
        content_type='application/json',
    )


@admin_required
def inbox_stats(request):
    """GET /manage/inbox/stats/ — Return thread counts by status as JSON."""
    all_threads = InboundEmailThread.objects.all()
    stats = {
        'open': all_threads.filter(status='open').count(),
        'in_progress': all_threads.filter(status='in_progress').count(),
        'closed': all_threads.filter(status='closed').count(),
    }
    return HttpResponse(
        json.dumps({'status': 'ok', 'stats': stats}),
        content_type='application/json',
    )


@admin_required
def inbox_export_pdf(request, thread_id):
    """GET /manage/inbox/thread/<id>/export/ — Export thread as downloadable text file."""
    thread = get_object_or_404(InboundEmailThread, id=thread_id)
    emails = thread.emails.select_related('replied_by').prefetch_related(
        'attachments',
    ).order_by('received_at')
    notes = thread.notes.select_related('created_by').order_by('created_at')

    lines = []
    lines.append('=' * 60)
    lines.append('Thread: %s' % thread.subject)
    lines.append('Status: %s | Assigned to: %s' % (
        thread.get_status_display(),
        thread.assigned_to.username if thread.assigned_to else 'Unassigned',
    ))
    lines.append('Created: %s | Updated: %s' % (
        thread.created_at.strftime('%Y-%m-%d %H:%M'),
        thread.updated_at.strftime('%Y-%m-%d %H:%M'),
    ))
    labels = thread.labels
    if labels.exists():
        lines.append('Labels: %s' % ', '.join(l.name for l in labels))
    lines.append('=' * 60)
    lines.append('')

    for e in emails:
        direction = '[SENT]' if e.is_outbound_reply else '[RECEIVED]'
        lines.append('-' * 40)
        lines.append('%s %s' % (direction, e.received_at.strftime('%Y-%m-%d %H:%M')))
        lines.append('From: %s' % e.sender)
        lines.append('To: %s' % e.recipient)
        lines.append('Subject: %s' % e.subject)
        if e.is_outbound_reply and e.replied_by:
            lines.append('Sent by: %s' % e.replied_by.username)
        lines.append('')
        lines.append(e.body_text or '(No text content)')
        # List attachments so attachment-only emails aren't blank
        attachments = e.attachments.all()
        if attachments:
            lines.append('')
            for att in attachments:
                lines.append('[Attachment: %s (%s)]' % (att.filename, att.content_type))
        lines.append('')

    if notes.exists():
        lines.append('=' * 60)
        lines.append('INTERNAL NOTES')
        lines.append('=' * 60)
        for n in notes:
            lines.append('')
            lines.append('[%s] %s:' % (
                n.created_at.strftime('%Y-%m-%d %H:%M'),
                n.created_by.username,
            ))
            lines.append(n.note_text)

    content = '\n'.join(lines)
    # Sanitize filename: strip non-alphanumeric chars (except underscore/hyphen)
    safe_subject = re.sub(r'[^\w\-]', '_', thread.subject[:30]).strip('_')
    if not safe_subject:
        safe_subject = 'thread'
    filename = 'thread-%d-%s.txt' % (thread.id, safe_subject)

    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response


@admin_required
def inbox_forward_thread(request, thread_id):
    """POST /manage/inbox/thread/<id>/forward/ — Forward thread summary via email."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    thread = get_object_or_404(InboundEmailThread, id=thread_id)
    forward_to = request.POST.get('email', '').strip()

    if not forward_to:
        return HttpResponse(
            json.dumps({'status': 'error', 'message': 'Email address is required'}),
            content_type='application/json', status=400,
        )
    try:
        validate_email(forward_to)
    except ValidationError:
        return HttpResponse(
            json.dumps({'status': 'error', 'message': 'Valid email address required'}),
            content_type='application/json', status=400,
        )

    # Build thread summary (cap at ~500KB to avoid MTA size limits)
    MAX_FORWARD_SIZE = 500000  # ~500KB text limit
    emails = thread.emails.prefetch_related('attachments').order_by('received_at')
    parts = []
    parts.append('Thread: %s' % thread.subject)
    parts.append('Status: %s' % thread.get_status_display())
    parts.append('Forwarded by: %s' % request.user.username)
    parts.append('')

    for e in emails:
        direction = '[SENT]' if e.is_outbound_reply else '[RECEIVED]'
        block = []
        block.append('--- %s %s ---' % (direction, e.received_at.strftime('%Y-%m-%d %H:%M')))
        block.append('From: %s' % e.sender)
        block.append('To: %s' % e.recipient)
        block.append('')
        block.append(e.body_text or '(No text content)')
        attachments = e.attachments.all()
        if attachments:
            block.append('')
            for att in attachments:
                block.append('[Attachment: %s]' % att.filename)
        block.append('')
        block_text = '\n'.join(block)
        if sum(len(p) for p in parts) + len(block_text) > MAX_FORWARD_SIZE:
            parts.append('\n[... Thread truncated due to length ...]')
            break
        parts.extend(block)

    body = '\n'.join(parts)
    subject = 'Fwd: %s' % thread.subject

    try:
        domain = settings.SITE_INFO[1]
    except (AttributeError, IndexError):
        domain = 'localhost'
    org_name = getattr(settings, 'ORGANIZATION_SHORT_NAME', 'ESP')
    from_email = '%s <info@%s>' % (org_name, domain)

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[forward_to],
        )
    except Exception as e:
        logger.error("Failed to forward thread %d to %s: %s", thread.id, forward_to, e)
        return HttpResponse(
            json.dumps({'status': 'error', 'message': 'Failed to send: %s' % str(e)}),
            content_type='application/json', status=500,
        )

    logger.info("Thread %d forwarded to %s by %s", thread.id, forward_to, request.user.username)
    return HttpResponse(
        json.dumps({'status': 'ok', 'message': 'Thread forwarded to %s' % forward_to}),
        content_type='application/json',
    )


def _send_reply(user, thread, body):
    """Send a reply email for a thread and record it in the inbox.

    Records the outbound email in the database regardless of whether the
    actual email delivery succeeds. This ensures the conversation is tracked
    even if the SMTP server is unavailable (e.g. dev environments).

    Returns a tuple (success, warning) where warning is a message string
    if the email could not be delivered, or empty string on success.
    """
    from uuid import uuid4

    latest = thread.emails.filter(is_outbound_reply=False).order_by('-received_at').first()
    if not latest:
        latest = thread.emails.order_by('-received_at').first()
    if not latest:
        raise ValueError("Thread has no emails to reply to")

    in_reply_to = latest.message_id
    refs = latest.references.strip()
    references = (refs + ' ' + latest.message_id) if refs else latest.message_id

    subject = thread.subject
    if not subject.lower().startswith('re:'):
        subject = 'Re: ' + subject

    try:
        domain = settings.SITE_INFO[1]
    except (AttributeError, IndexError):
        domain = 'localhost'
    org_name = getattr(settings, 'ORGANIZATION_SHORT_NAME', 'ESP')
    from_email = '%s <info@%s>' % (org_name, domain)
    to_email = latest.sender_email
    message_id = '<reply-%s@%s>' % (uuid4().hex, domain)

    extra_headers = {
        'In-Reply-To': in_reply_to,
        'References': references,
    }

    # Attempt to send the email; record the reply in DB regardless.
    delivery_warning = ''
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[to_email],
            extra_headers=extra_headers,
        )
    except Exception as e:
        logger.warning("Email delivery failed for thread %d (reply still recorded): %s", thread.id, e)
        delivery_warning = 'Reply recorded but email delivery failed: %s' % str(e)

    InboundEmail.objects.create(
        thread=thread,
        message_id=message_id,
        in_reply_to=in_reply_to,
        references=references,
        sender=from_email,
        sender_email='info@%s' % domain,
        recipient=to_email,
        subject=subject,
        body_text=body,
        is_outbound_reply=True,
        replied_by=user,
    )

    if thread.status == 'closed':
        thread.status = 'in_progress'
        InboundEmailNote.objects.create(
            thread=thread,
            note_text='Thread automatically re-opened due to admin reply.',
            created_by=user,
        )
    elif thread.status == 'open':
        thread.status = 'in_progress'
    thread.save()

    logger.info("Sent reply to %s for thread %d by %s", to_email, thread.id, user.username)
    return delivery_warning
