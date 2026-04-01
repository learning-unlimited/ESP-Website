#!/usr/bin/env python

# Main mailgate
# Handles incoming messages etc.

from __future__ import absolute_import
from __future__ import print_function

import logging
import os.path
import sys
import smtplib
import traceback
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses

# Custom header marker for loop prevention
FORWARDER_HEADER = "X-Forwarded-By: lu-forwarder"

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

# TODO: Better:
#if sys.prefix == sys.base_prefix:
#    os.execv("env/bin/python", ["env/bin/python"] + sys.argv)

# Import Django and site-defined modules after activating the virtual environment
import django
django.setup()
from esp.dbmail.models import EmailList, PlainRedirect, send_mail
from esp.users.models import ESPUser
from django.conf import settings
from django.db.models.functions import Lower
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

import_location = 'esp.dbmail.receivers.'
SUPPORT = settings.DEFAULT_EMAIL_ADDRESSES['support']
ORGANIZATION_NAME = settings.INSTITUTION_NAME + '_' + settings.ORGANIZATION_SHORT_NAME
DOMAIN = '.learningu.org'

#DEBUG=True
DEBUG=False
######################################################################################################################


def get_final_sender(sender):
    logger.debug("In final sender")
    return sender # TODO: add look-up logic


def get_final_recipients(recipients):
    """
    Expand and deduplicate recipients using the ESPUser database
    """
    logger.debug("In final recipients")
    resolved = []
    aliases = []
    for recipient in instance.recipients:
        # If the recipient has an email address that does not end with @anysite.learningu.org, keep them
        # Note we `DOMAIN` instead of the `HOSTNAME` because the latter resolves to `thissite.learningu.org`
        # in settings,  and we want `anysite.learningu.org` while still allowing user@learningu.org because
        # those resolve to enterprise Gmail addresses
        if recipient.endswith(DOMAIN):
            aliases.append(recipient)
        elif '@' in recipient:
            resolved.append(recipient)
        else:
            logger.warning('Email address without `@` symbol: `{}`'.format(recipient))
    redirects = PlainRedirect.objects.annotate(original_lower=Lower("original"
                )).filter(original_lower__in=[x.split('@')[0].lower() for x in aliases]
                ).exclude(destination__isnull=True).exclude(destination='')
    # Split out individual email addresses if any of the redirects is a list
    redirects = list(itertools.chain.from_iterable(map(lambda x: x.destination.split(',') if x.destination else [], redirects)))
    users = ESPUser.objects.annotate(username_lower=Lower("username"
            )).filter(username_lower__in=[x.split('@')[0].lower() for x in aliases])
    # Grab the emails from the users
    users = [x.email for x in users]
    # Theoretically at least one of these should be empty, but now doesn't seem like the time
    # If the redirect resolve to anything@anysite.learningu.org, kill it
    for address in redirects + users:
        if not address.endswith(DOMAIN):
            resolved.append(address)
    # if the above filtering leaves the 'to' list empty, abort
    if len(resolved) == 0:
        continue

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for r in resolved:
        if r not in seen:
            seen.add(r)
            unique.append(r)

    return unique


def has_been_forwarded(raw_email):
    """
    Detect if this email has already passed through our system.
    """
    if isinstance(raw_email, bytes):
        try:
            raw_email_str = raw_email.decode("utf-8", errors="ignore")
        except Exception:
            return False
    else:
        raw_email_str = raw_email

    return FORWARDER_HEADER in raw_email_str


def forward_email(raw_email, sender, recipients):
    """
    Forward email via SendGrid without modifying raw MIME content so that it
      * is S/MIME safe
      * prevents loops (read-only check)
      * uses separate bounce address
    """

    # Loop prevention (read-only so that we don't modify the message)
    if has_been_forwarded(raw_email):
        logger.warning("Email already forwarded. Skipping to prevent loop.")
        return


    if not recipients:
        logger.info("No recipients after alias resolution of `{}`. Skipping.".format(recipients))
        return

    try:
        smtp = smtplib.SMTP(settings.SENDGRID_SMTP_HOST, settings.SENDGRID_SMTP_PORT)
        smtp.starttls()
        smtp.login(settings.SENDGRID_SMTP_USERNAME, settings.SENDGRID_API_KEY)

        # Send one email to each recipient, using bounce address as envelope sender
        for recipient in recipients:
            smtp.sendmail(sender, recipient, raw_email)

        smtp.quit()

        logger.info("Forwarded email from {} to {} via SendGrid".format(sender, recipients))

    except Exception as e:
        logger.exception("Failed to forward email: ".format(e))
        raise


def main():
    logger.debug("Main has been executed")

    # Read the raw email exactly as Exim provides it
    raw_email = sys.stdin.buffer.read()
    logger.debug("Read raw email from buffer")
    if not raw_email:
        logger.info("No email to forward")
        return

    # Get sender and recipient(s) for routing logic
    msg = BytesParser(policy=policy.default).parsebytes(raw_email)
    logger.debug("Getting sender")
    original_sender = msg.get("From", "")
    logger.debug("Getting recipients")
    addresses = getaddresses(msg.get_all("to", []) +
                             msg.get_all("cc", []) +
                             msg.get_all("bcc", []))
    original_recipients = [addr for name, addr in addresses]

    # Look up sender's account alias
    logger.debug("Looking up sender")
    final_sender = get_final_sender(original_sender)
    logger.debug("Aliasing original `{}` as `{}`".format(original_sender, final_sender))
    # Look up emails associated with recipient alias(es)
    final_recipients = get_final_recipients(original_recipients)
    logger.debug("Resolving original `{}` as `{}`".format(original_recipients, final_recipients))

    # Send unchanged message to new recipient(s) with aliased sender
    forward_email(raw_email, final_sender, final_recipients)
    logger.info("Sent mail from `{}` to `{}`".format(final_sender, final_recipients))


if __name__ == "__main__":
    logger.debug("Beginning")
    try:
        main()
    except Exception as e: # TODO: improve this
        logger.debug("Traceback: {}".format(e))
        error_info = traceback.format_exc()
        logger.debug("Traceback is\n{}".format(error_info))
        raise Exception("Python script failed")

