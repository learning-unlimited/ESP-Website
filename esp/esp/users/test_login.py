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

    def test_logout(self):
        """Test that a logged-in user can successfully log out."""
        
        # STEP 1: First, log in the user
        login_successful = self.client.login(
            username=self.username,
            password=self.password
        )
        self.assertTrue(login_successful,
                       "User should be able to log in")
        
        # STEP 2: Verify user is authenticated before logout
        response = self.client.get('/myesp/login/')
        self.assertTrue(response.wsgi_request.user.is_authenticated,
                       "User should be authenticated before logout")
        self.assertEqual(response.wsgi_request.user.username, self.username,
                        "Logged-in user should match our test user")
        
        # STEP 3: Perform logout via the logout URL
        # The logout view is typically at /myesp/signout/
        logout_response = self.client.get('/myesp/signout/', follow=True)
        
        # STEP 4: Verify logout was successful
        # After logout, the user should be anonymous (not authenticated)
        self.assertFalse(logout_response.wsgi_request.user.is_authenticated,
                        "User should not be authenticated after logout")
        
        # STEP 5: Verify we can't access the user's session anymore
        # Try to access a page - the user should be anonymous
        response_after_logout = self.client.get('/myesp/login/')
        self.assertFalse(response_after_logout.wsgi_request.user.is_authenticated,
                        "User should remain logged out")
        
        # STEP 6: Verify user can log in again after logout
        # This ensures logout didn't break anything
        login_data = {
            'username': self.username,
            'password': self.password,
        }
        response = self.client.post('/myesp/login/', login_data, follow=True)
        self.assertTrue(response.wsgi_request.user.is_authenticated,
                       "User should be able to log in again after logout")
        
        # STEP 7: Alternative logout method - using client.logout()
        # This is Django's test utility for logging out
        self.client.logout()
        
        # Verify logout worked
        response = self.client.get('/myesp/login/')
        self.assertFalse(response.wsgi_request.user.is_authenticated,
                        "client.logout() should successfully log out the user")

    def test_login_with_invalid_username(self):
        """Test that login fails when username does not exist."""
        
        # STEP 1: Attempt to log in with a non-existent username
        login_data = {
            'username': 'nonexistent_user',
            'password': 'somepassword',
        }
        response = self.client.post('/myesp/login/', login_data, follow=True)
        
        # STEP 2: Verify login failed
        # User should NOT be authenticated
        self.assertFalse(response.wsgi_request.user.is_authenticated,
                        "User should not be authenticated with invalid username")
        
        # STEP 3: Verify we're still on the login page (or redirected back to it)
        self.assertTemplateUsed(response, 'registration/login.html',
                               "Should show login page after failed login")
        
        # STEP 4: Verify error context is set
        # The CustomLoginView sets 'wrong_user' in context when username doesn't exist
        self.assertIn('wrong_user', response.context,
                     "Context should indicate wrong username")
        self.assertTrue(response.context.get('wrong_user'),
                       "wrong_user flag should be True for non-existent username")
        
        # STEP 5: Verify using client.login() also fails
        login_successful = self.client.login(
            username='nonexistent_user',
            password='somepassword'
        )
        self.assertFalse(login_successful,
                        "client.login() should fail with invalid username")

    def test_login_with_invalid_password(self):
        """Test that login fails when password is incorrect."""
        
        # STEP 1: Attempt to log in with correct username but wrong password
        login_data = {
            'username': self.username,  # Valid username
            'password': 'wrongpassword',  # Invalid password
        }
        response = self.client.post('/myesp/login/', login_data, follow=True)
        
        # STEP 2: Verify login failed
        # User should NOT be authenticated
        self.assertFalse(response.wsgi_request.user.is_authenticated,
                        "User should not be authenticated with wrong password")
        
        # STEP 3: Verify we're still on the login page
        self.assertTemplateUsed(response, 'registration/login.html',
                               "Should show login page after failed login")
        
        # STEP 4: Verify error context is set
        # The CustomLoginView sets 'wrong_pw' in context when password is wrong
        self.assertIn('wrong_pw', response.context,
                     "Context should indicate wrong password")
        self.assertTrue(response.context.get('wrong_pw'),
                       "wrong_pw flag should be True for incorrect password")
        
        # STEP 5: Verify the user still exists and password is unchanged
        user = ESPUser.objects.get(username=self.username)
        self.assertTrue(user.check_password(self.password),
                       "Original password should still be valid")
        self.assertFalse(user.check_password('wrongpassword'),
                        "Wrong password should not validate")
        
        # STEP 6: Verify using client.login() also fails
        login_successful = self.client.login(
            username=self.username,
            password='wrongpassword'
        )
        self.assertFalse(login_successful,
                        "client.login() should fail with wrong password")

    def test_login_with_inactive_user(self):
        """Test that login fails when user account is inactive."""
        
        # STEP 1: Create an inactive user
        inactive_username = 'inactive_user'
        inactive_password = 'testpassword456'
        
        inactive_user, created = ESPUser.objects.get_or_create(
            username=inactive_username,
            defaults={
                'email': 'inactive@example.com',
                'first_name': 'Inactive',
                'last_name': 'User'
            }
        )
        inactive_user.set_password(inactive_password)
        inactive_user.is_active = False  # Set user as inactive
        inactive_user.save()
        
        # STEP 2: Attempt to log in with the inactive user
        login_data = {
            'username': inactive_username,
            'password': inactive_password,
        }
        response = self.client.post('/myesp/login/', login_data, follow=True)
        
        # STEP 3: Verify login failed
        # Inactive users should NOT be able to authenticate
        self.assertFalse(response.wsgi_request.user.is_authenticated,
                        "Inactive user should not be authenticated")
        
        # STEP 4: Verify we're still on the login page
        self.assertTemplateUsed(response, 'registration/login.html', "Should show login page when inactive user tries to login")
        
    
        #  the user should still be marked as inactive in the database
        user = ESPUser.objects.get(username=inactive_username)
        self.assertFalse(user.is_active, "User should still be inactive in database")
        
        # Log out to clean up the session
        self.client.logout()
        
        # STEP 6: Verify the user exists but is inactive
        user = ESPUser.objects.get(username=inactive_username)
        self.assertFalse(user.is_active, "User should still be inactive")
        self.assertTrue(user.check_password(inactive_password), "Password should be correct, but user is inactive")
        
        # STEP 7: Verify that activating the user allows login
        inactive_user.is_active = True
        inactive_user.save()
        
        login_successful = self.client.login(
            username=inactive_username,
            password=inactive_password
        )
        self.assertTrue(login_successful, "Login should succeed after user is activated")
        
        # Clean up
        self.client.logout()
        inactive_user.delete()
