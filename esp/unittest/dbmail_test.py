import unittest
from esp.dbmail.models import MessageRequest, EmailRequest, TextOfEmail, EmailController

class CreateMessageRequest(unittest.TestCase):
    def runTest(self):
        m = MessageRequest()
        m.subject = 'Sample Subject'
        m.msgtext = 'Sample Message Text'
        m.special_headers = 'X-Sample-Test-Message="True"'
        m.sender = 'test@esp.mit.edu'
        m.save()

        assert MessageRequest.objects.filter(
            subject='Sample Subject',
            msgtext='Sample Message Text',
            special_headers='X-Sample-Test-Message="True"',
            sender='test@esp.mit.edu'
            ).count() == 1 ,
            'Can\'t find saved message in ' + str(MessageRequest.objects.all())

