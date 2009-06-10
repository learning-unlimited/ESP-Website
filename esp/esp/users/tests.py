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
        assert self.client.login( username='forgetful', password='forgotten_pw' ) == True
        assert self.client.login( username='innocent', password='remembered_pw' ) == True
        
        # Create tickets; both User and ESPUser should work
        one   = PasswordRecoveryTicket.new_ticket( self.user )
        two   = PasswordRecoveryTicket.new_ticket( self.user )
        three = PasswordRecoveryTicket.new_ticket( ESPUser(self.user) )
        four  = PasswordRecoveryTicket.new_ticket( self.other )
        assert one.is_valid() == two.is_valid() == three.is_valid() == four.is_valid() == True
        
        # Try expiring #1; trying to validate it should destroy it
        one.expire = datetime.now()
        assert one.is_valid() == False
        assert one.id is None
        # Try using #1; it shouldn't work
        assert one.change_password( 'forgetful', 'bad_pw' ) == False
        assert self.client.login( username='forgetful', password='bad_pw' ) == False
        
        # Try using #2
        # Make sure it doesn't work for the wrong user
        assert two.change_password( 'innocent', 'bad_pw' ) == False
        assert self.client.login( username='forgetful', password='bad_pw' ) == False
        assert self.client.login( username='innocent', password='bad_pw' ) == False
        # Make sure using it changes the password it's supposed to
        assert two.change_password( 'forgetful', 'new_pw' ) == True
        assert self.client.login( username='forgetful', password='new_pw' ) == True
        assert self.client.login( username='innocent', password='remembered_pw' ) == True
        # Make sure it destroys all other tickets for user forgetful
        assert PasswordRecoveryTicket.objects.filter(user=self.user).count() == 0
        assert PasswordRecoveryTicket.objects.filter(user=self.other).count() == 1
