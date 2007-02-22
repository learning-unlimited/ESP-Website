from django.db import models
from django.contrib.auth.models import User

from datetime import datetime
from esp.lib.markdown import markdown


import django.core.mail

from esp.datatree.models import DataTree, GetNode, StringToPerm, PermToString
from esp.users.models import UserBit, PersistentQueryFilter, ESPUser
from django.template import Template, VariableNode, TextNode

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
    subject = models.TextField(null=True,blank=True) 
    msgtext = models.TextField(blank=True, null=True) 
    special_headers = models.TextField(blank=True, null=True) 
    recipients = models.ForeignKey(PersistentQueryFilter) # We will get the user from a query filter
    sender = models.TextField(blank=True, null=True) # E-mail sender; should be a valid SMTP sender string 
    creator = models.ForiegnKey(User,blank=True, null=True) # the person who sent this message
    processed = models.BooleanField(default=False) # Have we made EmailRequest objects from this MessageRequest yet?
    email_all = models.BooleanField(default=True) # do we just want to create an emailrequest for each user?
    priority_level = models.IntegerField(null=True, blank=True) # Priority of a message; may be used in the future to make a message non-digested, or to prevent a low-priority message from being sent

    def __str__(self):
        return str(self.subject)

    def __init__(self, var_dict, *args, **kwargs):

        super(MessageRequest, self).__init__(*args, **kwargs)

        self.save()

        MessageVars.createMessageVars(self, var_dict) # create the message Variables

    def parseSmartText(self, text, user):
        """ Takes a text and user, and, within the confines of this message, will make it better. """

        # prepare variables
        text = str(text)
        user = ESPUser(user)

        newtext = ''
        template = Template(text)
        for node in template.nodelist:
            # loop through each node, ignore if not var or string.
            if type(node) == TextNode:
                newtext += node.s
            elif type(node) == VariableNode:
                newtext += node.filter_expression.var

        return newtext
                
        

    def process(self):
        """ Process this request...if it's an email, create all the necessary email requests. """

        # if we already processed, return
        if self.processed:
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


        users = self.recipients.getList(User)
        
        # go through each user and parse the text...then create the proper
        # emailrequest and textofemail object
        for user in users:
            user = ESPUser(user)
            newemailrequest = EmailRequest(target = user, msgreq = self)
            
            newtxt = TextOfEmail(send_to   = '%s <%s>' % (user.name(), user.email),
                                 send_from = send_from,
                                 subject   = self.parseSmartText(self.subject, user),
                                 msgtext   = self.parseSmartText(self.msgtext, user),
                                 sent      = None)

            newtxt.save()

            newemailrequest.textofemail = newtxt

            newemailrequest.save()

            
            
  target = models.ForeignKey(User)
      msgreq 

    class Admin:
        pass


class TextOfEmail(models.Model):
    """ Contains the processed form of an EmailRequest, ready to be sent.  SmartText becomes plain text. """
    send_to = models.CharField(length=64)  # Valid email address, "Name" <foo@bar.com>
    send_from = models.CharField(length=64) # Valid email address
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


class MessageVars(models.Model):
    """ A storage of message variables for a specific message. """
    messagerequest = models.ForeignKey(MessageRequest)
    pickled_provider = models.TextField() # Object which must have obj.get_message_var(key)
    provider_name    = models.CharField(maxlength=128)
    
    @staticmethod
    def createVar(msgrequest, name, obj):
        """ This is used to create a variable container for a message."""
        import pickle

        
        newMessageVar = MessageVars(messagerequest = msgrequest, provider_name = name)
        newMessageVar.pickled_provider = pickle.dumps(obj)

        newMessageVar.save()

        return newMessageVar

    def getVar(self, key, user):
        """ Get a variable from this object. """
        import pickle

        try:
            provider = pickle.loads(self.pickled_provider)
        except:
            raise ESPError(), 'Could not load variable provider object!'

        if hasattr(provider, 'get_msg_vars'):
            return str(provider.get_msg_vars(user, key))
        else:
            return None

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
            raise ESPError(False), 'Variable %s not a valid module.var name' % varstring

        try:
            msgVar = MessageVars.objects.get(provider_name = module, messagerequest = msgrequest)
        except:
            raise ESPError(False), "Could not get the variable provider... %s is an invalid variable module." % module

        result = msgVar.getVar(varname, user)

        if result is None:
            return '{{%s}}' % varstring
        else:
            return result

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
