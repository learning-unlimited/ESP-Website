from esp.tests.util import CacheFlushTestCase as TestCase, user_role_setup
from django import forms
from esp.users.models import User, ESPUser, PasswordRecoveryTicket, UserBit, UserForwarder, StudentInfo
from esp.users.forms.user_reg import ValidHostEmailField
from esp.program.tests import ProgramFrameworkTest
from esp.datatree.models import GetNode
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.models import Group
from esp.middleware import ESPError
from esp.users.views import make_user_admin
from django.core import mail
from esp.program.models import RegistrationProfile, Program
import datetime
import esp.users.views as views
from esp.tagdict.models import Tag

class ESPUserTest(TestCase):
    def setUp(self):
        user_role_setup()

    def testInit(self):
        one = ESPUser()
        two = User()
        three = ESPUser(two)
        four = ESPUser(three)
        self.failUnless( three.__dict__ == four.__dict__ )

    def testDelete(self):
        from esp.datatree.models import GetNode
        from esp.users.models import UserBit
        # Create a user and a userbit
        self.user, created = ESPUser.objects.get_or_create(username='forgetful')
        self.userbit = UserBit.objects.get_or_create(user=self.user, verb=GetNode('V/Administer'), qsc=GetNode('Q'))
        # Save the ID and then delete the user
        uid = self.user.id
        self.user.delete()
        # Make sure it's gone.
        self.failUnless( User.objects.filter(id=uid).count() == 0 )
        self.failUnless( ESPUser.objects.filter(id=uid).count() == 0 )
        self.failUnless( UserBit.objects.filter(user=uid).count() == 0 )

    def testMorph(self):
        class scratchCls(object):
            pass
        class scratchDict(dict):
            def cycle_key(self):
                pass
            def flush(self):
                for i in self.keys():
                    del self[i]

        # Make up a fake request object
        # This definitely doesn't meet the spec of the real request object;
        # if tests fail as a result in the future, it'll need to be fixed.
        request = scratchCls()

        request.backend = 'django.contrib.auth.backends.ModelBackend'
        request.user = None
        request.session = scratchDict()

        # Create a couple users and a userbit
        self.user, created = ESPUser.objects.get_or_create(username='forgetful')
        self.userbit = UserBit.objects.get_or_create(user=self.user, verb=GetNode('V/Administer'), qsc=GetNode('Q'))

        self.basic_user, created = ESPUser.objects.get_or_create(username='simple_student')
        self.userbit = UserBit.objects.get_or_create(user=self.basic_user, verb=GetNode('V/Flags/UserRole/Student'), qsc=GetNode('Q'))

        self.user.backend = request.backend
        self.basic_user.backend = request.backend

        login(request, self.user)
        self.assertEqual(request.user, self.user, "Failed to log in as '%s'" % self.user)

        request.user.switch_to_user(request, self.basic_user, None, None)
        self.assertEqual(request.user, self.basic_user, "Failed to morph into '%s'" % self.basic_user)

        request.user.switch_back(request)
        self.assertEqual(request.user, self.user, "Failed to morph back into '%s'" % self.user)        

        blocked_illegal_morph = True
        try:
            ESPUser(request.user).switch_to_user(request, self.basic_user, None, None)
            self.assertEqual(request.user, self.basic_user, "Failed to morph into '%s'" % self.basic_user)
        except ESPError():
            blocked_illegal_morph = True

        self.assertTrue(blocked_illegal_morph, "User '%s' was allowed to morph into an admin!")

    def testGradeChange(self):
        # Create the admin user
        adminUser, c1 = ESPUser.objects.get_or_create(username='admin')
        adminUser.set_password('password')
        make_user_admin(adminUser)
        # Create the student user
        studentUser, c2 = ESPUser.objects.get_or_create(username='student')
        # Make it a student
        studentUser.makeRole("Student")
        # Give it a starting grade
        student_studentinfo = StudentInfo(user=studentUser, graduation_year=ESPUser.YOGFromGrade(9))
        student_studentinfo.save()
        student_regprofile = RegistrationProfile(user=studentUser, student_info=student_studentinfo, most_recent_profile=True)
        student_regprofile.save()
        # Check that the grade starts at 9
        self.failUnless(studentUser.getGrade() == 9)

        # Login the admin
        self.failUnless(self.client.login(username="admin", password="password"))

        testGrade = 11
        curYear = ESPUser.current_schoolyear()
        gradYear = curYear + (12 - testGrade)
        self.client.get("/manage/userview?username=student&graduation_year="+str(gradYear))
        self.failUnless(studentUser.getGrade() == testGrade, "Grades don't match: %s %s" % (studentUser.getGrade(), testGrade))

        # Clean up
        if (c1):
            adminUser.delete()
        if (c2):
            studentUser.delete()



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
        one.cancel()
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

class TeacherInfo__validationtest(TestCase):
    def setUp(self):
        self.user, created = ESPUser.objects.get_or_create(username='teacherinfo_teacher')
        self.user.profile = self.user.getLastProfile()
        self.info_data = {
            'graduation_year': '2000',
            'school': 'L University',
            'major': 'Underwater Basket Weaving',
            'shirt_size': 'XXL',
            'shirt_type': 'M',
            'from_here': 'True'
        }

    def useData(self, data):
        from esp.users.models import TeacherInfo
        from esp.users.forms.user_profile import TeacherInfoForm
        # Stuff data into the form and check validation.
        tif = TeacherInfoForm(data)
        self.failUnless(tif.is_valid())
        # Check that form data copies correctly into the model
        ti = TeacherInfo.addOrUpdate(self.user, self.user.getLastProfile(), tif.cleaned_data)

        def is_int(i):
            try:
                int(i)
                return True
            except:
                return False
            
        # There's some data-cleaning going on here, so
        # ti.graduation_year may have been edited to drop
        # invalid values.
        self.failUnless(ti.graduation_year.strip() == tif.cleaned_data['graduation_year'].strip()
                        or (ti.graduation_year.strip() == "N/A"
                            and not (is_int(tif.cleaned_data['graduation_year'].strip())
                                 or tif.cleaned_data['graduation_year'].strip() == 'G')))
        
        # Check that model data copies correctly back to the form
        tifnew = TeacherInfoForm(ti.updateForm({}))
        self.failUnless(tifnew.is_valid())

        # This one should be an exact match
        self.failUnless(tifnew.cleaned_data['graduation_year'] == ti.graduation_year)

    def testUndergrad(self):
        self.info_data['graduation_year'] = '2000'
        self.useData( self.info_data )
    def testGrad(self):
        self.info_data['graduation_year'] = ' G'
        self.useData( self.info_data )
    def testOther(self):
        self.info_data['graduation_year'] = ''
        self.useData( self.info_data )
        self.info_data['graduation_year'] = 'N/A'
        self.useData( self.info_data )

class ValidHostEmailFieldTest(TestCase):
    def testCleaningKnownDomains(self):
        # Hardcoding 'esp.mit.edu' here might be a bad idea
        # But at least it verifies that A records work in place of MX
        for domain in [ 'esp.mit.edu', 'gmail.com', 'yahoo.com' ]:
            self.failUnless( ValidHostEmailField().clean( u'fakeaddress@%s' % domain ) == u'fakeaddress@%s' % domain )
    def testFakeDomain(self):
        # If we have an internet connection, bad domains raise ValidationError.
        # This should be the *only* kind of error we ever raise!
        try:
            ValidHostEmailField().clean( u'fakeaddress@idontex.ist' )
        except forms.ValidationError:
            pass

class UserForwarderTest(TestCase):
    def setUp(self):
        self.ua, created = ESPUser.objects.get_or_create(username='forward_a')
        self.ub, created = ESPUser.objects.get_or_create(username='forward_b')
        self.uc, created = ESPUser.objects.get_or_create(username='forward_c')
        self.users = [self.ua, self.ub, self.uc]
    def runTest(self):
        def fwd_info(user):
            return '%s forwards by: %s' % (user.username, user.forwarders_out.all())
        # Ensure that users have no forwarders by default
        for user in self.users:
            self.assertTrue(UserForwarder.follow(user) == (user, False), fwd_info(user))
        # Try forwarding B --> C
        # Expect (A), (B --> C)
        UserForwarder.forward(self.ub, self.uc)
        self.assertTrue(UserForwarder.follow(self.ua) == (self.ua, False), fwd_info(self.ua))
        self.assertTrue(UserForwarder.follow(self.ub) == (self.uc, True), fwd_info(self.ub))
        self.assertTrue(UserForwarder.follow(self.uc) == (self.uc, False), fwd_info(self.uc))
        # Try forwarding A --> B
        # Expect (A --> C), (B --> C)
        UserForwarder.forward(self.ua, self.ub)
        self.assertTrue(UserForwarder.follow(self.ua) == (self.uc, True), fwd_info(self.ua))
        self.assertTrue(UserForwarder.follow(self.ub) == (self.uc, True), fwd_info(self.ub))
        self.assertTrue(UserForwarder.follow(self.uc) == (self.uc, False), fwd_info(self.uc))
        # Try forwarding C --> B
        # Expect (A --> B), (C --> B)
        UserForwarder.forward(self.uc, self.ub)
        self.assertTrue(UserForwarder.follow(self.ua) == (self.ub, True), fwd_info(self.ua))
        self.assertTrue(UserForwarder.follow(self.ub) == (self.ub, False), fwd_info(self.ub))
        self.assertTrue(UserForwarder.follow(self.uc) == (self.ub, True), fwd_info(self.uc))

class MakeAdminTest(TestCase):
    def setUp(self):
        self.user, created = ESPUser.objects.get_or_create(username='admin_test')
        self.user.is_staff = False
        self.user.is_superview = False
        UserBit.objects.filter(user=self.user, qsc=GetNode('Q'), verb=GetNode('V/Administer')).delete()
        UserBit.objects.filter(user=self.user, qsc=GetNode('Q'), verb=GetNode('V/Flags/UserRole/Administrator')).delete()
        user_role_setup()

    def runTest(self):
        # Make sure user starts off with no administrator priviliges
        self.assertFalse(self.user.is_staff)        
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(UserBit.objects.UserHasPerms(user=self.user, qsc=GetNode('Q'), verb=GetNode('V/Administer')))
        self.assertFalse(UserBit.objects.UserHasPerms(user=self.user, qsc=GetNode('Q'), verb=GetNode('V/Flags/UserRole/Administrator')))

        # Now make admin_test into an admin using make_admin
        make_user_admin(self.user)

        # Make sure user now has administrator privileges
        self.assertTrue(self.user.is_staff)
        self.assertTrue(self.user.is_superuser)
        self.assertTrue(UserBit.objects.UserHasPerms(user=self.user, qsc=GetNode('Q'), verb=GetNode('V/Administer')))
        self.assertTrue(self.user.groups.filter(name="Administrator").exists())

        # Make sure that an unprivileged access to /myesp/makeadmin/ returns 403 Forbidden
        response = self.client.get('/myesp/makeadmin/')
        self.assertEqual(response.status_code, 403)

class AjaxExistenceChecker(TestCase):
    """ Check that an Ajax view is there by trying to retrieve it and checking for the desired keys
        in the response. 
    """
    def runTest(self):
        #   Quit if path and keys are not provided.  This ensures nothing will
        #   break if this is invoked without those attributes.
        if (not hasattr(self, 'path')) or (not hasattr(self, 'keys')):
            return
        
        import simplejson as json
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        for key in self.keys:
            self.assertTrue(content.has_key(key), "Key %s missing from Ajax response to %s" % (key, self.path))
        
class AjaxLoginExistenceTest(AjaxExistenceChecker):
    def __init__(self, *args, **kwargs):
        super(AjaxLoginExistenceTest, self).__init__(*args, **kwargs)
        self.path = '/myesp/ajax_login/'
        self.keys = ['loginbox_html']
        
class AjaxScheduleExistenceTest(AjaxExistenceChecker, ProgramFrameworkTest):
    def runTest(self):
        self.path = '/learn/%s/ajax_schedule' % self.program.getUrlBase()
        self.keys = ['student_schedule_html']
        user=self.students[0]
        self.assertTrue(self.client.login(username=user.username, password='password'))
        super(AjaxScheduleExistenceTest, self).runTest()

class AccountCreationTest(TestCase):
    
    def setUp(self):
        user_role_setup()

    def test_phase_1(self):
        #There's a tag that affects phase 1 so we put the tests into a function
        #and call it twice here
        Tag.setTag('ask_about_duplicate_accounts',value='true')
        self.phase_1()
        Tag.setTag('ask_about_duplicate_accounts',value='false')
        self.phase_1()
        

    def phase_1(self):
        """Testing the phase 1 of registration, the email address page"""
        #first try an email that shouldn't have an account
        #first without follow, to see that it redirects correctly
        response1 = self.client.post("/myesp/register/",data={"email":"tsutton125@gmail.com"})
        if Tag.getTag('ask_about_duplicate_accounts', default='false').lower() == 'false':
            self.assertTemplateUsed(response1,"registration/newuser.html")
            return

        self.assertRedirects(response1, "/myesp/register/information?email=tsutton125%40gmail.com")
        
        #next, make a user with that email and try the same
        u=ESPUser.objects.create(email="tsutton125@gmail.com")
        response2 = self.client.post("/myesp/register/",data={"email":"tsutton125@gmail.com"},follow=True)
        self.assertTemplateUsed(response2, 'registration/newuser_phase1.html')
        self.assertContains(response2, "do_reg_no_really")

        #check when there's a user awaiting activation
        #(we check with a regex searching for _ in the password, since that
        #can't happen normally)
        u.password="blah_"
        response3 = self.client.post("/myesp/register/",data={"email":"tsutton125@gmail.com"},follow=True)
        self.assertTemplateUsed(response3, 'registration/newuser_phase1.html')
        self.assertContains(response3, "do_reg_no_really")

        #check when you send do_reg_no_really it procedes
        response4 = self.client.post("/myesp/register/",data={"email":"tsutton125@gmail.com","do_reg_no_really":""},follow=False)
        self.assertRedirects(response4, "/myesp/register/information?email=tsutton125%40gmail.com")
        response4 = self.client.post("/myesp/register/",data={"email":"tsutton125@gmail.com","do_reg_no_really":""},follow=True)
        self.assertContains(response4, "tsutton125@gmail.com")

    def test_phase_2(self):
        #similarly to phase_1, call helper function twice with tag settings
        Tag.setTag('require_email_validation',value='True')
        self.phase_2()
        Tag.setTag('require_email_validation',value='False')
        self.phase_2()

    def phase_2(self):
        """Testing phase 2, where user provides info, and we make the account"""

        url = "/myesp/register/"
        if Tag.getTag("ask_about_duplicate_accounts", default="false").lower() != "false":
            url+="information/"
        response = self.client.post(url,
                                   data={"username":"username",
                                         "password":"passw",
                                         "confirm_password":"passw",
                                         "first_name":"first",
                                         "last_name":"last",
                                         "email":"tsutton125@gmail.com",
                                         "initial_role":"Teacher"})
        
        #test that the user was created properly
        try:
            u=ESPUser.objects.get(username="username",
                                  first_name="first",
                                  last_name="last",
                                  email="tsutton125@gmail.com")
        except ESPUser.DoesNotExist, ESPUser.MultipleObjectsReturned:
            self.fail("User not created correctly or created multiple times")

        if Tag.getTag('require_email_validation', default='False') != 'True':
            return

        self.assertFalse(u.is_active)
        self.assertTrue("_" in u.password)

        self.assertEqual(len(mail.outbox),1)
        self.assertEqual(len(mail.outbox[0].to),1)
        self.assertEqual(mail.outbox[0].to[0],u.email)
        #note: will break if the activation email is changed too much
        import re
        match = re.search("\?username=(?P<user>[^&]*)&key=(?P<key>\d+)",mail.outbox[0].body)
        self.assertEqual(match.group("user"),u.username)
        self.assertEqual(match.group("key"),u.password.rsplit("_")[-1])
        

