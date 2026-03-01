"""
Inbound email storage and threading for the mailgate system (Issue #3831).

This module captures inbound emails processed by mailgate.py and stores them
in the database for the shared chapter inbox UI at /manage/inbox/.
"""

import email.utils
import logging
import re
from datetime import datetime, timedelta
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction

logger = logging.getLogger('esp.mailgate')

# Size limits
MAX_BODY_SIZE = 1 * 1024 * 1024    # 1 MB
MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024  # 25 MB

# Subject normalization: strip a single Re:/Fwd:/FW:/Fw: prefix per pass
# to avoid nested quantifiers that can cause catastrophic backtracking.
_SUBJECT_PREFIX_RE = re.compile(r'^\s*(Re|Fwd|FW|Fw)\s*:\s*', re.IGNORECASE)

# Unicode bidirectional control characters (RLO, LRO, RLE, LRE, PDF, etc.)
_BIDI_CONTROL_RE = re.compile(u'[\u200e\u200f\u202a-\u202e\u2066-\u2069]')


def strip_bidi_chars(text):
    """Strip Unicode bidirectional control characters that can break UI layout."""
    if not text:
        return text
    return _BIDI_CONTROL_RE.sub('', text)


def extract_sender(message):
    """Safely extract sender email from a message's From header.

    Returns a tuple of (full_from_header, email_address).
    """
    from_header = message.get('From', '')
    _, addr = email.utils.parseaddr(from_header)
    return from_header, addr.strip().lower() if addr else ''


def normalize_subject(subject):
    """Strip Re:/Fwd:/FW: prefixes and whitespace for threading comparison."""
    if not subject:
        return ''
    # Strip one prefix per iteration to avoid nested-quantifier ReDoS
    prev = None
    while subject != prev:
        prev = subject
        subject = _SUBJECT_PREFIX_RE.sub('', subject, count=1)
    return subject.strip()


def extract_body_parts(message):
    """Walk MIME tree and extract text body, HTML body, and attachments.

    Returns (text_body, html_body, attachments_list) where attachments_list
    contains dicts with keys: filename, content_type, data, size.
    """
    text_body = ''
    html_body = ''
    attachments = []

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = str(part.get('Content-Disposition', ''))

            if content_type == 'text/plain' and 'attachment' not in disposition:
                # Check encoded size before decoding to limit memory use
                raw = part.get_payload()
                if isinstance(raw, str) and len(raw) > MAX_BODY_SIZE * 2:
                    text_body += raw[:MAX_BODY_SIZE].encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                    text_body += '\n\n[Content truncated]'
                else:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        text_body += payload.decode(charset, errors='replace')
            elif content_type == 'text/html' and 'attachment' not in disposition:
                raw = part.get_payload()
                if isinstance(raw, str) and len(raw) > MAX_BODY_SIZE * 2:
                    html_body += raw[:MAX_BODY_SIZE].encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                    html_body += '\n\n<!-- Content truncated -->'
                else:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        html_body += payload.decode(charset, errors='replace')
            elif disposition and 'attachment' in disposition:
                # Check encoded size before decoding
                raw = part.get_payload()
                raw_size = len(raw) if isinstance(raw, str) else 0
                if raw_size > MAX_ATTACHMENT_SIZE * 2:
                    logger.warning("Skipping attachment '%s' (encoded ~%d bytes > limit)",
                                   part.get_filename(), raw_size)
                    continue
                payload = part.get_payload(decode=True)
                if payload and len(payload) <= MAX_ATTACHMENT_SIZE:
                    attachments.append({
                        'filename': part.get_filename() or 'unnamed',
                        'content_type': content_type,
                        'data': payload,
                        'size': len(payload),
                    })
                elif payload:
                    logger.warning("Skipping attachment '%s' (%d bytes > %d limit)",
                                   part.get_filename(), len(payload), MAX_ATTACHMENT_SIZE)
    else:
        payload = message.get_payload(decode=True)
        if payload:
            charset = message.get_content_charset() or 'utf-8'
            decoded = payload.decode(charset, errors='replace')
            if message.get_content_type() == 'text/html':
                html_body = decoded
            else:
                text_body = decoded

    # Truncate oversized bodies
    if len(text_body) > MAX_BODY_SIZE:
        text_body = text_body[:MAX_BODY_SIZE] + '\n\n[Content truncated]'
    if len(html_body) > MAX_BODY_SIZE:
        html_body = html_body[:MAX_BODY_SIZE] + '\n\n<!-- Content truncated -->'

    return text_body, html_body, attachments


def extract_raw_headers(message):
    """Extract a string representation of all headers for archival."""
    headers = []
    for key, value in message.items():
        headers.append('%s: %s' % (key, value))
    return '\n'.join(headers)


def find_or_create_thread(message_id, in_reply_to, references, subject):
    """Find an existing thread or create a new one based on threading headers.

    Threading algorithm:
    1. If In-Reply-To is set, find InboundEmail with that message_id and use its thread.
    2. Otherwise, parse References (space-separated), iterate in reverse, find any match.
    3. Otherwise, normalize subject and look for a thread with matching subject from last 30 days.
    4. Otherwise, create a new InboundEmailThread.
    """
    from esp.dbmail.models import InboundEmail, InboundEmailThread

    # 1. Try In-Reply-To
    if in_reply_to:
        try:
            parent = InboundEmail.objects.get(message_id=in_reply_to)
            if parent.thread:
                # Touch updated_at
                parent.thread.save()
                return parent.thread
        except InboundEmail.DoesNotExist:
            pass

    # 2. Try References (space-separated, iterate reverse for most recent)
    if references:
        ref_ids = references.strip().split()
        for ref_id in reversed(ref_ids):
            ref_id = ref_id.strip()
            if not ref_id:
                continue
            try:
                parent = InboundEmail.objects.get(message_id=ref_id)
                if parent.thread:
                    parent.thread.save()
                    return parent.thread
            except InboundEmail.DoesNotExist:
                continue

    # 3. Try subject-based matching (last 30 days)
    normalized = normalize_subject(subject)
    if normalized:
        cutoff = datetime.now() - timedelta(days=30)
        # Look for threads where the normalized subject matches
        threads = InboundEmailThread.objects.filter(
            created_at__gte=cutoff,
        ).order_by('-updated_at')
        for thread in threads[:50]:  # Limit search to avoid scanning everything
            if normalize_subject(thread.subject) == normalized:
                thread.save()  # Touch updated_at
                return thread

    # 4. Create new thread
    return InboundEmailThread.objects.create(
        subject=subject or '(No Subject)',
    )


def store_inbound_email(local_part, message):
    """Store an inbound email in the database for the inbox UI.

    This is called by mailgate.py after parsing the email but before forwarding.
    It is wrapped in try/except in mailgate.py so failures never block delivery.

    Args:
        local_part: The LOCAL_PART from the envelope (the address before @)
        message: A parsed email.message.Message object
    """
    from esp.dbmail.models import InboundEmail, InboundEmailAttachment

    # Extract sender
    from_header, sender_email = extract_sender(message)
    if not sender_email:
        logger.warning("No sender email found, skipping inbox storage")
        return None

    # Extract Message-ID (generate if missing)
    message_id = message.get('Message-ID', '').strip()
    if not message_id:
        try:
            domain = settings.SITE_INFO[1]
        except (AttributeError, IndexError):
            domain = 'localhost'
        message_id = '<generated-%s@%s>' % (uuid4().hex, domain)

    # Extract threading headers
    in_reply_to = message.get('In-Reply-To', '').strip()
    references = message.get('References', '').strip()

    # Extract subject — strip bidi control chars to prevent UI layout attacks,
    # strip null bytes (PostgreSQL rejects them), and truncate to fit DB field
    subject = strip_bidi_chars(message.get('Subject', '').strip()) or '(No Subject)'
    subject = subject.replace('\x00', '')[:998]

    # Sanitize sender display name (bidi chars and null bytes in From header)
    from_header = strip_bidi_chars(from_header)
    from_header = from_header.replace('\x00', '') if from_header else from_header

    # Extract body parts and attachments
    text_body, html_body, attachment_data = extract_body_parts(message)

    # Extract raw headers for archival
    raw_headers = extract_raw_headers(message)

    # Strip null bytes from all text fields — PostgreSQL rejects \x00
    def _strip_nul(s):
        return s.replace('\x00', '') if s and '\x00' in s else s

    text_body = _strip_nul(text_body)
    html_body = _strip_nul(html_body)
    raw_headers = _strip_nul(raw_headers)
    in_reply_to = _strip_nul(in_reply_to)
    references = _strip_nul(references)
    message_id = _strip_nul(message_id)
    sender_email = _strip_nul(sender_email)

    # Find or create thread
    thread = find_or_create_thread(message_id, in_reply_to, references, subject)

    # Create InboundEmail record (handle duplicate message_id gracefully)
    # Use a savepoint so IntegrityError doesn't break the outer transaction
    try:
        with transaction.atomic():
            inbound = InboundEmail.objects.create(
                thread=thread,
                message_id=message_id,
                in_reply_to=in_reply_to,
                references=references,
                sender=from_header,
                sender_email=sender_email,
                recipient=local_part,
                subject=subject,
                body_text=text_body,
                body_html=html_body,
                raw_headers=raw_headers,
            )
    except IntegrityError:
        logger.warning("Duplicate message_id '%s', skipping storage", message_id)
        return None

    # Save attachments
    for att in attachment_data:
        try:
            attachment = InboundEmailAttachment(
                email=inbound,
                filename=att['filename'][:255],
                content_type=att['content_type'][:255],
                size=att['size'],
            )
            attachment.file.save(
                att['filename'][:255],
                ContentFile(att['data']),
                save=False,
            )
            attachment.save()
        except Exception as e:
            logger.warning("Failed to save attachment '%s': %s", att['filename'], e)

    logger.info("Stored inbound email '%s' from %s in thread %d",
                subject, sender_email, thread.id)
    return inbound
