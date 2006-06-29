from esp.unittest.unittest import TestCase, TestSuite

from esp.unittest.watchlists_test import TreeTest
from esp.users.models import ESPUser, UserBit
from django.contrib.auth.models import User

class UserTest(TestCase):
    users = (
        ('test1', 'pass1'),
        ('test2', 'pass2'),
        ('test3', 'pass3'),
        ('Fred', 'none'),
        ('Bob', 'password'),
        ('Joe', 'kc sdklnmawefovsdmlkasdmkfla;wefcvm zkido as;3ear;j a340wwei9f0a'),
        )

    saved_users = []

    def setUp(self):
        """ Create and link ESP users """
        for u in self.users:
            django_user = User()
            django_user.username = u[0]
            django_user.set_password(u[1])
            django_user.save()

            u = ESPUser()
            u.user = django_user
            u.save()
        
            self.saved_users.append( [ [django_user, u] ] )

    def tearDown(self):
        """ Remove our sample users """
        for user_set in self.saved_users:
            user_set[1].delete()
            user_set[0].delete()

class UserBitsTest(UserTest, TreeTest):
    bits = []
    
    def setUp(self):
        """ Create an arbitrary set of user bits, based on currently-existing data """
        len = min(len(self.users), len(self.usergrouptree_nodes), len(sitetree.nodes))
        for i in range(0,len):
            bit = UserBit()
            bit.user = self.users[i]
            bit.permission = self.sitetree_nodes[i]
            bit.subject = self.usergrouptree_nodes[i]
            bit.save()

            self.bits.append( [bit] )
        
    def tearDown(self):
        """ Get rid of the users that we created in setUp() """
        for bit in self.bits:
            bit.delete()

