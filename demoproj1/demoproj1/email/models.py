from django.db import models
from django.contrib.auth.models import User

import smtplib
from email.MIMEMultiPart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from datetime import datetime

smtp_server = 'outgoing.mit.edu'

# Create your models here.

class MessageSender:
    sender_addr = ''
    def __str__(self):
        return sender_addr

class MessageRequest(models.Model):
    subject = models.TextField()
    msgtext = models.TextField()
    special_headers = models.TextField()
    # category = models.ForeignKey(Category) # we haven't defined Category yet
    category = models.IntegerField()
    sender = models.TextField()

class EmailRequest(models.Model):
    target = models.ForeignKey(User)
    msgreq = models.ForeignKey(MessageRequest)

class TextOfEmail(models.Model):
    send_to = models.EmailField()
    send_from = models.EmailField()
    subject = models.TextField()
    msgtext = models.TextField()
    sent = models.DateTimeField(default=datetime.max)

    def send(self):
        # Code flagrantly pulled from http://www.bigbold.com/snippets/posts/show/2038
        sent = datetime.now()
        message = MIMEMultipart()
        message['To'] = str(send_to)
        message['From'] = str(send_from)
        message['Date'] = sent
        message['Subject'] = subject
        msg.attach( MIMEText(msgtext) )

        sendvia_smtp = smtplib.SMTP(smtp_server)
        smtp.sendmail(send_from, send_to, msg.as_string())
        smtp.close()
