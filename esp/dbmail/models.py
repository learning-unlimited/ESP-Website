from django.db import models
from django.contrib.auth.models import User

from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from datetime import datetime
from email.Utils import formatdate
from esp.lib.markdown import markdown

#import smtplib

from django.core.mail import send_mail

from esp.workflow.models import Controller
from esp.datatree.models import DataTree, GetNode, StringToPerm, PermToString
from esp.users.models import UserBit

smtp_server = 'outgoing.mit.edu'

# Create your models here.

class MessageRequest(models.Model):
    """ An initial request to broadcast an e-mail message """
    # I'm a bit confused on how you get two different pieces of text from models.TextField() - Catherine
    subject = models.TextField() # Message "Subject" line, can be SmartText
    msgtext = models.TextField() # Text of the message; can be SmartText
    special_headers = models.TextField(blank=True) # Any special e-mail headers, formatted so that they can be concatenated into the message
    category = models.ForeignKey(DataTree, null=True, blank=True) # Category of users who should receive this message.  Note that it's not possible to specify a specific user, unless we implement per-user categories.
    sender = models.TextField() # E-mail sender; should be a valid SMTP sender string
    def __str__(self):
        return str(self.subject)

    class Admin:
        pass

class EmailRequest(models.Model):
    """ Each e-mail is sent to all users in a category.  This a one-to-many that binds a message to the users that it will be sent to. """
    target = models.ForeignKey(User)
    msgreq = models.ForeignKey(MessageRequest)
    def __str__(self):
        return str(self.msgreq.subject) + ' <' + str(self.target.username) + '>'

    class Admin:
        pass

class TextOfEmail(models.Model):
    """ Contains the processed form of an EmailRequest, ready to be sent.  SmartText becomes plain text. """
    send_to = models.EmailField()
    send_from = models.EmailField()
    subject = models.TextField() # E-mail subject; plain text
    msgtext = models.TextField() # Message body; plain text
    sent = models.DateTimeField(blank=True, null=True)
    emailReq = models.OneToOneField(EmailRequest)

    def __str__(self):
        return str(self.subject) + ' <' + str(self.send_to) + '>'

    def send(self):  # Code flagrantly pulled from http://www.bigbold.com/snippets/posts/show/2038
        """ Take the e-mail data contained within this class, put it into a MIMEMultipart() object, and send it """
        now = datetime.now()

        send_mail(str(self.subject),
                  '<html>' + str(self.msgtext) + '</html>',
                  str(self.send_from),
                  [ str(self.send_to) ],
                  fail_silently=False )

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


class EmailController(Controller):
    """ The workflow for a broadcast e-mail (distinct from e-mail sent to a specific user)

    The workflow works as follows:
    - Get the list of users subscribed to the MessageRequest's category
    - Spawn a list of EmailRequests for this list of users
    - Process the SmartText in the EmailRequests, and generate a corresponding list of TextOfEmails
    - Send the TextOfEmails
    """

    def apply_smarttext(self, smartstr):
        """ Takes either a plain string or a SmartText-encoded string.  Returns a plain string.  """
        return markdown(smartstr)

    def msgreq_to_emailreqs(self, msgreq):
        """ Accepts a MessageRequest.  Returns a list of EmailRequests.

        Given a MessageRequest, get the users subscribed to it, and return a set of EmailRequests that bind each of those users to the specified MessageRequest """
        emailreqs = []

        if msgreq.category == None:
            emailreqs = EmailRequest.objects.filter(msgreq=msgreq)
        else:
            for user in UserBit.bits_get_users(msgreq.category, GetNode('V/dbmail/Subscribe')):
                temp_emailreq = EmailRequest()
                temp_emailreq.target = user.user.user
                temp_emailreq.msgreq = msgreq
                temp_emailreq.save()
                emailreqs.append(temp_emailreq)

        return emailreqs

    def emailreq_to_textreq(self, emailreq):
        """ Accepts an EmailRequest.  Returns a TextToEmail.

        Given an EmailRequest, make a TextToEmail object.  Pull text from the EmailRequest's associated MessageRequest and do SmartText processing as necessary. """
        textreq = TextOfEmail()
        textreq.send_to = str(emailreq.target.email)
        textreq.send_from = str(emailreq.msgreq.sender)
        textreq.subject = str(emailreq.msgreq.subject)
        textreq.msgtext = self.apply_smarttext(str(emailreq.msgreq.msgtext))
        textreq.emailReq = emailreq
        textreq.save()
        return textreq
    
    def create_textreqs(self, data):
        """ Create TextRequests to send (like run()), but don't actually send them """
        emailreqs = self.msgreq_to_emailreqs(data)

        textreqs = []
        for emailreq in emailreqs:
            textreqs.append(self.emailreq_to_textreq(emailreq))

        return textreqs

    def run(self, data):
        """ Accepts a MessageRequest.

        Given a MessageRequest, generates and sends e-mails based on this request. """
        # Do we want to send automatically/immediately?
        for textreq in self.create_textreqs(data):
            textreq.send()
