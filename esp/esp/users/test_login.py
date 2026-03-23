"""
Tests for user authentication and login functionality.
"""

from django.test.client import RequestFactory

from esp.program.models import RegistrationProfile
from esp.tests.util import CacheFlushTestCase as TestCase, user_role_setup
from esp.users.models import ESPUser, StudentInfo


class LoginTest(TestCase):
    """Test user authentication and login functionality."""

    def setUp(self):
        """Set up test users and required data before each test."""
        # Call user_role_setup to create necessary groups (Student, Teacher, etc.)
        user_role_setup()
        
        # Create a test user with a known password
        self.username = 'testuser'
        self.password = 'testpassword123'
        self.email = 'testuser@example.com'
        
        # Create the user using get_or_create to avoid duplicates
        self.user, created = ESPUser.objects.get_or_create(
            username=self.username,
            defaults={
                'email': self.email,
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        # Set the password (this hashes it properly)
        self.user.set_password(self.password)
        # Make sure the user is active (inactive users can't log in)
        self.user.is_active = True
        self.user.save()
        
        # Give the user a role (optional, but realistic)
        self.user.makeRole('Student')
        
        # Create a RegistrationProfile so the user has a complete profile
        # This prevents redirects to /myesp/profile during login
        student_info = StudentInfo.objects.create(
            user=self.user,
            graduation_year=ESPUser.YOGFromGrade(10)
        )
        RegistrationProfile.objects.create(
            user=self.user,
            student_info=student_info,
            most_recent_profile=True
        )

    def test_successful_login_with_valid_credentials(self):
        """Test that a user can successfully log in with correct username and password."""
        
        # STEP 1: Verify user is not logged in initially
        # The test client starts with an anonymous user
        response = self.client.get('/myesp/login/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')
        
        # STEP 2: Attempt to log in with valid credentials
        # POST to the login URL with username and password
        login_data = {
            'username': self.username,
            'password': self.password,
        }
        response = self.client.post('/myesp/login/', login_data, follow=True)
        
        # STEP 3: Verify the login was successful
        # Check that we got a successful response (200 or redirect)
        self.assertIn(response.status_code, [200, 302],
                     "Login should succeed with valid credentials")
        
        # STEP 4: Verify the user is now authenticated
        # After login, the test client's session should have the user
        # We can check this by accessing a page that requires login
        self.assertTrue(response.wsgi_request.user.is_authenticated,
                       "User should be authenticated after successful login")
        
        # STEP 5: Verify it's the correct user
        self.assertEqual(response.wsgi_request.user.username, self.username,
                        "The logged-in user should match the credentials provided")
        self.assertEqual(response.wsgi_request.user.id, self.user.id,
                        "The logged-in user ID should match the test user")
        
        # STEP 6: Verify session was created
        # Check that a session key exists (session was created)
        self.assertIsNotNone(self.client.session.session_key,
                            "A session should be created after login")
        
        # STEP 7: Alternative method - using Django's login() helper
        # You can also test login using the client's login() method directly
        # First, log out
        self.client.logout()
        
        # Then use the login() helper (this bypasses the view)
        login_successful = self.client.login(
            username=self.username,
            password=self.password
        )
        self.assertTrue(login_successful,
                       "Django's client.login() should succeed with valid credentials")
        
        # STEP 8: Verify user attributes are accessible
        # After login, we should be able to access user properties
        user = ESPUser.objects.get(username=self.username)
        self.assertEqual(user.email, self.email)
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password(self.password),
                       "Password should be correctly hashed and verifiable")
