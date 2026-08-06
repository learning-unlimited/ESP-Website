#!/usr/bin/env python

# Main mailgate
# Handles incoming messages etc.

import email
import email.utils
import hashlib
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
    exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this))

# TODO: replace the activate_this.py bootstrap above by re-execing this script
# with env/bin/python whenever it is run outside the project virtualenv.
# (activate_this.py ships with the `virtualenv` package but not stdlib `venv`.)

# Import Django and site-defined modules after activating the virtual environment
import django
django.setup()
from django.conf import settings
from django.core.mail import send_mail as django_send_mail
from esp.dbmail.models import EmailList
from esp.users.models import ESPUser

host = socket.gethostname()
import_location = 'esp.dbmail.receivers.'
SUPPORT = settings.DEFAULT_EMAIL_ADDRESSES['support']
BOUNCES = settings.DEFAULT_EMAIL_ADDRESSES['bounces']
ORGANIZATION_NAME = settings.INSTITUTION_NAME + '_' + settings.ORGANIZATION_SHORT_NAME
# This site's own public domain, which may be a vanity domain (e.g. `stanfordesp.org`
# or `esp.mit.edu`) rather than a `learningu.org` subdomain.
SITE_DOMAIN = settings.SITE_INFO[1].lower()

#DEBUG=True
DEBUG=False


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


def _rewrite_headers(message, handler_row, instance):
    """Header rewriting for group broadcasts (ClassList, SectionList, PlainList).

    Handlers that set `preserve_headers` (e.g. UserEmail) skip this entirely.
    """
    del message['to']
    del message['cc']
    message['X-ESP-SENDER'] = 'version 2'
    client_ip = message['X-Client-IP'] or message['Client-IP']
    if client_ip:
        message['X-FORWARDED-FOR'] = client_ip

    subject = message['subject']
    del message['subject']
    if getattr(instance, 'emailcode', None):
        subject = '[%s] %s' % (instance.emailcode, subject)
    if handler_row.subject_prefix:
        subject = '[%s] %s' % (handler_row.subject_prefix, subject)
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


def deliver(message, recipients, cc_all):
    """Send `message` to `recipients` via SendGrid SMTP.

    `recipients` always comes from an EmailList handler, never from the incoming
    message's own To/Cc/Bcc headers, so this cannot be used to relay mail to an
    arbitrary address.
    """
    api_key = getattr(settings, 'SENDGRID_API_KEY', None)
    if not api_key:
        raise RuntimeError("SENDGRID_API_KEY is not configured; cannot send mail.")

    smtp = smtplib.SMTP(settings.SENDGRID_SMTP_HOST, settings.SENDGRID_SMTP_PORT)
    try:
        smtp.starttls()
        smtp.login(settings.SENDGRID_SMTP_USERNAME, api_key)
        if cc_all:
            del message['To']
            message['To'] = ', '.join(recipients)
            smtp.sendmail(BOUNCES, recipients, message.as_bytes())
        else:
            for recipient in recipients:
                del message['To']
                message['To'] = recipient
                smtp.sendmail(BOUNCES, [recipient], message.as_bytes())
    finally:
        try:
            smtp.quit()
        except Exception:
            logger.debug("Error closing SMTP connection", exc_info=True)
    logger.info("Forwarded message to %s via SendGrid", recipients)


def dispatch(local_part, message):
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
            _rewrite_headers(message, handler_row, instance)

        if not instance.recipients:
            logger.warning("Handler %s matched `%s` but produced no recipients",
                           handler_row.handler, local_part)
            return False

        deliver(message, instance.recipients, handler_row.cc_all)
        return True

    return False


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

    message = email.message_from_bytes(raw_email)

    # Per-address loop detection. Record this delivery before forwarding, so that
    # a message which comes back to the same address is recognised next time.
    delivery_address = _delivery_address(local_part)
    if _already_delivered_to(message, delivery_address):
        logger.warning("Message has already been delivered to `%s`; dropping to "
                       "prevent a mail loop", delivery_address)
        return
    message[DELIVERED_TO_HEADER] = delivery_address

    if not dispatch(local_part, message):
        logger.info("Nothing delivered for `%s`", delivery_address)
        bounce(delivery_address, message)


if __name__ == "__main__":
    try:
        main()
    except smtplib.SMTPException:
        # Transient delivery problem: exit EX_TEMPFAIL so the MTA queues the
        # message and retries, rather than dropping it silently.
        logger.exception("SMTP failure while forwarding; asking the MTA to retry")
        sys.exit(75)
    except Exception:
        # A bug or a permanently undeliverable message. Exit 0 so the MTA treats
        # delivery as handled and does not emit its own bounce.
        logger.exception("mailgate failed; dropping message")
        if DEBUG:
            raise
    sys.exit(0)
