
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
"""
from esp.lib.markdown import markdown
from esp.workflow.models import Controller
from esp.datatree.models import GetNode
from esp.users.models import UserBit
from esp.dbmail.models import MessageRequest, TextOfEmail, EmailRequest

class EmailController(Controller):
    """ The workflow for a broadcast e-mail (distinct from e-mail sent to a specific user)
    
    The workflow works as follows:
    - Get the list of users subscribed to the MessageRequest's category
    - Spawn a list of EmailRequests for this list of users
    - Process the SmartText in the EmailRequests, and generate a corresponding list of TextOfEmails
    - Send the TextOfEmails
    """

    force_digest = False

    def __init__(self, force_digest=False):
        super(EmailController, self).__init__()

        self.force_digest = force_digest

    def apply_smarttext(self, smartstr):
        """ Takes either a plain string or a SmartText-encoded string.  Returns a plain string.  """
        return markdown(smartstr)

    def msgreq_to_emailreqs(self, msgreq):
        """ Accepts a MessageRequest.  Returns a list of EmailRequests.

        Given a MessageRequest, get the users subscribed to it, and return a set of EmailRequests that bind each of those users to the specified 
MessageRequest """
        emailreqs = []

        if msgreq.category == None:
            emailreqs = EmailRequest.objects.filter(msgreq=msgreq)

            msgreq.processed = True
            msgreq.save()
        else:
            for user in UserBit.bits_get_users(msgreq.category, GetNode('V/Subscribe')):
                temp_emailreq = EmailRequest()
                temp_emailreq.target = user.user
                temp_emailreq.msgreq = msgreq
                temp_emailreq.save()
                emailreqs.append(temp_emailreq)

                msgreq.processed = True
                msgreq.save()

        return emailreqs

    def emailreqs_to_textreqs(self, emailreqs):
        """ Accepts an EmailRequest.  Returns a TextToEmail.

        Given an EmailRequest, make a TextToEmail object.  Pull text from the EmailRequest's associated MessageRequest.

        If a user wants a digest of the specified node, queue that message to be digested; if we're sending digested messages, after scanning all messages, send the digest queue"""

        user_msgs = { }
        textreqs = []

        for emailreq in emailreqs:
            # Default node is Q/Event, because we're not always associating events with nodes.  That should probably change.
            if emailreq.msgreq.category == None:
                node = GetNode('Q/Event')
            else:
                node = emailreq.msgreq.category

            # If the user wants digests on the specified node, queue this message for digest
            if UserBit.UserHasPerms(emailreq.target, node, GetNode('V/Digest')):
                # Only queue if we're dealing with digests right now
                if self.force_digest:
                    if not user_msgs.has_key(emailreq.target):
                        user_msgs[emailreq.target] = []

                    user_msgs[emailreq.target].append(emailreq)
            else:
                # Dump our data into a textreq
                textreq = TextOfEmail()
                textreq.send_to = str(emailreq.target.email)
                textreq.send_from = str(emailreq.msgreq.sender)
                textreq.subject = str(emailreq.msgreq.subject)
                textreq.msgtext = str(emailreq.msgreq.msgtext)
                textreq.save()

                emailreq.textofemail = textreq
                emailreq.save()

                textreqs.append(textreq)

        # Handle digested messages
        if self.force_digest:
            # For each user with a requested digest, first generate a TextOfEmail for them.
            # Second, iterate through all emailreqs that this person is to receive,
            #  gather their msgtext, and encode the text into a string, to be the
            #  digest message's body.  Associate all emailreqs with this new TextOfEmail
            # Finally, save the body into the TextOfEmail, and add the TextOfEmail to the
            #  list of texts to be sent

            for user in user_msgs.keys():
                msg_text = "Daily Digest\n============\n\n"
                
                # Generate a shell TextOfEmail
                textreq = TextOfEmail()
                textreq.send_to = str(user.email)
                textreq.send_from = 'ESP Mailer Daemon <esp@mit.edu>'
                textreq.subject = 'Daily ESP E-mail Digest'
                textreq.msgtext = ' '
                textreq.save()

                # Pull data to send in the e-mail
                for emailreq in user_msgs[user]:
                    msg_text.append("Subject: " + emailreq.msgreq.subject + "\n\n"
                                    + "Message:\n" + emailreq.msgreq.msgtext
                                    + '-'*30)
                    emailreq.textofemail = textreq
                    emailreq.save()

                # Finalize the TextOfEmail
                textreq.msgtext = msg_text
                textreq.save()
                
                textreqs.append(textreq)

        return textreqs

    def create_textreqs(self, data = None):
        """ Create TextRequests to send (like run()), but don't actually send them """
        
        emailreqs = []
        
        if data == None:
            for m in MessageRequest.objects.filter(processed=False):
                emailreqs += self.msgreq_to_emailreqs(m)
        else:
            for m in data:
                emailreqs += self.msgreq_to_emailreqs(m)

        return self.emailreqs_to_textreqs(emailreqs)

    def run(self, data = None):
        """ Accepts a MessageRequest.

        Given a MessageRequest, generates and sends e-mails based on this request. """
        # Do we want to send automatically/immediately?
        for textreq in self.create_textreqs(data):
            textreq.send()

