from django.db import models
from django.contrib.auth.models import User

from datetime import datetime
from esp.lib.markdown import markdown

import django.core.mail

from esp.datatree.models import DataTree, GetNode, StringToPerm, PermToString
from esp.users.models import UserBit


def send_mail(subject, message, from_email, recipient_list,
              fail_silently=False, *args, **kwargs):
    new_list = [ x for x in recipient_list ]
    new_list.append('esparchive@gmail.com')

    from django.core.mail import send_mail as django_send_mail
    django_send_mail(subject, message, from_email, new_list,
                               fail_silently, *args, **kwargs)
    


# Create your models here.

class MessageRequest(models.Model):
    """ An initial request to broadcast an e-mail message """
    # I'm a bit confused on how you get two different pieces of text from models.TextField() - Catherine
    subject = models.TextField() # Message "Subject" line, can be SmartText
    msgtext = models.TextField() # Text of the message; can be SmartText
    special_headers = models.TextField(blank=True) # Any special e-mail headers, formatted so that they can be concatenated into the message
    category = models.ForeignKey(DataTree, null=True, blank=True) # Category of users who should receive this message.  Note that it's not possible to specify a specific user, unless we implement per-user categories.
    sender = models.TextField() # E-mail sender; should be a valid SMTP sender string
    processed = models.BooleanField(default=False) # Have we made EmailRequest objects from this MessageRequest yet?
                                      # Different from "self.emailrequest_set().count() == 0" because it's possible that a MessageRequest will not incur any EmailRequests.

    priority_level = models.IntegerField(null=True, blank=True) # Priority of a message; may be used in the future to make a message non-digested, or to prevent a low-priority message from being sent

    def __str__(self):
        return str(self.subject)

    class Admin:
        pass


class TextOfEmail(models.Model):
    """ Contains the processed form of an EmailRequest, ready to be sent.  SmartText becomes plain text. """
    send_to = models.EmailField()
    send_from = models.EmailField()
    subject = models.TextField() # E-mail subject; plain text
    msgtext = models.TextField() # Message body; plain text
    sent = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return str(self.subject) + ' <' + str(self.send_to) + '>'

    def send(self):
        """ Take the e-mail data contained within this class, put it into a MIMEMultipart() object, and send it """
        now = datetime.now()

        #send_mail(str(self.subject),
        #          str(self.msgtext),
        #          str(self.send_from),
        #          [ str(self.send_to) ],
        #          fail_silently=False )
        
        #message = MIMEMultipart()
        #message['To'] = str(self.send_to)
        #message['From'] = str(self.send_from)
        #message['Date'] = formatdate(localtime=True, timeval=now)
        #message['Subject'] = str(self.subject)
        #message.attach( MIMEText(str(self.msgtext)) )
        #print str(self.send_from) + ' | ' + str(self.send_to) + ' | ' + message.as_string() + "\n"
        # aseering: Code currently commented out because we're debugging this.  It might break and, say, spam esp-webmasters.  That would be bad.
        #sendvia_smtp = smtplib.SMTP(smtp_server)
        #sendvia_smtp.sendmail(str(self.send_from), str(self.send_to), message.as_string())
        #sendvia_smtp.close()

        self.sent = now
        self.save()
        
    class Admin:
        pass



class EmailRequest(models.Model):
    """ Each e-mail is sent to all users in a category.  This a one-to-many that binds a message to the users that it will be sent to. """
    target = models.ForeignKey(User)
    msgreq = models.ForeignKey(MessageRequest)
    textofemail = models.ForeignKey(TextOfEmail, blank=True, null=True)
    def __str__(self):
        return str(self.msgreq.subject) + ' <' + str(self.target.username) + '>'

    class Admin:
        pass
