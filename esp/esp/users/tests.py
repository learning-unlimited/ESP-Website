from django.test import TestCase
from esp.users.models import User, ESPUser, PasswordRecoveryTicket

class ESPUser__inittest(TestCase):
    def runTest(self):
        one = ESPUser()
        two = User()
        three = ESPUser(two)
        four = ESPUser(three)
        assert three.__dict__ == four.__dict__

class PasswordRecoveryTicketTest(TestCase):
    def setUp(self):
        self.user, created = User.objects.get_or_create(username='forgetful')
        self.user.set_password('forgotten_pw')
        self.user.save()
        self.other, created = User.objects.get_or_create(username='innocent')
        self.other.set_password('remembered_pw')
        self.other.save()
    def runTest(self):
        from datetime import datetime
        
        # First, make sure both people can log in
        self.assertTrue(self.client.login( username='forgetful', password='forgotten_pw' ), "User forgetful cannot login")
        self.assertTrue(self.client.login( username='innocent', password='remembered_pw' ), "User innocent cannot login")
        
        # Create tickets; both User and ESPUser should work
        one   = PasswordRecoveryTicket.new_ticket( self.user )
        two   = PasswordRecoveryTicket.new_ticket( self.user )
        three = PasswordRecoveryTicket.new_ticket( ESPUser(self.user) )
        four  = PasswordRecoveryTicket.new_ticket( self.other )
        self.assertTrue(one.is_valid(), "Recovery ticket one is invalid.")
        self.assertTrue(two.is_valid(), "Recovery ticket two is invalid.")
        self.assertTrue(three.is_valid(), "Recovery ticket three is invalid.")
        self.assertTrue(four.is_valid(), "Recovery ticket four is invalid.")
        
        # Try expiring #1; trying to validate it should destroy it
        one.expire = datetime.now()
        self.assertFalse(one.is_valid(), "Expired ticket is still valid.")
        self.assertEqual(one.id, None, "Ticket was not auto-deleted.")
        # Try using #1; it shouldn't work
        self.assertFalse(one.change_password( 'forgetful', 'bad_pw' ), "Expired ticket still changed password.")
        self.assertFalse(self.client.login( username='forgetful', password='bad_pw' ), "User forgetful logged in with incorrect password.")
        
        # Try using #2
        # Make sure it doesn't work for the wrong user
        self.assertFalse(two.change_password( 'innocent', 'bad_pw' ), "Recovery ticket two used for the wrong user.")
        self.assertFalse(self.client.login( username='forgetful', password='bad_pw' ), "Incorrectly cashed ticket still changed password.")
        self.assertFalse(self.client.login( username='innocent', password='bad_pw' ), "User innocent's password changed.")
        # Make sure using it changes the password it's supposed to
        self.assertTrue(two.change_password( 'forgetful', 'new_pw' ), "Recovery ticket two failed to be cashed.")
        self.assertTrue(self.client.login( username='forgetful', password='new_pw' ), "User forgetful cannot login with new password.")
        self.assertTrue(self.client.login( username='innocent', password='remembered_pw' ), "User innocent's old password no longer works.")
        # Make sure it destroys all other tickets for user forgetful
        self.assertEqual(PasswordRecoveryTicket.objects.filter(user=self.user).count(), 0, "Tickets for user forgetful not wiped.")
        self.assertEqual(PasswordRecoveryTicket.objects.filter(user=self.other).count(), 1, "Tickets for user innocent incorrectly wiped.")
