from django.core.urlresolvers import reverse
from django_selenium.testcases import SeleniumTestCase
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from esp.users.models import ESPUser

from sys import stderr, stdout, exc_info

import time

def noActiveAjax(driver):
    return driver.execute_script("return numAjaxConnections == 0")

def waitForAjax(driver):
    while(not noActiveAjax(driver)):
        time.sleep(1)

class CsrfTestCase(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        user, created = ESPUser.objects.get_or_create(username='student', first_name='Student', last_name='Student')
        user.set_password('student')
        user.save()

    def try_login(self):
        elem = self.find_element_by_name("username") # Find the username field
        elem.send_keys("student")
        elem = self.find_element_by_name("password") # Find the password field
        elem.send_keys("student")
        elem.submit()
        try:
            WebDriverWait(self, 10).until(noActiveAjax)
        except:
            stderr.write(str(exc_info()[0]) + "\n")
            stderr.write("Wait for ajax login timed out.\n")
        self.open_url("/")

    def logout(self):
        self.open_url("/myesp/signout/")
        self.open_url("/")

    def test_csrf_delete(self):
        self.open_url("/") # Load index

        self.try_login()
        self.failUnless(self.is_text_present('Student Student'))
        self.logout()

        self.delete_cookie("csrftoken")

        self.try_login()
        self.failUnless(self.is_text_present('Please log in to access program registration'))
        self.logout()

        self.try_login()
        self.failUnless(self.is_text_present('Student Student'))
        self.logout()

        self.close()
