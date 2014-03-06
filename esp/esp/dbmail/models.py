
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
  Email: web-team@lists.learningu.org
"""
import sys

from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from esp.cache import cache_function
from esp.users.models import ESPUser
from esp.middleware import ESPError
from datetime import datetime
from esp.db.fields import AjaxForeignKey

from esp.datatree.models import *
from esp.users.models import PersistentQueryFilter, ESPUser
from django.template import Template #, VariableNode, TextNode

import esp.dbmail.sendto_fns

from django.conf import settings

from django.core.mail import get_connection
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend
from django.core.mail.message import sanitize_address
from django.core.exceptions import ImproperlyConfigured

from south.models import MigrationHistory



def send_mail(subject, message, from_email, recipient_list, fail_silently=False, bcc=settings.DEFAULT_EMAIL_ADDRESSES['archive'],
              return_path=settings.DEFAULT_EMAIL_ADDRESSES['bounces'], extra_headers={},
              *args, **kwargs):
    from_email = from_email.strip()
    if 'Reply-To' in extra_headers:
        extra_headers['Reply-To'] = extra_headers['Reply-To'].strip()
    if type(recipient_list) == str or type(recipient_list) == unicode:
        new_list = [ recipient_list ]
    else:
        new_list = [ x for x in recipient_list ]
    from django.core.mail import EmailMessage #send_mail as django_send_mail
    print "Sent mail to %s" % str(new_list)
    
    #   Get whatever type of e-mail connection Django provides.
    #   Normally this will be SMTP, but it also has an in-memory backend for testing.
    connection = get_connection(fail_silently=fail_silently, return_path=return_path)
    msg = EmailMessage(subject, message, from_email, new_list, bcc=(bcc,), connection=connection, headers=extra_headers)
    
    #   Detect HTML tags in message and change content-type if they are found
    if '<html>' in message:
        msg.content_subtype = 'html'
    
    msg.send()

def expire_unsent_emails(orm=None):
    """
    Expires old, unsent TextOfEmails and MessageRequests.

    By default, performs the query using the models/managers defined in this
    file. Alternatively, during a migration, a frozen orm can be passed via the
    orm parameter.
    """
    if orm is None:
        orm = sys.modules[__name__]
    TextOfEmail.expireUnsentEmails(orm_class=orm.TextOfEmail)
    MessageRequest.expireUnprocessedRequests(orm_class=orm.MessageRequest)

@cache_function
def can_process_and_send():
    """
    Returns True if the dbmail cronmail script is allowed to process and send
    emails, and False otherwise.

    Currently, this function asserts that the expire_unsent_emails migration
    has been run. If it hasn't, it is possible that there are old, unsent
    messages from before 6e350a3735 that should not be sent because they are
    out-of-date. This requirement can be removed after the full deployment of
    stable release 4.
    """
    now = datetime.now()
    return MigrationHistory.objects.filter(app_name='dbmail',
                                migration__contains='expire_unsent_emails',
                                applied__lt=now).exists()
can_process_and_send.depend_on_model(MigrationHistory)



class ActionHandler(object):
    """ This class passes variable keys in such a way that django templates can use them."""
    def __init__(self, obj, user):
        self._obj  = obj
        self._user = user
        
    def __getattribute__(self, key):
        
        # get the object, can't use self.obj since we're doing fun stuff
        if key == '_obj' or key == '_user':
            # use the parent's __getattribute__
            return super(ActionHandler, self).__getattribute__(key)

        obj = self._obj
        
        if not hasattr(obj, 'get_msg_vars'):
            return getattr(obj, key)
        
        return obj.get_msg_vars(self._user, key)
    

class MessageRequest(models.Model):
    """ An initial request to broadcast an e-mail message """

    # Each MessageRequest can specify a sendto function, which specifies, for
    # each recipient in the recipients query, which set of associated email
    # addresses should receive the message.  The sendto functions are defined
    # in esp.dbmail.sendto_fns, and their names are choices for the
    # MessageRequest.sendto_fn_name field.
    SEND_TO_GUARDIAN = 'send_to_guardian'
    SEND_TO_EMERGENCY = 'send_to_emergency'
    SEND_TO_SELF_AND_GUARDIAN = 'send_to_self_and_guardian'
    SEND_TO_SELF_AND_EMERGENCY = 'send_to_self_and_emergency'
    SEND_TO_GUARDIAN_AND_EMERGENCY = 'send_to_guardian_and_emergency'
    SEND_TO_SELF_AND_GUARDIAN_AND_EMERGENCY = 'send_to_self_and_guardian_and_emergency'

    # The empty string is the default value of the MessageRequest.sendto_fn_name
    # field and means 'send_to_self', the legacy functionality of sending only
    # to the ESPUser's email as given in the email field.
    SEND_TO_SELF = ''
    SEND_TO_SELF_REAL = 'send_to_self'

    SENDTO_FN_CHOICES = (
        (SEND_TO_SELF, 'send to user'),
        (SEND_TO_GUARDIAN, 'send to guardian'),
        (SEND_TO_EMERGENCY, 'send to emergency contact'),
        (SEND_TO_SELF_AND_GUARDIAN, 'send to user and guardian'),
        (SEND_TO_SELF_AND_EMERGENCY, 'send to user and emergency contact'),
        (SEND_TO_GUARDIAN_AND_EMERGENCY, 'send to guardian and emergency contact'),
        (SEND_TO_SELF_AND_GUARDIAN_AND_EMERGENCY, 'send to user and guardian and emergency contact'),
    )

    id = models.AutoField(primary_key=True)
    subject = models.TextField(null=True,blank=True) 
    msgtext = models.TextField(blank=True, null=True) 
    special_headers = models.TextField(blank=True, null=True) 
    recipients = models.ForeignKey(PersistentQueryFilter) # We will get the user from a query filter
    sendto_fn_name = models.CharField("sendto function", max_length=128,
                    choices=SENDTO_FN_CHOICES, default=SEND_TO_SELF,
                    help_text="The function that specifies, for each recipient " +
                    "of the message, which set of associated email addresses " +
                    "should receive the message.")
    sender = models.TextField(blank=True, null=True) # E-mail sender; should be a valid SMTP sender string 
    creator = AjaxForeignKey(ESPUser) # the person who sent this message
    processed = models.BooleanField(default=False, db_index=True) # Have we made EmailRequest objects from this MessageRequest yet?
    processed_by = models.DateTimeField(null=True, default=None, db_index=True) # When should this be processed by?
    email_all = models.BooleanField(default=True) # do we just want to create an emailrequest for each user?
    priority_level = models.IntegerField(null=True, blank=True) # Priority of a message; may be used in the future to make a message non-digested, or to prevent a low-priority message from being sent

    def __unicode__(self):
        return unicode(self.subject)
    
    # Access special_headers as a dictionary
    def special_headers_dict_get(self):
        if not self.special_headers:
            return {}
        import cPickle as pickle
        return pickle.loads(str(self.special_headers)) # We call str here because pickle hates unicode. -ageng 2008-11-18
    def special_headers_dict_set(self, value):
        import cPickle as pickle
        if type(value) is not dict:
            value = {}
        self.special_headers = pickle.dumps(value)
    special_headers_dict = property( special_headers_dict_get, special_headers_dict_set )
    
    @staticmethod
    def createRequest(var_dict = None, *args, **kwargs):
        """ To create a new MessageRequest, you should provide a dictionary of
            the variables you want substituted, if you want any. """
        new_request = MessageRequest(*args, **kwargs)

        if var_dict is not None:
            new_request.save()
            MessageVars.createMessageVars(new_request, var_dict) # create the message Variables
        return new_request

    @classmethod
    def expireUnprocessedRequests(cls, orm_class=None):
        """
        For all unprocessed requests (probably old messages that for some
        reason were never sent), expire them by pretending that they've been
        processed. Used to prevent old, outdated messages from going out.

        By default, performs the query using the MessageRequest model and its
        default Manager. Alternatively, during a migration, a frozen orm class
        can be passed via the orm_class parameter.
        """
        if orm_class is None:
            orm_class = cls
        return orm_class.objects.filter(Q(processed_by__isnull=True) | Q(processed_by__lt=datetime.now()), processed=False).update(processed=True)

    def parseSmartText(self, text, user):
        """ Takes a text and user, and, within the confines of this message, will make it better. """

        # prepare variables
        text = unicode(text)
        user = ESPUser(user)

        context = MessageVars.getContext(self, user)

        newtext = ''
        template = Template(text)

        return template.render(context)

    @classmethod
    def is_sendto_fn_name_choice(cls, sendto_fn_name):
        """
        Determines if the given string is one of the sendto_fn_name field choices.
        """
        if sendto_fn_name == cls.SEND_TO_SELF_REAL:
            return True
        return bool(filter(lambda fn: sendto_fn_name == fn[0], cls.SENDTO_FN_CHOICES))

    @classmethod
    def get_sendto_fn_callable(cls, sendto_fn_name):
        """
        Returns the callable sendto function whose name is the given string.

        The function must be one of the sendto_fn_name field choices, and must
        be a callable defined in esp.dbmail.sendto_fns. Raises aan
        ImproperlyConfigured exception if that is not the case.
        """
        if not cls.is_sendto_fn_name_choice(sendto_fn_name):
            raise ImproperlyConfigured('"%s" is not one of the available sendto function choices' % sendto_fn_name)
        if sendto_fn_name == cls.SEND_TO_SELF:
            sendto_fn_name = cls.SEND_TO_SELF_REAL
        if not hasattr(esp.dbmail.sendto_fns, sendto_fn_name):
            raise ImproperlyConfigured('"esp.dbmail.sendto_fns" does not define "%s"' % sendto_fn_name)
        sendto_fn_callable = getattr(esp.dbmail.sendto_fns, sendto_fn_name)
        if not callable(sendto_fn_callable):
            raise ImproperlyConfigured('"esp.dbmail.sendto_fns" does not define a "%s" callable sendto function' % sendto_fn_name)
        return sendto_fn_callable

    def get_sendto_fn(self):
        """
        Returns the callable sendto function for this MessageRequest.
        """
        return self.get_sendto_fn_callable(self.sendto_fn_name)

    @classmethod
    def assert_is_valid_sendto_fn_or_ESPError(cls, sendto_fn_name):
        """
        Returns the callable sendto function whose name is the given string.

        If the callable cannot be retrieved, raises an ESPError.
        """
        if sendto_fn_name == cls.SEND_TO_SELF:
            sendto_fn_name = cls.SEND_TO_SELF_REAL
        try:
            return cls.get_sendto_fn_callable(sendto_fn_name)
        except ImproperlyConfigured, e:
            raise ESPError(True, 'Invalid sendto function "%s". ' + \
                'This might be a website bug. Please contact us at %s ' + \
                'and tell us how you got this error, and we will look into it. ' + \
                'The error message is: "%s".' % \
                (sendto_fn_name, DEFAULT_EMAIL_ADDRESSES['support'], e))

    def process(self, processoverride = False):
        """ Process this request...if it's an email, create all the necessary email requests. """

        # if we already processed, return
        if self.processed and not processoverride:
            return

        # there's no real thing for this...yet
        if not self.email_all:
            return

        # this is for thread-safeness...
        self.processed = True
        self.save()

        # figure out who we're sending from...
        if self.sender is not None and len(self.sender.strip()) > 0:
            send_from = self.sender
        else:
            if self.creator is not None:
                send_from = '%s <%s>' % (ESPUser(self.creator).name(), self.creator.email)
            else:
                send_from = 'ESP Web Site <esp@mit.edu>'

        users = self.recipients.getList(ESPUser)
        try:
            users = users.distinct()
        except:
            pass

        sendto_fn = self.get_sendto_fn_callable(self.sendto_fn_name)

        # go through each user and parse the text...then create the proper
        # emailrequest and textofemail object
        for user in users:
            user = ESPUser(user)
            subject = self.parseSmartText(self.subject, user)
            msgtext = self.parseSmartText(self.msgtext, user)

            # For each user, create an EmailRequest and a TextOfEmail
            # for each address given by the output of the sendto function.
            for address_pair in sendto_fn(user):
                newemailrequest = EmailRequest(target = user, msgreq = self)

                newtxt = TextOfEmail(send_to   = ESPUser.email_sendto_address(*address_pair),
                                     send_from = send_from,
                                     subject   = subject,
                                     msgtext   = msgtext,
                                     sent      = None)

                newtxt.save()

                newemailrequest.textofemail = newtxt

                newemailrequest.save()

        print 'Prepared e-mails to send for message request %d: %s' % (self.id, self.subject)


    class Admin:
        pass


class TextOfEmail(models.Model):
    """ Contains the processed form of an EmailRequest, ready to be sent.  SmartText becomes plain text. """
    send_to = models.CharField(max_length=1024)  # Valid email address, "Name" <foo@bar.com>
    send_from = models.CharField(max_length=1024) # Valid email address
    subject = models.TextField() # E-mail subject; plain text
    msgtext = models.TextField() # Message body; plain text
    sent = models.DateTimeField(blank=True, null=True)
    sent_by = models.DateTimeField(null=True, default=None, db_index=True) # When it should be sent by.
    locked = models.BooleanField(default=False)
    tries = models.IntegerField(default=0) # Number of times we attempted to send this message and failed

    def __unicode__(self):
        return unicode(self.subject) + ' <' + (self.send_to) + '>'

    def send(self):
        """ Take the e-mail data contained within this class, put it into a MIMEMultipart() object, and send it """

        parent_request = None
        if self.emailrequest_set.count() > 0:
            parent_request = self.emailrequest_set.all()[0].msgreq
        
        if parent_request is not None:
            extra_headers = parent_request.special_headers_dict
        else:
            extra_headers = {}
        
        now = datetime.now()

        # Before sending the email, check one more time that it hasn't been
        # sent or expired.
        if self.sent is not None:
            return

        send_mail(self.subject,
                  self.msgtext,
                  self.send_from,
                  self.send_to,
                  False,
                  extra_headers=extra_headers)

        self.sent = now
        self.save()

    @classmethod
    def expireUnsentEmails(cls, min_tries=0, orm_class=None):
        """
        For all unsent emails (probably old messages that for some reason were
        never sent), expire them by pretending that they were just sent.  Used
        to prevent old, outdated messages from going out.

        The optional min_tries parameter sets the number of tries that must
        have happened before expiring the message. Defaults to 0, since old
        messages from before the 0003_lock_and_retry_emails migration start
        with 0 tries.

        By default, performs the query using the TextOfEmail model and its
        default Manager. Alternatively, during a migration, a frozen orm class
        can be passed via the orm_class parameter.
        """
        if orm_class is None:
            orm_class = cls
        now = datetime.now()
        return orm_class.objects.filter(Q(sent_by__isnull=True) | Q(sent_by__lt=now), sent__isnull=True, tries__gte=min_tries).update(sent=now)
        
    class Admin:
        pass

    class Meta:
        verbose_name_plural = 'Email Texts'

class MessageVars(models.Model):
    """ A storage of message variables for a specific message. """
    messagerequest = models.ForeignKey(MessageRequest)
    pickled_provider = models.TextField() # Object which must have obj.get_message_var(key)
    provider_name    = models.CharField(max_length=128)
    
    @staticmethod
    def createVar(msgrequest, name, obj):
        """ This is used to create a variable container for a message."""
        import cPickle as pickle

        
        newMessageVar = MessageVars(messagerequest = msgrequest, provider_name = name)
        newMessageVar.pickled_provider = pickle.dumps(obj)

        newMessageVar.save()

        return newMessageVar

    def getDict(self, user):
        import cPickle as pickle
        #try:
        provider = pickle.loads(str(self.pickled_provider))
        #except:
        #    raise ESPError('Coule not load variable provider object!')

        actionhandler = ActionHandler(provider, user)

        
        return {self.provider_name: actionhandler}

    def getVar(self, key, user):
        """ Get a variable from this object. """
        import cPickle as pickle

        try:
            provider = pickle.loads(str(self.pickled_provider))
        except:
            raise ESPError('Could not load variable provider object!')

        if hasattr(provider, 'get_msg_vars'):
            return str(provider.get_msg_vars(user, key))
        else:
            return None

    @staticmethod
    def getContext(msgrequest, user):
        """ Get a context-like dictionary for template rendering. """
        from django.template import Context  ## aseering 8-13-2010 -- Yes, this is supposed to be 'Context', not 'RequestContext'.

        context = {}
        msgvars = msgrequest.messagevars_set.all()
        
        for msgvar in msgvars:
            context.update(msgvar.getDict(user))
        return Context(context)

    @staticmethod
    def createMessageVars(msgrequest, var_dict):
        """ Takes a var_dict, which should be of the form:
            {'FirstHalf': obj, ... }
            Where a variable like {{Program.schedule}} should have:
            {'Program':   programObj ...} and programObj needs to have
            get_msg_vars(userObj, 'schedule') to work
        """    

        # for each module in the dictionary, create a corresponding
        # MessageVar object
        for key, obj in var_dict.items():
            MessageVars.createVar(msgrequest, key, obj)
        

        return True
            
    @staticmethod
    def getModuleVar(msgrequest, varstring, user):
        """ This is used to get the module variable from a string representation. """

        try:
            module, varname = varstring.split('.')
        except:
            raise ESPError('Variable %s not a valid module.var name' % varstring, log=False)

        try:
            msgVar = MessageVars.objects.get(provider_name = module, messagerequest = msgrequest)
        except:
            #raise ESPError("Could not get the variable provider... %s is an invalid variable module." % module, log=False)
            # instead of erroring, I'm just going to ignore it.
            return '{{%s}}' % varstring
    

        result = msgVar.getVar(varname, user)

        if result is None:
            return '{{%s}}' % varstring
        else:
            return result

    class Meta:
        verbose_name_plural = 'Message Variables'


class EmailRequest(models.Model):
    """ Each e-mail is sent to all users in a category.  This a one-to-many that binds a message to the users that it will be sent to. """
    target = AjaxForeignKey(ESPUser)
    msgreq = models.ForeignKey(MessageRequest)
    textofemail = AjaxForeignKey(TextOfEmail, blank=True, null=True)

    def __unicode__(self):
        return unicode(self.msgreq.subject) + ' <' + unicode(self.target.username) + '>'

    class Admin:
        pass




class EmailList(models.Model):
    """
    A list that gets handled when an email comes in to @esp.mit.edu.
    """

    regex = models.CharField(verbose_name='Regular Expression',
            max_length=512, help_text="(e.g. '^(.*)$' matches everything)")

    seq   = models.PositiveIntegerField(blank=True, verbose_name = 'Sequence',
                                        help_text="Smaller is earlier.")

    handler = models.CharField(max_length=128)

    subject_prefix = models.CharField(max_length=64,blank=True,null=True)

    admin_hold = models.BooleanField(default=False)

    cc_all     = models.BooleanField(help_text="If true, the CC field will list everyone. Otherwise each email will be sent individually.", default=False)

    from_email = models.CharField(help_text="If specified, the FROM header will be overwritten with this email.", blank=True, null=True, max_length=512)

    description = models.TextField(blank=True,null=True)

    class Meta:
        ordering=('seq',)

    def save(self, *args, **kwargs):
        if self.seq is None:
            try:
                self.seq = EmailList.objects.order_by('-seq')[0].seq + 5
            except EmailList.DoesNotExist:
                self.seq = 0
            except IndexError:
                self.seq = 0

        super(EmailList, self).save(*args, **kwargs)

    def __unicode__(self):
        return '%s (%s)' % (self.description, self.regex)

class PlainRedirect(models.Model):
    """
    A simple catch-all for mail redirection.
    """

    original = models.CharField(max_length=512)

    destination = models.CharField(max_length=512)

    def __unicode__(self):
        return '%s --> %s'  % (self.original, self.destination)

    class Meta:
        ordering=('original',)


# Adapted from http://www.djangosnippets.org/snippets/735/
class CustomSMTPBackend(SMTPEmailBackend):
    """ Simple override of Django's default backend to allow a Return-Path to be specified """
    
    def __init__(self, return_path=None, **kwargs):
        self.return_path = return_path
        super(CustomSMTPBackend, self).__init__(**kwargs)
        
    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        from_email = sanitize_address(email_message.from_email, email_message.encoding)
        recipients = [sanitize_address(addr, email_message.encoding)
                      for addr in email_message.recipients()]
        try:
            if self.return_path:
                return_path = self.return_path
            else:
                return_path = email_message.from_email
            self.connection.sendmail(sanitize_address(return_path, email_message.encoding),
                    recipients,
                    email_message.message().as_string())
        except:
            if not self.fail_silently:
                raise
            return False
        return True
