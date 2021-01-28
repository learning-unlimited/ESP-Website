import datetime

from django import forms
from django.core import mail
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.models import Group
from django.test.client import Client, RequestFactory
from django.http import HttpRequest
from django.conf import settings
from django.utils.functional import SimpleLazyObject

from esp.middleware import ESPError
from esp.program.models import RegistrationProfile, Program
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.tests.util import CacheFlushTestCase as TestCase, user_role_setup
from esp.users.forms.user_reg import ValidHostEmailField
from esp.users.models import User, ESPUser, PasswordRecoveryTicket, UserForwarder, StudentInfo, Permission, Record

class ESPUserTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user_role_setup()

    def testDelete(self):
        # Create a user and a permission
        self.user, created = ESPUser.objects.get_or_create(username='forgetful')
        self.permission, created = Permission.objects.get_or_create(user=self.user, permission_type='Administer')
        # Save the ID and then delete the user
        uid = self.user.id
        self.user.delete()
        # Make sure it's gone.
        self.assertTrue( User.objects.filter(id=uid).count() == 0 )
        self.assertTrue( ESPUser.objects.filter(id=uid).count() == 0 )
        self.assertTrue( Permission.objects.filter(user=uid).count() == 0 )

    def testMorph(self):
        class scratchDict(dict):
            def cycle_key(self):
                pass
            def flush(self):
                for i in self.keys():
                    del self[i]

        # Make up a fake request object
        request = self.factory.get('/')
        request.session = scratchDict()
        request.backend = 'esp.utils.auth_backend.ESPAuthBackend'
        request.user = None

        # Create a couple users and give them roles
        self.user, created = ESPUser.objects.get_or_create(username='forgetful')
        self.user.makeRole('Administrator')

        self.basic_user, created = ESPUser.objects.get_or_create(username='simple_student')
        self.basic_user.makeRole('Student')

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
            request.user.switch_to_user(request, self.basic_user, None, None)
            self.assertEqual(request.user, self.basic_user, "Failed to morph into '%s'" % self.basic_user)
        except ESPError():
            blocked_illegal_morph = True

        self.assertTrue(blocked_illegal_morph, "User '%s' was allowed to morph into an admin!")

    def testGradeChange(self):
        # Create the admin user
        adminUser, c1 = ESPUser.objects.get_or_create(username='admin')
        adminUser.set_password('password')
        adminUser.makeAdmin()
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
        self.assertTrue(studentUser.getGrade() == 9)

        # Login the admin
        self.assertTrue(self.client.login(username="admin", password="password"))

        testGrade = 11
        curYear = ESPUser.current_schoolyear()
        gradYear = curYear + (12 - testGrade)
        self.client.get("/manage/userview?username=student&graduation_year="+str(gradYear))
        self.assertTrue(studentUser.getGrade() == testGrade, "Grades don't match: %s %s" % (studentUser.getGrade(), testGrade))

        # Clean up
        if (c1):
            adminUser.delete()
        if (c2):
            studentUser.delete()

class PasswordRecoveryTicketTest(TestCase):
    def setUp(self):
        self.user, created = ESPUser.objects.get_or_create(username='forgetful')
        self.user.set_password('forgotten_pw')
        self.user.save()
        self.other, created = ESPUser.objects.get_or_create(username='innocent')
        self.other.set_password('remembered_pw')
        self.other.save()
    def runTest(self):
        # First, make sure both people can log in
        self.assertTrue(self.client.login( username='forgetful', password='forgotten_pw' ), "User forgetful cannot login")
        self.assertTrue(self.client.login( username='innocent', password='remembered_pw' ), "User innocent cannot login")

        # Create tickets; both User and ESPUser should work
        one   = PasswordRecoveryTicket.new_ticket( self.user )
        two   = PasswordRecoveryTicket.new_ticket( self.user )
        four  = PasswordRecoveryTicket.new_ticket( self.other )
        self.assertTrue(one.is_valid(), "Recovery ticket one is invalid.")
        self.assertTrue(two.is_valid(), "Recovery ticket two is invalid.")
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
        Tag.setTag('teacher_shirt_sizes', value='XS, S, M, L, XL, XXL')
        Tag.setTag('student_shirt_sizes', value='XS, S, M, L, XL, XXL')
        Tag.setTag('volunteer_shirt_sizes', value='XS, S, M, L, XL, XXL')
        Tag.setTag('shirt_types', value='Straight cut, Fitted cut')
        self.user, created = ESPUser.objects.get_or_create(username='teacherinfo_teacher')
        self.user.profile = self.user.getLastProfile()
        self.info_data = {
            'graduation_year': '2000',
            'major': 'Underwater Basket Weaving',
            'shirt_size': 'XXL',
            'shirt_type': 'Straight cut'
        }

    def useData(self, data):
        from esp.users.models import TeacherInfo
        from esp.users.forms.user_profile import TeacherInfoForm
        # Stuff data into the form and check validation.
        tif = TeacherInfoForm(data)
        self.assertTrue(tif.is_valid())
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
        self.assertTrue(ti.graduation_year.strip() == tif.cleaned_data['graduation_year'].strip()
                        or (ti.graduation_year.strip() == "N/A"
                            and not (is_int(tif.cleaned_data['graduation_year'].strip())
                                 or tif.cleaned_data['graduation_year'].strip() == 'G')))

        # Check that model data copies correctly back to the form
        tifnew = TeacherInfoForm(ti.updateForm({}))

        # split values from dropdown widget of affiliation
        affiliation_dropdown_widget = tifnew.fields['affiliation'].widget
        affiliation_values = affiliation_dropdown_widget.decompress(tifnew.data['affiliation'])
        tifnew.data['affiliation_0'] = affiliation_values[0]
        tifnew.data['affiliation_1'] = affiliation_values[1]
        del tifnew.data['affiliation']

        self.assertTrue(tifnew.is_valid())

        # This one should be an exact match
        self.assertTrue(tifnew.cleaned_data['graduation_year'] == ti.graduation_year)

    def testUndergrad(self):
        self.info_data['graduation_year'] = '2000'
        self.info_data['affiliation_0'] = 'Undergrad'
        self.info_data['affiliation_1'] = ''
        self.useData( self.info_data )
    def testGrad(self):
        self.info_data['graduation_year'] = ' G'
        self.info_data['affiliation_0'] = 'Grad'
        self.info_data['affiliation_1'] = ''
        self.useData( self.info_data )
    def testPostdoc(self):
        self.info_data['graduation_year'] = ''
        self.info_data['affiliation_0'] = 'Postdoc'
        self.info_data['affiliation_1'] = ''
        self.useData(self.info_data)
    def testOther(self):
        self.info_data['graduation_year'] = ''
        self.info_data['affiliation_0'] = 'Other'
        self.info_data['affiliation_1'] = 'Professor'
        self.useData( self.info_data )
        self.info_data['graduation_year'] = 'N/A'
        self.info_data['affiliation_0'] = 'None'
        self.info_data['affiliation_1'] = 'other school'
        self.useData( self.info_data )

class ValidHostEmailFieldTest(TestCase):
    def testCleaningKnownDomains(self):
        # Hardcoding 'esp.mit.edu' here might be a bad idea
        # But at least it verifies that A records work in place of MX
        for domain in [ 'esp.mit.edu', 'gmail.com', 'yahoo.com' ]:
            self.assertTrue( ValidHostEmailField().clean( u'fakeaddress@%s' % domain ) == u'fakeaddress@%s' % domain )
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
        self.user.is_superuser = False
        user_role_setup()

    def runTest(self):
        # Make sure user starts off with no administrator priviliges
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.groups.filter(name="Administrator").exists())

        # Now make admin_test into an admin using make_admin
        self.user.makeAdmin()

        # Make sure user now has administrator privileges
        self.assertTrue(self.user.is_staff)
        self.assertTrue(self.user.is_superuser)
        self.assertTrue(self.user.groups.filter(name="Administrator").exists())

        # Make sure that an unprivileged access to /myesp/makeadmin/ returns a redirect to the login page
        response = self.client.get('/myesp/makeadmin/')
        self.assertRedirects(response, '/accounts/login/?next=/myesp/makeadmin/')

class AjaxExistenceChecker(TestCase):
    """ Check that an Ajax view is there by trying to retrieve it and checking for the desired keys
        in the response.
    """
    def runTest(self):
        #   Quit if path and keys are not provided.  This ensures nothing will
        #   break if this is invoked without those attributes.
        if (not hasattr(self, 'path')) or (not hasattr(self, 'keys')):
            return

        import json
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        for key in self.keys:
            self.assertTrue(key in content, "Key %s missing from Ajax response to %s" % (key, self.path))

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
        response1 = self.client.post("/myesp/register/",data={"email":"tsutton125@gmail.com", "confirm_email":"tsutton125@gmail.com"})
        if not Tag.getBooleanTag('ask_about_duplicate_accounts'):
            self.assertTemplateUsed(response1,"registration/newuser.html")
            return

        self.assertRedirects(response1, "/myesp/register/information?email=tsutton125%40gmail.com")

        #next, make a user with that email and try the same
        u=ESPUser.objects.create(email="tsutton125@gmail.com")
        response2 = self.client.post("/myesp/register/",data={"email":"tsutton125@gmail.com", "confirm_email":"tsutton125@gmail.com"},follow=True)
        self.assertTemplateUsed(response2, 'registration/newuser_phase1.html')
        self.assertContains(response2, "do_reg_no_really")

        #check when there's a user awaiting activation
        #(we check with a regex searching for _ in the password, since that
        #can't happen normally)
        u.password="blah_"
        response3 = self.client.post("/myesp/register/",data={"email":"tsutton125@gmail.com", "confirm_email":"tsutton125@gmail.com"},follow=True)
        self.assertTemplateUsed(response3, 'registration/newuser_phase1.html')
        self.assertContains(response3, "do_reg_no_really")

        #check when you send do_reg_no_really it procedes
        response4 = self.client.post("/myesp/register/",data={"email":"tsutton125@gmail.com", "confirm_email":"tsutton125@gmail.com","do_reg_no_really":""},follow=False)
        self.assertRedirects(response4, "/myesp/register/information?email=tsutton125%40gmail.com")
        response4 = self.client.post("/myesp/register/",data={"email":"tsutton125@gmail.com", "confirm_email":"tsutton125@gmail.com","do_reg_no_really":""},follow=True)
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
        if Tag.getBooleanTag("ask_about_duplicate_accounts"):
            url+="information/"
        response = self.client.post(url,
                                   data={"username":"username",
                                         "password":"passw",
                                         "confirm_password":"passw",
                                         "first_name":"first",
                                         "last_name":"last",
                                         "email":"tsutton125@gmail.com",
                                         "confirm_email":"tsutton125@gmail.com",
                                         "initial_role":"Teacher"})

        #test that the user was created properly
        try:
            u=ESPUser.objects.get(username="username",
                                  first_name="first",
                                  last_name="last",
                                  email="tsutton125@gmail.com")
        except ESPUser.DoesNotExist, ESPUser.MultipleObjectsReturned:
            self.fail("User not created correctly or created multiple times")

        if not Tag.getBooleanTag('require_email_validation'):
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

from esp.users.models import GradeChangeRequest


class TestChangeRequestModel(TestCase):

    def _create_change_request(self):
        student = ESPUser.objects.create_user('bobdobbs', first_name='bob', last_name='dobbs')
        change_request = GradeChangeRequest.objects.create(claimed_grade=12, grade_before_request=8,
                                                           reason="hello", requesting_student=student)
        return change_request

    def test_acknowledged_time_set(self):
        """ Tests assignment of current time to acknowledged_time when
        request approval flag is set"""
        change_request = self._create_change_request()
        self.assertIsNone(change_request.acknowledged_time)

        change_request.approved = True
        change_request.save()

        self.assertIsInstance(change_request.acknowledged_time,datetime.datetime)

    def test_acknowledged_time_not_set(self):
        """ Tests acknowledged_time not set if approved is None """
        change_request = self._create_change_request()
        change_request.acknowledged_time = None
        change_request.approved = None
        change_request.save()

        self.assertIsNone(change_request.acknowledged_time)

    def test_confirmation_email_content(self):
        """Verifies content in confirmation email"""
        change_request = self._create_change_request()
        student = change_request.requesting_student
        subject, message  = change_request._confirmation_email_content()

        self.assertIn(student.first_name,message)
        self.assertIn(student.last_name,message)
        self.assertIn('Grade Change Request Update', subject)


    def test_request_email_content(self):
        """Verifies content in request email"""
        change_request = self._create_change_request()
        student = change_request.requesting_student
        subject, message  = change_request._request_email_content()

        self.assertIn(student.first_name,message)
        self.assertIn(student.last_name,message)
        self.assertIn(student.name(),subject)


class TestChangeRequestView(TestCase):

    def setUp(self):
        import random

        """ Set up a bunch of user accounts to play with """
        self.password = "pass1234"

        #   May fail once in a while, but it's not critical.
        self.unique_name = 'Test_UNIQUE%06d' % random.randint(0, 999999)
        self.user, created = ESPUser.objects.get_or_create(first_name=self.unique_name, last_name="User", username="testuser123543", email="server@esp.mit.edu")
        if created:
            self.user.set_password(self.password)
            self.user.save()

    def test_send_request_view_submission_invalid(self):
        c = Client()
        c.login(username=self.user.username, password=self.password)

        response = c.post("/myesp/grade_change_request", { "reason": '', 'claimed_grade': 483 })

        self.assertFormError(response, 'form', 'reason', 'This field is required.')
        self.assertFormError(response, 'form', 'claimed_grade', 'Value 483 is not a valid choice.')

    def test_send_request_email(self):
        c = Client()
        c.login(username=self.user.username, password=self.password)

        #   Submit a valid grade change request
        response = c.post("/myesp/grade_change_request", { "reason": 'I should not get this email', 'claimed_grade': 10 })

        #   Check that an email was sent with the right from/to
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, [settings.DEFAULT_EMAIL_ADDRESSES['default']])
        self.assertEqual(msg.from_email, settings.SERVER_EMAIL)

class RecordTest(TestCase):
    def setUp(self):
        super(RecordTest, self).setUp()
        self.past     = datetime.datetime(1970, 1, 1)
        self.future   = datetime.datetime.max
        self.user     = ESPUser.objects.create(username='RecordTest')
        self.event    = Record.EVENT_CHOICES[0][0]
        self.program1 = Program.objects.create(grade_min=7, grade_max=12)
        self.program2 = Program.objects.create(grade_min=7, grade_max=12)

    def tearDown(self):
        Record.filter(self.user, self.event, when=self.future).delete()
        self.user.delete()
        self.program1.delete()
        self.program2.delete()

    def runTest(self):
        # Run the tests for Records with two different programs, and without
        # a specific program.
        # If all iterations run successfully, this means that the Record
        # methods properly filter by program.
        for program in [None, self.program1, self.program2]:
            # Aliases so full set of args don't need to be typed each time.
            def user_completed(when=None, only_today=False):
                return Record.user_completed(self.user, self.event, program,
                                             when, only_today)
            def filter(when=None, only_today=False):
                return Record.filter(self.user, self.event, program,
                                     when, only_today)
            def create(when=None):
                kwargs = {'event'   : self.event,
                          'program' : program,
                          'user'    : self.user}
                if when is not None:
                    kwargs['time'] = when
                return Record.objects.create(**kwargs)

            # Create Record without time, test that it was created for now,
            # and that the event is complete, both in general and for the
            # current day.
            before = datetime.datetime.now()
            nowRecord = create()
            after = datetime.datetime.now()
            self.assertTrue(before <= nowRecord.time <= after)
            self.assertTrue(user_completed())
            # Below, we must explicitly pass time, instead of relying on
            # default.  Otherwise, the test would fail if the date rolled
            # over while running the test.
            self.assertTrue(user_completed(nowRecord.time, only_today=True))

            # Clear Records, test that event is incomplete at all times.
            nowRecord.delete()
            del nowRecord
            filter(self.future).delete()
            self.assertFalse(user_completed())
            self.assertFalse(user_completed(self.past))
            self.assertFalse(user_completed(self.future))

            # Create future Record, test that event is incomplete in the
            # present and past but complete in the future.
            create(self.future)
            self.assertFalse(user_completed())
            self.assertFalse(user_completed(self.past))
            self.assertTrue(user_completed(self.future))

            # Create past Record, test that event is complete at all times.
            # Furthermore, the past and the present only recognize this new
            # Record, whereas the future recognizes both the new and the
            # previous Record.
            create(self.past)
            self.assertTrue(user_completed())
            self.assertTrue(user_completed(self.past))
            self.assertTrue(user_completed(self.future))
            self.assertEqual(1, filter().count())
            self.assertEqual(1, filter(self.past).count())
            self.assertEqual(2, filter(self.future).count())

            # Test that event is complete for the past and future days, but
            # is incomplete for today. Furthermore, when filtering by day,
            # the future recognizes only one Record instead of two.
            self.assertTrue(user_completed(self.past, only_today=True))
            self.assertTrue(user_completed(self.future, only_today=True))
            self.assertFalse(user_completed(only_today=True))
            self.assertEqual(1, filter(self.future, only_today=True).count())

class PermissionTestCase(TestCase):

    def setUp(self):
        super(PermissionTestCase, self).setUp()
        self.role = Group.objects.create(name='group')
        self.user = ESPUser.objects.create(username='user')
        self.user.makeRole(self.role)
        self.program = Program.objects.create(grade_min=7, grade_max=12)

    def create_perm(self, name, user_or_role, **kwargs):
        """Create Permission object of type `name`.

        If user_or_role is 'user', sets user=self.user.

        If user_or_role is 'role', sets role=self.role.
        """
        kwargs.update({user_or_role: getattr(self, user_or_role)})
        return Permission.objects.create(permission_type=name, **kwargs)

    def create_user_perm(self, name, **kwargs):
        """Creates Permission object with user=self.user."""
        return self.create_perm(name, user_or_role='user', **kwargs)

    def create_user_perm_for_program(self, name, **kwargs):
        """Creates Permission object with user=self.user and program=self.program."""
        return self.create_user_perm(name, program=self.program, **kwargs)

    def create_role_perm(self, name, **kwargs):
        """Creates Permission object with role=self.role."""
        return self.create_perm(name, user_or_role='role', **kwargs)

    def create_role_perm_for_program(self, name, **kwargs):
        """Creates Permission object with role=self.role and program=self.program."""
        return self.create_role_perm(name, program=self.program, **kwargs)

    def user_has_perm(self, name, *args, **kwargs):
        """Checks for Permission object with user=self.user."""
        return Permission.user_has_perm(self.user, name, *args, **kwargs)

    def user_has_perm_for_program(self, name, *args, **kwargs):
        """Checks for Permission object for self.program with user=self.user."""
        return self.user_has_perm(name, program=self.program, *args, **kwargs)

    def testUserAdministerProgram(self):
        self.create_user_perm_for_program('Administer')
        self.assertTrue(self.user_has_perm_for_program('test'))

    def testRoleAdministerProgram(self):
        self.create_role_perm_for_program('Administer')
        self.assertTrue(self.user_has_perm_for_program('test'))

    def testUserAdministerAll(self):
        self.create_user_perm('Administer')
        self.assertTrue(self.user_has_perm_for_program('test'))
        self.assertTrue(self.user_has_perm('test'))

    def testRoleAdministerAll(self):
        self.create_role_perm('Administer')
        self.assertTrue(self.user_has_perm_for_program('test'))
        self.assertTrue(self.user_has_perm('test'))

    def testAdministratorAlwaysHasPerm(self):
        self.user.makeRole('Administrator')
        self.assertTrue(self.user_has_perm_for_program('test'))
        self.assertTrue(self.user_has_perm('test'))

    def testImplications(self):
        for base, implications in Permission.implications.iteritems():
            perm = self.create_role_perm_for_program(base)
            for implication in implications:
                self.assertTrue(self.user_has_perm_for_program(implication))
            perm.delete()

    def testUserPerm(self):
        perm = 'Student/MainPage'
        other_user = ESPUser.objects.create(username='other')
        self.create_user_perm_for_program(perm)
        self.assertTrue(self.user_has_perm_for_program(perm))
        self.assertFalse(Permission.user_has_perm(other_user, perm, program=self.program))

    def testRolePerm(self):
        perm = 'Student/MainPage'
        other_user = ESPUser.objects.create(username='other')
        self.create_role_perm_for_program(perm)
        self.assertTrue(self.user_has_perm_for_program(perm))
        self.assertFalse(Permission.user_has_perm(other_user, perm, program=self.program))

    def testProgramPerm(self):
        perm = 'Student/MainPage'
        other_program = Program.objects.create(grade_min=7, grade_max=12)
        self.create_role_perm_for_program(perm)
        self.assertTrue(self.user_has_perm_for_program(perm))
        self.assertFalse(self.user_has_perm(perm))
        self.assertFalse(Permission.user_has_perm(self.user, perm, program=other_program))

    def testProgramIsNonePerm(self):
        perm = 'Student/MainPage'
        self.create_role_perm(perm)
        self.assertFalse(self.user_has_perm_for_program(perm))
        self.assertTrue(self.user_has_perm(perm))

    def testProgramIsNoneImpliesAllPerm(self):
        perm = 'Onsite'
        self.create_role_perm(perm)
        self.assertTrue(self.user_has_perm_for_program(perm, program_is_none_implies_all=True))

    def testTeacherClassesCreateImpliesTeacherClassesCreateClass(self):
        """Test that Teacher/Classes/Create implies Teacher/Classes/Create/Class.

        Ensure that old Teacher/Classes/Create Permissions, which were
        intended to give permission to create standard classes, are forward
        compatible and still grant this permission, which is now
        Teacher/Classes/Create/Class.
        """
        old_name = 'Teacher/Classes/Create'
        new_name = 'Teacher/Classes/Create/Class'

        self.create_user_perm_for_program(old_name)
        self.assertTrue(self.user_has_perm_for_program(new_name))

    def testOtherTeacherClassesCreateImplications(self):
        """Test the other Teacher/Classes/Create implications.

        - Ensure that Teacher/Classes/Create implies
          Teacher/Classes/Create/OpenClass.
        """
        name = 'Teacher/Classes/Create'
        implications = ['Teacher/Classes/Create/OpenClass']
        self.create_user_perm_for_program(name)
        self.assertTrue(all(map(self.user_has_perm_for_program, implications)))
