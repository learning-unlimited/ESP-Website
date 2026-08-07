#!/usr/bin/env python

# Main mailgate
# Handles incoming messages etc.

import email
import email.generator
import email.message
import email.utils
import hashlib
import io
import logging
import os
import random
import re
import smtplib
import socket
import sys

# Records each address this message has been delivered to, so that a message
# which returns to the *same* address is recognised as a loop, while a message
# legitimately forwarded from one site address to another is not.
DELIVERED_TO_HEADER = 'Delivered-To'

# Configure paths and environment variables
new_path = '/'.join(sys.path[0].split('/')[:-1])
sys.path += [new_path]
sys.path.insert(0, "/usr/sbin/")
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

# Make sure we end up in our logger even though this file is outside esp/esp/
logger = logging.getLogger('esp.mailgate')

project = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Path for site code
sys.path.insert(0, project)

# Check if a virtualenv has been installed and activated from elsewhere.
# If this has happened, then the VIRTUAL_ENV environment variable should be
# defined.
# If the variable isn't defined, then activate our own virtualenv.
if os.environ.get('VIRTUAL_ENV') is None:
    root = os.path.dirname(project)
    activate_this = os.path.join(root, 'env', 'bin', 'activate_this.py')
    # This file ships with the `virtualenv` package but not with stdlib `venv`,
    # and is absent wherever packages are installed system-wide (containers, CI).
    # Skipping it when missing keeps those environments working, and lets the
    # test suite import this module.
    if os.path.exists(activate_this):
        exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'),
             dict(__file__=activate_this))

# TODO: replace the activate_this.py bootstrap above by re-execing this script
# with env/bin/python whenever it is run outside the project virtualenv.

# Import Django and site-defined modules after activating the virtual environment
import django
django.setup()
from django.conf import settings
from django.core.cache import cache
from django.core.mail import get_connection
from django.core.mail import send_mail as django_send_mail
from django.core.mail.message import EmailMessage
from esp.dbmail.base import sender_account
from esp.dbmail.models import EmailList
from esp.users.models import ESPUser

host = socket.gethostname()
import_location = 'esp.dbmail.receivers.'
SUPPORT = settings.DEFAULT_EMAIL_ADDRESSES['support']
BOUNCES = settings.DEFAULT_EMAIL_ADDRESSES['bounces']

# The LU alias domain, and this site's own public domain, which may be a vanity
# domain (e.g., `stanfordesp.org` or `esp.mit.edu`) rather than an LU subdomain.
DOMAIN = '.learningu.org'
SITE_DOMAIN = settings.SITE_INFO[1].lower()

#DEBUG=True
DEBUG=False


class _RawMIMEMessage(email.message.Message):
    """A parsed message that accepts Django's `as_bytes(linesep=...)` call."""

    def as_bytes(self, unixfrom=False, linesep='\n'):
        buf = io.BytesIO()
        generator = email.generator.BytesGenerator(buf, mangle_from_=False)
        generator.flatten(self, unixfrom=unixfrom, linesep=linesep)
        return buf.getvalue()


class _ForwardedMessage(EmailMessage):
    """Hands an already-parsed MIME message to a Django mail backend unchanged."""

    def __init__(self, mime_message, from_email, to, connection=None):
        super().__init__(from_email=from_email, to=to, connection=connection)
        self._mime_message = mime_message

    def message(self):
        return self._mime_message


def _mail_connection():
    """Open a mail connection using whichever backend this site has configured.

    Defaults to Django's SMTP backend, which reads EMAIL_HOST/EMAIL_PORT and the
    matching credentials. A site with a local MTA therefore needs no extra
    configuration, and a site relaying through SendGrid points those settings at
    it. MAILGATE_EMAIL_BACKEND overrides the choice.
    """
    return get_connection(backend=getattr(
        settings, 'MAILGATE_EMAIL_BACKEND',
        'django.core.mail.backends.smtp.EmailBackend'))


def _delivery_address(local_part):
    """The canonical address this message was delivered to.

    Normalised onto SITE_DOMAIN so that a message arriving via the vanity domain
    (`alice@stanfordesp.org`) and one arriving via the LU alias
    (`alice@stanford.learningu.org`) count as the same address when detecting loops.
    """
    return '%s@%s' % (local_part.lower(), SITE_DOMAIN)


def _already_delivered_to(message, address):
    """True if this message has already been delivered to `address`.

    Per-address loop detection, as used by Postfix and qmail. A message arriving a
    second time at the *same* address is looping and must be dropped. A message
    forwarded from one site address to another (e.g., a program director alias
    resolving to a personal address) is not and must be allowed through.
    """
    target = address.strip().lower()
    for value in message.get_all(DELIVERED_TO_HEADER, []):
        _name, addr = email.utils.parseaddr(value)
        if (addr or value).strip().lower() == target:
            return True
    return False


def _is_site_address(address):
    """True if `address` is on a domain this site is authorised to sign for.

    Covers the vanity domain (`user@stanfordesp.org`) and the LU alias domain
    (`user@stanford.learningu.org`).
    """
    _name, addr = email.utils.parseaddr(address)
    domain = (addr or address).rsplit('@', 1)[-1].lower()
    return domain == SITE_DOMAIN or domain.endswith(DOMAIN)


def _alias_sender(message, sender):
    """Rewrite From: to the sender's site alias, so the message passes DMARC."""
    _name, address = email.utils.parseaddr(message.get('From', ''))
    if address and _is_site_address(address):
        # Already on one of our domains, so leave it alone.
        return

    del message['From']
    message['From'] = ESPUser.email_sendto_address(
        '%s@%s' % (sender.username, SITE_DOMAIN), sender.name())

    # Remove a Reply-To pointing off our domains for safety
    reply_to = message.get('Reply-To')
    if reply_to and not _is_site_address(reply_to):
        del message['Reply-To']


def _prefix_subject(subject, tag):
    """Prepend `[tag]` to `subject` unless it already carries it."""
    marker = '[%s]' % tag
    if marker.lower() in subject.lower():
        return subject
    return '%s %s' % (marker, subject) if subject else marker


def _rewrite_headers(message, handler_row, instance, list_address, sender):
    """Header rewriting for group broadcasts (ClassList, SectionList, PlainList).

    Handlers that set `preserve_headers` (e.g. UserEmail) skip this entirely.
    """
    del message['to']
    del message['cc']
    message['X-ESP-SENDER'] = 'version 2'
    client_ip = message['X-Client-IP'] or message['Client-IP']
    if client_ip:
        message['X-FORWARDED-FOR'] = client_ip

    # Point replies back at the list rather than at whoever wrote in
    reply_to = [list_address]
    # Also include the sender in the Reply-To if they are not already on the list.
    member_addresses = {email.utils.parseaddr(recipient)[1].lower()
                        for recipient in instance.recipients}
    if (sender.email or '').lower() not in member_addresses:
        reply_to.append('%s@%s' % (sender.username, SITE_DOMAIN))
    del message['Reply-To']
    message['Reply-To'] = ', '.join(reply_to)

    subject = message['subject'] or ''
    del message['subject']
    if getattr(instance, 'emailcode', None):
        subject = _prefix_subject(subject, instance.emailcode)
    if handler_row.subject_prefix:
        subject = _prefix_subject(subject, handler_row.subject_prefix)
    message['Subject'] = subject

    if handler_row.from_email:
        del message['from']
        message['From'] = handler_row.from_email

    # A fresh Message-ID per broadcast, so that a recipient who receives the
    # message by more than one route is not deduplicated down to a single copy
    # by their mail provider.
    del message['Message-ID']
    message['Message-ID'] = '<%s@%s>' % (
        hashlib.sha1(str(random.random()).encode()).hexdigest(), host)


def deliver(message, recipients, cc_all, sender):
    """Send `message` to `recipients` using this site's configured mail backend.

    `recipients` always comes from an EmailList handler, never from the incoming
    message's own To/Cc/Bcc headers, so this cannot be used to relay mail to an
    arbitrary address.
    """
    # Rewrite From: to the sender's site alias so the message passes DMARC
    _alias_sender(message, sender)

    # cc_all lists go out as a single message naming everyone; otherwise each
    # recipient gets their own copy addressed to them alone.
    batches = [recipients] if cc_all else [[recipient] for recipient in recipients]

    connection = _mail_connection()
    connection.open()
    try:
        for batch in batches:
            del message['To']
            message['To'] = ', '.join(batch)
            connection.send_messages(
                [_ForwardedMessage(message, BOUNCES, batch, connection)])
    finally:
        connection.close()
    logger.info("Forwarded message to %s", recipients)


def dispatch(local_part, message, sender):
    """Route `message` using the EmailList table.

    Returns True if the message was actually delivered to at least one recipient.
    False means the message was not delivered either because no handler recognised
    the address, or that the matched handler(s) declined to send.
    """
    for handler_row in EmailList.objects.all():  # Meta.ordering = ('seq',)
        try:
            match = re.compile(handler_row.regex).search(local_part)
        except re.error:
            logger.exception("EmailList %s has an invalid regex; skipping", handler_row.pk)
            continue
        if not match:
            continue

        try:
            module = __import__(import_location + handler_row.handler.lower(), (), (), [''])
            HandlerClass = getattr(module, handler_row.handler)
        except (ImportError, AttributeError):
            logger.exception("Could not load handler %r", handler_row.handler)
            continue

        instance = HandlerClass(handler_row, message)
        instance.process(local_part, *match.groups(), **match.groupdict())

        if not instance.send:
            logger.debug("Handler %s matched `%s` but declined to send",
                         handler_row.handler, local_part)
            continue

        if not getattr(instance, 'preserve_headers', False):
            _rewrite_headers(message, handler_row, instance,
                             _delivery_address(local_part), sender)

        if not instance.recipients:
            logger.warning("Handler %s matched `%s` but produced no recipients",
                           handler_row.handler, local_part)
            return False

        deliver(message, instance.recipients, handler_row.cc_all, sender)
        return True

    return False


def _bounce_allowed(sender_email):
    """True at most once per sender per MAILGATE_BOUNCE_INTERVAL seconds.

    The From header is trivially forged, so without a limit someone could spoof a
    registered user's address, fire a run of messages at nonexistent addresses and
    have every one of them bounce back at that user.
    """
    interval = getattr(settings, 'MAILGATE_BOUNCE_INTERVAL', 24 * 60 * 60)
    if not interval:
        return True
    key = 'mailgate:bounce:%s' % hashlib.sha1(
        sender_email.strip().lower().encode('utf-8')).hexdigest()
    if cache.get(key):
        return False
    cache.set(key, True, interval)
    return True


def bounce(delivery_address, message):
    """Tell a registered sender that their message could not be delivered.

    For security reasons, only senders who have an account on the site are notified.
    """
    _sender_name, sender_email = email.utils.parseaddr(message.get('From', ''))
    if not sender_email:
        return
    # Anti-loop: never bounce to our own system address
    if sender_email.lower() == SUPPORT.lower():
        return
    # Only bounce to senders we recognize, so that this cannot be used to send
    # unsolicited mail to an arbitrary address by spoofing the From header.
    if not ESPUser.objects.filter(email__iexact=sender_email).exists():
        logger.info("Undeliverable mail to `%s` from unregistered sender; not bouncing",
                    delivery_address)
        return
    if not _bounce_allowed(sender_email):
        logger.info("Undeliverable mail to `%s`; bounce to `%s` suppressed by rate limit",
                    delivery_address, sender_email)
        return
    try:
        django_send_mail(
            'Undeliverable mail to %s' % delivery_address,
            'Your message to "%s" could not be delivered.\n\n'
            'The address does not exist or is not currently accepting '
            'messages. If you believe this is an error, please contact '
            '%s for assistance.\n' % (delivery_address, SUPPORT),
            SUPPORT,
            [sender_email],
            fail_silently=True,
        )
    except Exception:
        logger.warning("Failed to send bounce to '%s'", sender_email)
    else:
        logger.info("Queued undeliverable notice for `%s` to `%s`",
                    delivery_address, sender_email)


def main():
    raw_email = sys.stdin.buffer.read()
    if not raw_email:
        logger.info("No message on stdin; nothing to do")
        return

    # Route on the envelope recipient supplied by the MTA, never on the
    # message's own headers.
    local_part = os.environ.get('LOCAL_PART')
    if not local_part:
        logger.error("LOCAL_PART is not set by the MTA; cannot route this message")
        return

    message = email.message_from_bytes(raw_email, _class=_RawMIMEMessage)

    # Per-address loop detection. Record this delivery before forwarding, so that
    # a message which comes back to the same address is recognised next time.
    delivery_address = _delivery_address(local_part)
    if _already_delivered_to(message, delivery_address):
        logger.warning("Message has already been delivered to `%s`; dropping to "
                       "prevent a mail loop", delivery_address)
        return
    message[DELIVERED_TO_HEADER] = delivery_address

    # Only registered users may send through the site
    sender = sender_account(message)
    if sender is None:
        logger.info("Message to `%s` from an unregistered sender; not forwarding",
                    delivery_address)
        return

    if not dispatch(local_part, message, sender):
        logger.info("Nothing delivered for `%s`", delivery_address)
        bounce(delivery_address, message)


if __name__ == "__main__":
    try:
        main()
    except (smtplib.SMTPException, ConnectionError, TimeoutError):
        # Transient delivery problem: exit EX_TEMPFAIL so the MTA queues the
        # message and retries, rather than dropping it silently.
        logger.exception("Mail transport failure while forwarding; asking the MTA to retry")
        sys.exit(75)
    except Exception:
        # A bug or a permanently undeliverable message. Exit 0 so the MTA treats
        # delivery as handled and does not emit its own bounce.
        logger.exception("mailgate failed; dropping message")
        if DEBUG:
            raise
    sys.exit(0)
