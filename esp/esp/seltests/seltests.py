from django.core.urlresolvers import reverse
from django_selenium.testcases import SeleniumTestCase
from selenium.webdriver.common.keys import Keys

from esp.users.models import ESPUser

import time

class CsrfTestCase(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        user, created = ESPUser.objects.get_or_create(username='student', first_name='Student', last_name='Student')
        user.set_password('student')
        user.save()
	print user.get_full_name()

    def try_login(self):
        elem = self.find_element_by_name("username") # Find the username field
        elem.send_keys("student")
        elem = self.find_element_by_name("password") # Find the password field
        elem.send_keys("student" + Keys.RETURN)
        time.sleep(1)
        self.open_url("/")

    def logout(self):
        self.open_url("/myesp/signout/")
        self.open_url("/")

    def test_csrf_delete(self):
        self.open_url("/") # Load index

        self.try_login()
        #time.sleep(5)
        self.failUnless(self.is_text_present('Student Student'))
        self.logout()
        #time.sleep(5)

        self.delete_cookie("csrftoken")

        self.try_login()
        #time.sleep(5)
        alert = self.switch_to_alert()
        #time.sleep(5)
        alert.dismiss()
        #time.sleep(5)
        self.switch_to_default_content()
        #time.sleep(5)
        self.failUnless(self.is_text_present('Please log in to access program registration'))
        self.logout()
        time.sleep(5)

        self.try_login()
        #time.sleep(5)
        self.failUnless(self.is_text_present('Student Student'))
        self.logout()

        #time.sleep(5)
        self.close()
