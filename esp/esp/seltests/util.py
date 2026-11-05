from __future__ import absolute_import
import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


@pytest.mark.selenium
class SeleniumTestCase(StaticLiveServerTestCase):
    """
    Base class for browser tests, run in headless Firefox. These are skipped
    unless pytest is run with --selenium; once requested, a browser that
    cannot start fails the test instead of skipping it.
    """

    def setUp(self):
        super().setUp()
        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        self.selenium = webdriver.Firefox(options=options)
        self.addCleanup(self.selenium.quit)
        self.selenium.implicitly_wait(10)


def try_login(selenium, username, password):
    username_input = WebDriverWait(selenium, 10).until(
        EC.visibility_of_element_located((By.NAME, "username"))
    )
    username_input.send_keys(username)
    password_input = selenium.find_element(By.NAME, "password")
    password_input.send_keys(password)
    selenium.find_element(By.ID, 'gologin').click()


def try_normal_login(selenium, live_server_url, username, password):
    try_login(selenium, username, password)
    WebDriverWait(selenium, 10).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "logged_in"))
    )
    selenium.get('%s%s' % (live_server_url, "/"))


def logout(selenium, live_server_url):
    selenium.get('%s%s' % (live_server_url, "/myesp/signout/"))
    selenium.get('%s%s' % (live_server_url, "/"))
