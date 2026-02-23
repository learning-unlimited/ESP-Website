"""
Views for the shared chapter email inbox (Issue #3831).

Provides a web UI at /manage/inbox/ for chapter administrators to view,
reply to, and manage inbound emails.
"""

import json
import logging
import re

from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Max, Count
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404

from esp.dbmail.forms import InboxReplyForm, InboxFilterForm
from esp.dbmail.models import (
    InboundEmailThread, InboundEmail, InboundEmailAttachment,
    InboundEmailReadStatus, send_mail,
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

    # Annotate with email count
    threads = threads.annotate(
        email_count_ann=Count('emails'),
        latest_email_date=Max('emails__received_at'),
    )

    # Get read status for current user
    read_statuses = dict(
        InboundEmailReadStatus.objects.filter(
            user=request.user,
        ).values_list('thread_id', 'read_at')
    )

    # Build thread data for template
    thread_list = []
    for thread in threads:
        latest = thread.latest_email
        is_read = (thread.id in read_statuses and
                   read_statuses[thread.id] >= thread.updated_at)
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

    context = {
        'filter_form': filter_form,
        'page_obj': page_obj,
        'threads': page_obj.object_list,
        'total_count': paginator.count,
        'stats': stats,
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

    # Reply-to address
    latest_inbound = thread.emails.filter(is_outbound_reply=False).order_by('-received_at').first()
    reply_to_email = latest_inbound.sender_email if latest_inbound else ''

    context = {
        'thread': thread,
        'emails': emails,
        'reply_form': reply_form,
        'reply_error': reply_error,
        'reply_success': reply_success,
        'reply_to_email': reply_to_email,
        'admin_users': admin_users,
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


def _send_reply(user, thread, body):
    """Send a reply email for a thread and record it in the inbox.

    Records the outbound email in the database regardless of whether the
    actual email delivery succeeds. This ensures the conversation is tracked
    even if the SMTP server is unavailable (e.g. dev environments).

    Returns a warning message string if delivery failed, or empty string on success.
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

    # Update thread status (no notes in core — just change status)
    if thread.status == 'open' or thread.status == 'closed':
        thread.status = 'in_progress'
    thread.save()

    logger.info("Sent reply to %s for thread %d by %s", to_email, thread.id, user.username)
    return delivery_warning
