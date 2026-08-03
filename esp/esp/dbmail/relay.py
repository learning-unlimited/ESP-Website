"""
Email relay helpers for learningu.org alias resolution and sender selection.

Used by mailgates and unit-tested directly. Keep this module free of import-time
side effects so tests can import it under Django's test settings.
"""

import itertools
import logging

from django.conf import settings
from django.db.models.functions import Lower

from esp.dbmail.models import PlainRedirect
from esp.users.models import ESPUser

logger = logging.getLogger(__name__)

LEARNINGU_DOMAIN = '.learningu.org'
FORWARDER_HEADER = 'X-Forwarded-By: lu-forwarder'

# When multiple accounts share one email, prefer the highest-privilege role.
SENDER_GROUP_PRIORITY = (
    'Administrator',
    'Teacher',
    'Volunteer',
    'Student',
    'Educator',
)


def split_recipients(raw_recipients):
    """
    Partition recipient strings into external addresses, learningu.org aliases,
    and invalid values (no '@').
    """
    external_addrs = []
    aliases = []
    invalid = []
    for addr in raw_recipients:
        if not addr:
            invalid.append(addr)
            continue
        if addr.endswith(LEARNINGU_DOMAIN):
            aliases.append(addr)
        elif '@' in addr:
            external_addrs.append(addr)
        else:
            invalid.append(addr)
    return external_addrs, aliases, invalid


def resolve_aliases_via_plain_redirect(aliases):
    """
    Expand PlainRedirect destinations for alias local-parts.

    Comma-separated destinations are expanded. Destinations that still end in
    LEARNINGU_DOMAIN are dropped to avoid internal loops.
    """
    if not aliases:
        return []
    local_parts = [a.split('@')[0].lower() for a in aliases]
    redirects = (
        PlainRedirect.objects
        .annotate(original_lower=Lower('original'))
        .filter(original_lower__in=local_parts)
        .exclude(destination__isnull=True)
        .exclude(destination='')
    )
    expanded = list(itertools.chain.from_iterable(
        r.destination.split(',') for r in redirects
    ))
    return [addr.strip() for addr in expanded
            if addr.strip() and not addr.strip().endswith(LEARNINGU_DOMAIN)]


def resolve_aliases_via_espuser(aliases):
    """
    Resolve aliases to ESPUser emails by matching username to the local-part.

    Users whose email still ends in LEARNINGU_DOMAIN are excluded.
    """
    if not aliases:
        return []
    local_parts = [a.split('@')[0].lower() for a in aliases]
    users = (
        ESPUser.objects
        .annotate(username_lower=Lower('username'))
        .filter(username_lower__in=local_parts)
    )
    return [
        u.email for u in users
        if u.email and not u.email.endswith(LEARNINGU_DOMAIN)
    ]


def get_final_recipients(recipients):
    """
    Expand and deduplicate recipients using PlainRedirect and ESPUser lookups.

    External addresses pass through. learningu.org aliases are resolved via
    redirects then usernames. Internal learningu.org destinations are filtered
    out. Order is preserved; duplicates are removed.
    """
    external, aliases, invalid = split_recipients(recipients or [])
    for bad in invalid:
        if bad:
            logger.warning('Email address without `@` symbol: `%s`', bad)

    resolved = list(external)
    resolved.extend(resolve_aliases_via_plain_redirect(aliases))
    resolved.extend(resolve_aliases_via_espuser(aliases))

    seen = set()
    unique = []
    for addr in resolved:
        if addr not in seen:
            seen.add(addr)
            unique.append(addr)
    return unique


def users_for_from_field(from_field):
    """
    Return ESPUser queryset matching a From header value.

    Internal host senders (settings.EMAIL_HOST_SENDER) match by username;
    otherwise match by email. Display-name forms (`Name <addr>`) are parsed.
    """
    if not from_field or not str(from_field).strip():
        return ESPUser.objects.none()

    addr = str(from_field).strip()
    if '<' in addr and '>' in addr:
        addr = addr.split('<', 1)[1].split('>', 1)[0].strip()

    host_sender = getattr(settings, 'EMAIL_HOST_SENDER', '') or ''
    if host_sender and addr.endswith(host_sender):
        return ESPUser.objects.filter(
            username__iexact=addr.split('@')[0]
        ).order_by('date_joined')
    return ESPUser.objects.filter(email__iexact=addr).order_by('date_joined')


def select_sender_by_priority(users):
    """
    Pick one user when multiple accounts share an address.

    Priority: Administrator > Teacher > Volunteer > Student > Educator.
    Falls back to the first user (earliest date_joined when ordered).
    """
    users = list(users)
    if not users:
        return None
    if len(users) == 1:
        return users[0]

    for group_name in SENDER_GROUP_PRIORITY:
        group_users = [u for u in users if u.groups.filter(name=group_name).exists()]
        if group_users:
            return group_users[0]
    return users[0]


def get_final_sender(from_field):
    """
    Resolve the From header to a preferred ESPUser, or None if unknown/blank.
    """
    return select_sender_by_priority(users_for_from_field(from_field))


def has_been_forwarded(raw_email):
    """Return True if the message already carries our forwarder header."""
    if isinstance(raw_email, bytes):
        try:
            raw_email_str = raw_email.decode('utf-8', errors='ignore')
        except Exception:
            return False
    else:
        raw_email_str = raw_email or ''
    return FORWARDER_HEADER in raw_email_str
