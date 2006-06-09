from django.db import models
from django.contrib.auth.models import User

from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from datetime import datetime
from email.Utils import formatdate

import smtplib

from esp.workflow.models import Controller
from esp.watchlists.models import Category, Subscription, Datatree

smtp_server = 'outgoing.mit.edu'

# Create your models here.

class MessageRequest(models.Model):
    subject = models.TextField()
    msgtext = models.TextField()
    special_headers = models.TextField(blank=True)
    category = models.ForeignKey(Category)
    sender = models.TextField()
    def __str__(self):
        return str(self.subject)

    class Admin:
        pass

class EmailRequest(models.Model):
    target = models.ForeignKey(User)
    msgreq = models.ForeignKey(MessageRequest)
    def __str__(self):
        return str(self.msgreq.subject) + ' <' + str(self.target.username) + '>'

    class Admin:
        pass

class TextOfEmail(models.Model):
    send_to = models.EmailField()
    send_from = models.EmailField()
    subject = models.TextField()
    msgtext = models.TextField()
    sent = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return str(self.subject) + ' <' + str(self.send_to) + '>'

    def send(self):  # Code flagrantly pulled from http://www.bigbold.com/snippets/posts/show/2038
        now = datetime.now()
        message = MIMEMultipart()
        message['To'] = str(self.send_to)
        message['From'] = str(self.send_from)
        message['Date'] = formatdate(localtime=True, timeval=now)
        message['Subject'] = str(self.subject)
        message.attach( MIMEText(str(self.msgtext)) )
        print str(self.send_from) + ' | ' + str(self.send_to) + ' | ' + message.as_string() + "\n"
        #sendvia_smtp = smtplib.SMTP(smtp_server)
        #sendvia_smtp.sendmail(str(self.send_from), str(self.send_to), message.as_string())
        #sendvia_smtp.close()
        self.sent = now
        self.save()
        
    class Admin:
        pass


class EmailController(Controller):
    def users_subscribed_to(self, category):
        user = []
        for orig_node in Datatree.objects.filter(node_data__category__pk=category.id):
            for node in Datatree.objects.filter(rangestart__gte=orig_node.rangestart, rangeend__lte=orig_node.rangeend):
#Subscription.objects.filter(category__rangestart__gte=category.rangestart, category__rangestart__lte=category.rangeend):
#Subscription.objects.filter(category__pk=category_id):
                for sub in Subscription.objects.filter(category__pk=node.node_data.category.id):
                    user.append(sub.user)

        return user    

    # Blatant shell function
    def apply_smarttext(self, smartstr):
        return smartstr

    def msgreq_to_emailreqs(self, msgreq):
        emailreqs = []

        for user in self.users_subscribed_to(msgreq.category):
            temp_emailreq = EmailRequest()
            temp_emailreq.target = user
            temp_emailreq.msgreq = msgreq
            temp_emailreq.save()
            emailreqs.append(temp_emailreq)

        return emailreqs

    def emailreq_to_textreq(self, emailreq):
        textreq = TextOfEmail()
        textreq.send_to = str(emailreq.target.email)
        textreq.send_from = str(emailreq.msgreq.sender)
        textreq.subject = self.apply_smarttext(str(emailreq.msgreq.subject))
        textreq.msgtext = self.apply_smarttext(str(emailreq.msgreq.msgtext))
        textreq.save()
        return textreq
        
    def run(self, data):
        emailreqs = self.msgreq_to_emailreqs(data)

        textreqs = []
        for emailreq in emailreqs:
            textreqs.append(self.emailreq_to_textreq(emailreq))

        # Do we want to send automatically/immediately?
        #for textreq in textreqs:
        #    textreq.send()
