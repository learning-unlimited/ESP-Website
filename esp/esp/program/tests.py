from django.contrib.auth.models import User,Group
import datetime, random, hashlib
import unittest

class ProfileTest(unittest.TestCase):

    def setUp(self):
        self.salt = hashlib.sha1(str(random.random())).hexdigest()[:5]

    def testAcctCreate(self):
        self.u=User(
            first_name='bob',
            last_name='jones',
            username='bjones',
            email='test@bjones.com',
            # is_staff=True,
        )
        self.u.set_password('123!@#')
        self.u.save()
        self.group=Group(name='Test Group')
        self.group.save()
        self.u.groups.add(self.group)
        self.assertEquals(User.objects.get(username='bjones'), self.u)
        self.assertEquals(Group.objects.get(name='Test Group'), self.group)
        print self.u.__dict__
        print self.u.groups.all()

