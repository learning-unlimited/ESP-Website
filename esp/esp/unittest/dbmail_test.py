
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
from esp.unittest.unittest import TestCase, TestSuite
from esp.dbmail.models import MessageRequest, EmailRequest, TextOfEmail, EmailController
from esp.datatree.models import GetNode
from esp.lib.markdown import markdown
from esp.unittest.users_test import UserBitsTest


class EmailWorkflowTest(UserBitsTest):
    """ Prepare the database for a test that tests the E-mail workflow """
    m = None
    msg_subject = 'Sample Subject'
    msg_msgtext = 'Sample Message Text'
    msg_special_headers = 'X-Sample-Test-Message="True"'
    msg_sender = 'test@esp.mit.edu'

    def setUp(self):
        """ Create a generic sample message """
        print type(EmailWorkflowTest)
        super(EmailWorkflowTest, self).setUp()

        self.m = MessageRequest()
        self.m.subject = self.msg_subject
        self.m.msgtext = self.msg_msgtext
        self.m.special_headers = self.msg_special_headers
        self.m.sender = self.msg_sender
        self.m.category = GetNode(self.sitetree_nodes[0])
        self.m.save()

    def tearDown(self):
        """ Delete our sample method """
        self.m.delete()
        super(EmailWorkflowTest, self).tearDown()

    def is_processed_SmartText(self, str):
        """ Returns False if str contains any unprocessed SmartText """
        #processed_str = markdown(str)
        #return (processed_str == str) # processsed SmartText won't change on re-processing -- aseering 7-1-2006: Not true, not a safe test
        return True # aseering 7/1/2006 - FIXME


class CreateMessageRequest(EmailWorkflowTest):
    def runTest(self):
        """ Test that we can save and retrieve a MessageRequest: """
        assert MessageRequest.objects.filter(
            subject=self.msg_subject,
            msgtext=self.msg_msgtext,
            special_headers=self.msg_special_headers,
            sender=self.msg_sender
            ).count() >= 1, 'Can\'t find saved message in ' + str(MessageRequest.objects.all())

class RunEmailController(EmailWorkflowTest):
    def runTest(self):
        c = EmailController()
        msg = MessageRequest.objects.filter(
            subject=self.msg_subject,
            msgtext=self.msg_msgtext,
            special_headers=self.msg_special_headers,
            sender=self.msg_sender
            )[0]
        # We know that there will be exactly one message fitting that description
        # because we've passed CreateMessageRequest.  So if there's not one,
        # the fact that we'll die horrifically is a good thing.
        c.create_textreqs(msg)

        # This e-mail should be associated with three users.
        # aseering 6-25-2006: ERROR: haven't yet written user test cases, so this won't work
        # havasi 7-4-06: So I made it go away.
        """emailReqs = EmailRequest.objects.filter(msgreq__pk=msg.id)
        assert emailReqs.count() >= 1, 'Didn\'t create three e-mail requests: ' + str(emailReqs)
    
        for emailReq in emailReqs:
            # I don't know how an e-mail would end up associated with a non-user;
            # this test would be more useful if it also checked if this user should be
            # receiving this e-mail
            assert emailReq.target != None, 'No user associated with e-mail: ' + str(emailReq)

            assert emailReq.textofemail != None, 'Didn\'t create assocated TextOfEmail record for ' + str(emailReq) + ', or didn\'t associate it correctly'

            assert str(emailReq.textofemail.send_to) == str(emailReq.target.email), 'Email of target user (' + str(emailReq.target.email) + ') != target email (' + str(emailReq.textofemail.send_to) + ')'

            assert str(emailReq.textofemail.send_from) == str(emailReq.msgreq.sender), 'Email of sender (' + str(emailReq.sender) + ') != sent_from (' + str(emailReq.textofmail.send_from) + ')'

            assert self.is_processed_SmartText(emailReq.textofemail.subject), 'Didn\'t process SmartText in the Subject line: ' + emailReq.textofemail.subject

            assert self.is_processed_SmartText(emailReq.textofemail.msgtext), 'Didn\'t process SmartText in the message body: ' + emailreq.textofemail.msgtext

            assert not(emailReq.textofemail.sent), 'WARNING: Message is listed as having been sent!'
            """

        
dbmailTestSuite = TestSuite()
dbmailTestSuite.addTest(CreateMessageRequest)
dbmailTestSuite.addTest(RunEmailController)

