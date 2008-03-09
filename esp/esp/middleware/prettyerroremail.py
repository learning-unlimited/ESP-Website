
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu

== Addendum ==
The idea and much of the code to generate the pretty HTML email is taken from Kenneth Arnold.
http://www.djangosnippets.org/snippets/631/
"""

import sys
import django

from django.conf import settings
from django.views import debug
import django.core.mail

__all__ = ('PrettyErrorEmailMiddleware',)

class PrettyErrorEmailMiddleware(object):
    """ This middleware will catch exceptions and--- instead of the
    normal less useful debug errors sent ---will send out the technical 500
    error response.

    To install, be sure to place this middleware near the beginning
    of the MIDDLEWARE_CLASSES setting in your settings file.
    This will make sure that it doesn't accidentally catch errors
    you were meaning to catch with other middleware.
    """

    ADMINS = None
    def process_request(self, request):
        """ In case a previous view wiped out the ADMINS variable,
        it'd be nice to resurrect it before the next request is handled.
        """
        if not settings.ADMINS and PrettyErrorEmailMiddleware.ADMINS:
            settings.ADMINS = PrettyErrorEmailMiddleware.ADMINS


    def process_exception(self, request, exception):
        if not PrettyErrorEmailMiddleware.ADMINS:
            PrettyErrorEmailMiddleware.ADMINS = settings.ADMINS

        if settings.DEBUG:
            return None

        try:
            # Add the technical 500 page.
            exc_info = sys.exc_info()

            subject = 'Error (%s IP): %s' % ((request.META.get('REMOTE_ADDR')
                                              in settings.INTERNAL_IPS and 'internal'
                                              or 'EXTERNAL'), request.path)
            try:
                request_repr = repr(request)
            except:
                request_repr = "Request repr() unavailable"

            message = "%s\n\n%s" % (self._get_traceback(exc_info), request_repr)

            debug_response = debug.technical_500_response(request, *exc_info)
            msg = EmailMultiAlternatives(settings.EMAIL_SUBJECT_PREFIX \
                                             + subject, message,
                                         settings.SERVER_EMAIL,
                                         [a[1] for a in
                                          PrettyErrorEmailMiddleware.ADMINS])

            msg.attach_alternative(debug_response.content, 'text/html')
            msg.send(fail_silently=True)
        except Exception, e:
            return None
        else:
            # Now that ADMINS is empty, we shouldn't get a second email.
            settings.ADMINS = ()

        return None

    def _get_traceback(self, exc_info=None):
        "Helper function to return the traceback as a string"
        import traceback
        return '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))




if hasattr(django.core.mail, 'EmailMultiAlternatives'):
    # We already have what we need.. no need to run some more code.
    EmailMultiAlternatives = django.core.mail.EmailMultiAlternatives
    mail_admins = django.core.mail.mail_admins
else:
    """
    Tools for sending email.

    From Django: django.core.mail, revision 7183
    """

    from django.conf import settings
    from django.template.defaultfilters import smart_string as smart_str
    from email import Charset, Encoders
    from email.MIMEText import MIMEText
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEBase import MIMEBase
    from email.Header import Header
    from email.Utils import formatdate, parseaddr, formataddr
    import mimetypes
    import os
    import smtplib
    import socket
    import time
    import random

    def force_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
        """
        Similar to smart_unicode, except that lazy instances are resolved to
        strings, rather than kept as lazy objects.

        If strings_only is True, don't convert (some) non-string-like objects.
        """
        if strings_only and isinstance(s, (types.NoneType, int, long, datetime.datetime, datetime.date, datetime.time, float)):
            return s

        if not isinstance(s, basestring,):
            if hasattr(s, '__unicode__'):
                s = unicode(s)
            else:
                s = unicode(str(s), encoding, errors)
        elif not isinstance(s, unicode):
            # Note: We use .decode() here, instead of unicode(s, encoding,
            # errors), so that if s is a SafeString, it ends up being a
            # SafeUnicode at the end.
            s = s.decode(encoding, errors)

        return s

    # Don't BASE64-encode UTF-8 messages so that we avoid unwanted attention from
    # some spam filters.
    Charset.add_charset('utf-8', Charset.SHORTEST, Charset.QP, 'utf-8')

    # Default MIME type to use on attachments (if it is not explicitly given
    # and cannot be guessed).
    DEFAULT_ATTACHMENT_MIME_TYPE = 'application/octet-stream'

    # Cache the hostname, but do it lazily: socket.getfqdn() can take a couple of
    # seconds, which slows down the restart of the server.
    class CachedDnsName(object):
        def __str__(self):
            return self.get_fqdn()

        def get_fqdn(self):
            if not hasattr(self, '_fqdn'):
                self._fqdn = socket.getfqdn()
            return self._fqdn

    DNS_NAME = CachedDnsName()

    # Copied from Python standard library and modified to used the cached hostname
    # for performance.
    def make_msgid(idstring=None):
        """Returns a string suitable for RFC 2822 compliant Message-ID, e.g:

        <20020201195627.33539.96671@nightshade.la.mastaler.com>

        Optional idstring if given is a string used to strengthen the
        uniqueness of the message id.
        """
        timeval = time.time()
        utcdate = time.strftime('%Y%m%d%H%M%S', time.gmtime(timeval))
        try:
            pid = os.getpid()
        except AttributeError:
            # Not getpid() in Jython, for example.
            pid = 1
        randint = random.randrange(100000)
        if idstring is None:
            idstring = ''
        else:
            idstring = '.' + idstring
        idhost = DNS_NAME
        msgid = '<%s.%s.%s%s@%s>' % (utcdate, pid, randint, idstring, idhost)
        return msgid

    class BadHeaderError(ValueError):
        pass

    def forbid_multi_line_headers(name, val):
        "Forbids multi-line headers, to prevent header injection."
        if '\n' in val or '\r' in val:
            raise BadHeaderError("Header values can't contain newlines (got %r for header %r)" % (val, name))
        try:
            val = force_unicode(val).encode('ascii')
        except UnicodeEncodeError:
            if name.lower() in ('to', 'from', 'cc'):
                result = []
                for item in val.split(', '):
                    nm, addr = parseaddr(item)
                    nm = str(Header(nm, settings.DEFAULT_CHARSET))
                    result.append(formataddr((nm, str(addr))))
                val = ', '.join(result)
            else:
                val = Header(force_unicode(val), settings.DEFAULT_CHARSET)
        return name, val

    class SafeMIMEText(MIMEText):
        def __setitem__(self, name, val):
            name, val = forbid_multi_line_headers(name, val)
            MIMEText.__setitem__(self, name, val)

    class SafeMIMEMultipart(MIMEMultipart):
        def __setitem__(self, name, val):
            name, val = forbid_multi_line_headers(name, val)
            MIMEMultipart.__setitem__(self, name, val)

    class SMTPConnection(object):
        """
        A wrapper that manages the SMTP network connection.
        """

        def __init__(self, host=None, port=None, username=None, password=None,
                use_tls=None, fail_silently=False):
            self.host = host or settings.EMAIL_HOST
            self.port = port or settings.EMAIL_PORT
            self.username = username or settings.EMAIL_HOST_USER
            self.password = password or settings.EMAIL_HOST_PASSWORD
            self.use_tls = (use_tls is not None) and use_tls or getattr(settings, 'EMAIL_USE_TLS', False)
            self.fail_silently = fail_silently
            self.connection = None

        def open(self):
            """
            Ensure we have a connection to the email server. Returns whether or not
            a new connection was required.
            """
            if self.connection:
                # Nothing to do if the connection is already open.
                return False
            try:
                self.connection = smtplib.SMTP(self.host, self.port)
                if self.use_tls:
                    self.connection.ehlo()
                    self.connection.starttls()
                    self.connection.ehlo()
                if self.username and self.password:
                    self.connection.login(self.username, self.password)
                return True
            except:
                if not self.fail_silently:
                    raise

        def close(self):
            """Close the connection to the email server."""
            try:
                try:
                    self.connection.quit()
                except socket.sslerror:
                    # This happens when calling quit() on a TLS connection
                    # sometimes.
                    self.connection.close()
                except:
                    if self.fail_silently:
                        return
                    raise
            finally:
                self.connection = None

        def send_messages(self, email_messages):
            """
            Send one or more EmailMessage objects and return the number of email
            messages sent.
            """
            if not email_messages:
                return
            new_conn_created = self.open()
            if not self.connection:
                # We failed silently on open(). Trying to send would be pointless.
                return
            num_sent = 0
            for message in email_messages:
                sent = self._send(message)
                if sent:
                    num_sent += 1
            if new_conn_created:
                self.close()
            return num_sent

        def _send(self, email_message):
            """A helper method that does the actual sending."""
            if not email_message.to:
                return False
            try:
                self.connection.sendmail(email_message.from_email,
                        email_message.recipients(),
                        email_message.message().as_string())
            except:
                if not self.fail_silently:
                    raise
                return False
            return True

    class EmailMessage(object):
        """
        A container for email information.
        """
        content_subtype = 'plain'
        multipart_subtype = 'mixed'
        encoding = None     # None => use settings default

        def __init__(self, subject='', body='', from_email=None, to=None, bcc=None,
                connection=None, attachments=None, headers=None):
            """
            Initialise a single email message (which can be sent to multiple
            recipients).

            All strings used to create the message can be unicode strings (or UTF-8
            bytestrings). The SafeMIMEText class will handle any necessary encoding
            conversions.
            """
            if to:
                self.to = list(to)
            else:
                self.to = []
            if bcc:
                self.bcc = list(bcc)
            else:
                self.bcc = []
            self.from_email = from_email or settings.DEFAULT_FROM_EMAIL
            self.subject = subject
            self.body = body
            self.attachments = attachments or []
            self.extra_headers = headers or {}
            self.connection = connection

        def get_connection(self, fail_silently=False):
            if not self.connection:
                self.connection = SMTPConnection(fail_silently=fail_silently)
            return self.connection

        def message(self):
            encoding = self.encoding or settings.DEFAULT_CHARSET
            msg = SafeMIMEText(smart_str(self.body), self.content_subtype, encoding)
            if self.attachments:
                body_msg = msg
                msg = SafeMIMEMultipart(_subtype=self.multipart_subtype)
                if self.body:
                    msg.attach(body_msg)
                for attachment in self.attachments:
                    if isinstance(attachment, MIMEBase):
                        msg.attach(attachment)
                    else:
                        msg.attach(self._create_attachment(*attachment))
            msg['Subject'] = self.subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to)
            msg['Date'] = formatdate()
            msg['Message-ID'] = make_msgid()
            if self.bcc:
                msg['Bcc'] = ', '.join(self.bcc)
            for name, value in self.extra_headers.items():
                msg[name] = value
            return msg

        def recipients(self):
            """
            Returns a list of all recipients of the email (includes direct
            addressees as well as Bcc entries).
            """
            return self.to + self.bcc

        def send(self, fail_silently=False):
            """Send the email message."""
            return self.get_connection(fail_silently).send_messages([self])

        def attach(self, filename=None, content=None, mimetype=None):
            """
            Attaches a file with the given filename and content. The filename can
            be omitted (useful for multipart/alternative messages) and the mimetype
            is guessed, if not provided.

            If the first parameter is a MIMEBase subclass it is inserted directly
            into the resulting message attachments.
            """
            if isinstance(filename, MIMEBase):
                assert content == mimetype == None
                self.attachments.append(filename)
            else:
                assert content is not None
                self.attachments.append((filename, content, mimetype))

        def attach_file(self, path, mimetype=None):
            """Attaches a file from the filesystem."""
            filename = os.path.basename(path)
            content = open(path, 'rb').read()
            self.attach(filename, content, mimetype)

        def _create_attachment(self, filename, content, mimetype=None):
            """
            Convert the filename, content, mimetype triple into a MIME attachment
            object.
            """
            if mimetype is None:
                mimetype, _ = mimetypes.guess_type(filename)
                if mimetype is None:
                    mimetype = DEFAULT_ATTACHMENT_MIME_TYPE
            basetype, subtype = mimetype.split('/', 1)
            if basetype == 'text':
                attachment = SafeMIMEText(smart_str(content),
                                          subtype, settings.DEFAULT_CHARSET)
            else:
                # Encode non-text attachments with base64.
                attachment = MIMEBase(basetype, subtype)
                attachment.set_payload(content)
                Encoders.encode_base64(attachment)
            if filename:
                attachment.add_header('Content-Disposition', 'attachment', filename=filename)
            return attachment

    class EmailMultiAlternatives(EmailMessage):
        """
        A version of EmailMessage that makes it easy to send multipart/alternative
        messages. For example, including text and HTML versions of the text is
        made easier.
        """
        multipart_subtype = 'alternative'

        def attach_alternative(self, content, mimetype=None):
            """Attach an alternative content representation."""
            self.attach(content=content, mimetype=mimetype)

    def send_mail(subject, message, from_email, recipient_list, fail_silently=False, auth_user=None, auth_password=None):
        """
        Easy wrapper for sending a single message to a recipient list. All members
        of the recipient list will see the other recipients in the 'To' field.

        If auth_user is None, the EMAIL_HOST_USER setting is used.
        If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.

        Note: The API for this method is frozen. New code wanting to extend the
        functionality should use the EmailMessage class directly.
        """
        connection = SMTPConnection(username=auth_user, password=auth_password,
                                     fail_silently=fail_silently)
        return EmailMessage(subject, message, from_email, recipient_list, connection=connection).send()

    def send_mass_mail(datatuple, fail_silently=False, auth_user=None, auth_password=None):
        """
        Given a datatuple of (subject, message, from_email, recipient_list), sends
        each message to each recipient list. Returns the number of e-mails sent.

        If from_email is None, the DEFAULT_FROM_EMAIL setting is used.
        If auth_user and auth_password are set, they're used to log in.
        If auth_user is None, the EMAIL_HOST_USER setting is used.
        If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.

        Note: The API for this method is frozen. New code wanting to extend the
        functionality should use the EmailMessage class directly.
        """
        connection = SMTPConnection(username=auth_user, password=auth_password,
                                     fail_silently=fail_silently)
        messages = [EmailMessage(subject, message, sender, recipient) for subject, message, sender, recipient in datatuple]
        return connection.send_messages(messages)

    def mail_admins(subject, message, fail_silently=False):
        "Sends a message to the admins, as defined by the ADMINS setting."
        EmailMessage(settings.EMAIL_SUBJECT_PREFIX + subject, message,
                settings.SERVER_EMAIL, [a[1] for a in
                    settings.ADMINS]).send(fail_silently=fail_silently)

    def mail_managers(subject, message, fail_silently=False):
        "Sends a message to the managers, as defined by the MANAGERS setting."
        EmailMessage(settings.EMAIL_SUBJECT_PREFIX + subject, message,
                settings.SERVER_EMAIL, [a[1] for a in
                    settings.MANAGERS]).send(fail_silently=fail_silently)
