from selenium.webdriver.common.keys import Keys
from django_selenium.testcases import SeleniumTestCase
from django_selenium import settings
from esp.users import views
from esp.users.views import userprogram
from esp.mobiletests.factories import *

from mock import Mock
import time

class TestLogin(SeleniumTestCase):
    views.ajax_login = Mock()           # mocks '/myesp/ajax_login/'
    userprogram.get_program = Mock()    # mocks '/myesp/program/'

    def setUp(self):
        setattr(settings, 'SELENIUM_DRIVER', 'Chrome')
        setattr(settings, 'SELENIUM_TIMEOUT', 5)
        self.username_textbox = 'input[name="username"]'
        self.password_textbox = 'input[name="password"]'

        SeleniumTestCase.setUp(self)
        self.open_url('/media/mobile/build/production/index.html')
        time.sleep(1)   # delay for app to load its resources

    def tearDown(self):
        views.ajax_login.reset_mock()
        SeleniumTestCase.tearDown(self)

    def test_error_login(self):
        self.type_in(self.username_textbox, 'wronguser')
        self.type_in(self.password_textbox, 'wrongpassword')

        views.ajax_login.return_value = ErrorLoginResponseFactory.build()
        self.find(self.password_textbox).send_keys(Keys.RETURN)
        time.sleep(1)   # delay necessary for app to make request to mock server
        self.assertEqual(views.ajax_login.call_count, 1)
        self.assertTrue(views.ajax_login.called)

        # Check for error message box
        self.assertEqual(self.find('.x-msgbox .x-title > .x-innerhtml').text, 'Login Error')
        self.assertEqual(self.find('.x-msgbox-text > .x-innerhtml').text, 'Invalid username or password')

    def test_error_login_without_server(self):
        # Test for client side validation
        self.type_in(self.username_textbox, 'user')
        self.type_in(self.password_textbox, '')

        self.find(self.password_textbox).send_keys(Keys.RETURN)
        time.sleep(1)
        self.assertEqual(views.ajax_login.call_count, 0)
        self.assertFalse(views.ajax_login.called)

        # Check for error message box
        self.assertEqual(self.find('.x-msgbox .x-title > .x-innerhtml').text, 'Invalid Form')
        self.assertEqual(self.find('.x-msgbox-text > .x-innerhtml').text, 'You did not provide your password.')

    def test_user_login(self):
        self.type_in(self.username_textbox, 'student')
        self.type_in(self.password_textbox, 'password')

        views.ajax_login.return_value = StudentLoginResponseFactory.build()
        userprogram.get_program.return_value = ProgramResponseFactory.build()
        self.find(self.password_textbox).send_keys(Keys.RETURN)
        time.sleep(1)
        self.assertEqual(views.ajax_login.call_count, 1)
        self.assertTrue(views.ajax_login.called)
        self.assertEqual(userprogram.get_program.call_count, 1)
        self.assertTrue(userprogram.get_program.called)

        # Check for Program page
        self.assertEqual(self.find('.x-navigation-bar .x-title > .x-innerhtml').text, 'Program')
        self.assertEqual(self.find('.x-navigation-bar .x-button > .x-button-label').text, 'Go!')
        self.assertEqual(self.find('.x-scroll-container .description > .x-innerhtml').text, 'Select the program you are attending:')
        self.assertEqual(self.find('.x-list-container > .x-list-item:first-child > .x-list-item-label').text, 'Test Program 1')
        self.assertEqual(self.find('.x-list-container > .x-list-item:last-child > .x-list-item-label').text, 'Test Program 2')
