from __future__ import absolute_import
import shutil
import unittest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from esp.seltests.util import try_normal_login, logout
from esp.users.models import ESPUser
from esp.utils.models import TemplateOverride


@unittest.skipUnless(
    shutil.which('firefox') or shutil.which('firefox-esr'),
    'Firefox not installed')
class CsrfTestCase(StaticLiveServerTestCase):
    def setUp(self):
        super().setUp()
        user, created = ESPUser.objects.get_or_create(username='student', first_name='Student', last_name='Student')
        user.set_password('student')
        user.save()
        # Save the last good version of the template override in question
        if len(TemplateOverride.objects.filter(name='index.html')) == 0:
             # There are no existing template overrides
             self.good_version = -1
        else:
             to = TemplateOverride.objects.filter(name='index.html')[0]
             self.good_version = to.next_version() - 1
        options = Options()
        options.add_argument("--headless")
        try:
            self.selenium = webdriver.Firefox(options=options)
            self.selenium.implicitly_wait(10)
        except Exception as e:
            self.skipTest(f"Firefox WebDriver could not be started: {e}")

    def tearDown(self):
        self.selenium.quit()
        super(CsrfTestCase, self).tearDown()
        if (self.good_version > 1):
            # Tear down the template override for consistent behavior
            last_good_to = TemplateOverride.objects.filter(name='index.html', version=self.good_version)
            last_good_to.save()
        else:
            # We need to get rid of the template override entirely
            TemplateOverride.objects.filter(name='index.html').delete()

    def setUpNormalLogin(self):
        if(self.good_version == -1):
             to, created = TemplateOverride.objects.get_or_create(name='index.html', version=1)
        else:
             to = TemplateOverride.objects.filter(name='index.html')[0]
        to.content = """
             {% extends "elements/html" %}

             {% block body %}
             {% include "users/loginbox.html" %}
             {% endblock %}
             """
        to.save()

    def test_csrf_delete(self):
        # Now set up and test normal login
        self.setUpNormalLogin()
        self.selenium.get('%s%s' % (self.live_server_url, '/'))  # Load index

        try_normal_login(self.selenium, self.live_server_url, "student", "student")
        WebDriverWait(self.selenium, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, 'logged_in'))
        )
        WebDriverWait(self.selenium, 10).until(
            EC.text_to_be_present_in_element((By.ID, 'user_first_name'), "Student")
        )
        logout(self.selenium, self.live_server_url)

        self.selenium.delete_cookie("esp_csrftoken")

        try_normal_login(self.selenium, self.live_server_url, "student", "student")
        WebDriverWait(self.selenium, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, 'logged_in'))
        )
        WebDriverWait(self.selenium, 10).until(
            EC.text_to_be_present_in_element((By.ID, 'user_first_name'), "Student")
        )
        logout(self.selenium, self.live_server_url)
