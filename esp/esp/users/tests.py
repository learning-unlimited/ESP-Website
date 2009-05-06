from django.test import TestCase
from esp.users.models import User, ESPUser

class ESPUser__inittest(TestCase):
    def runTest(self):
        one = ESPUser()
        two = User()
        three = ESPUser(two)
