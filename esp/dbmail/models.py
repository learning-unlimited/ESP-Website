from django.db import models
from django.contrib.auth.models import User

from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from datetime import datetime

import smtplib



smtp_server = 'outgoing.mit.edu'

# Create your models here.

class MessageRequest(models.Model):
    subject = models.TextField()
    msgtext = models.TextField()
    special_headers = models.TextField()
    # category = models.ForeignKey(Category) # we haven't defined Category yet
    category = models.IntegerField()
    sender = models.TextField()
    class Admin:
        pass

class EmailRequest(models.Model):
    target = models.ForeignKey(User)
    msgreq = models.ForeignKey(MessageRequest)
    class Admin:
        pass

class TextOfEmail(models.Model):
    send_to = models.EmailField()
    send_from = models.EmailField()
    subject = models.TextField()
    msgtext = models.TextField()
    sent = models.DateTimeField() #default=datetime.max)

    def send(self):  # Code flagrantly pulled from http://www.bigbold.com/snippets/posts/show/2038
        self.sent = datetime.now()
        message = MIMEMultipart()
        message['To'] = str(self.send_to)
        message['From'] = str(self.send_from)
        message['Date'] = str(self.sent)
        message['Subject'] = str(self.subject)
        message.attach( MIMEText(str(self.msgtext)) )

        sendvia_smtp = smtplib.SMTP(smtp_server)
        print str(self.send_from) + ' | ' + str(self.send_to) + ' | ' + message.as_string() + "\n"
        sendvia_smtp.sendmail(str(self.send_from), str(self.send_to), message.as_string())
        sendvia_smtp.close()
        
    class Admin:
        pass
