"""
New Selenium browser tests for student-facing and admin navigation flows.

These tests cover user-facing browser behaviors that have zero existing coverage:
  - Student login / logout lifecycle and nav state
  - /myesp/ access control (authenticated vs unauthenticated)
  - Invalid credentials rejected without creating a session
  - Admin login and Django /admin/ panel access
  - Non-admin user cannot access /admin/

This file is intentionally self-contained so it can be merged independently
of the infrastructure changes in PR #4339. It uses the Selenium 4 API
(``selenium.webdriver.common.by.By``) and Django's ``StaticLiveServerTestCase``
directly, and gracefully skips if Firefox / geckodriver is not available.

Related issues:
  - https://github.com/learning-unlimited/ESP-Website/issues/3780
  - https://github.com/learning-unlimited/ESP-Website/pull/3460
"""
from __future__ import absolute_import

import shutil
import time
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from esp.users.models import ESPUser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _headless_firefox():
    """Return a headless Firefox WebDriver.  Raises on failure."""
    options = Options()
    options.add_argument("--headless")
    return webdriver.Firefox(options=options)


def _login(selenium, username, password):
    """Fill in and submit the login form."""
    username_input = WebDriverWait(selenium, 10).until(
        EC.visibility_of_element_located((By.NAME, "username"))
    )
    username_input.send_keys(username)
    selenium.find_element(By.NAME, "password").send_keys(password)
    selenium.find_element(By.ID, "gologin").click()


def _login_and_go_home(selenium, live_server_url, username, password):
    """Log in, wait for the nav to reflect the authenticated state, navigate home."""
    _login(selenium, username, password)
    WebDriverWait(selenium, 10).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "logged_in"))
    )
    selenium.get(live_server_url + "/")


def _logout(selenium, live_server_url):
    """Navigate to the sign-out URL and return to the homepage."""
    selenium.get(live_server_url + "/myesp/signout/")
    selenium.get(live_server_url + "/")


# ---------------------------------------------------------------------------
# Student account flow tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(
    shutil.which("firefox") or shutil.which("firefox-esr"),
    "Firefox not installed — skipping Selenium tests",
)
class StudentAccountFlowTest(StaticLiveServerTestCase):
    """
    Browser-level tests for the student account lifecycle.

    Covers login / logout round-trip, nav-bar state transitions,
    /myesp/ access control, and rejection of invalid credentials.
    """

    PASSWORD = "testpassword123"
    USERNAME = "sel_student"

    def setUp(self):
        super().setUp()
        self.student, _ = ESPUser.objects.get_or_create(
            username=self.USERNAME,
            defaults={
                "first_name": "Selena",
                "last_name": "Tester",
                "email": "sel_student@example.com",
            },
        )
        self.student.set_password(self.PASSWORD)
        self.student.save()
        self.student.makeRole("Student")

        try:
            self.selenium = _headless_firefox()
            self.selenium.implicitly_wait(10)
        except Exception as exc:
            self.skipTest(f"Firefox WebDriver could not be started: {exc}")

    def tearDown(self):
        if hasattr(self, "selenium"):
            self.selenium.quit()
        super().tearDown()

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_login_updates_nav_with_student_name(self):
        """After login the nav bar shows the student's first and last name."""
        self.selenium.get(self.live_server_url + "/")
        _login_and_go_home(self.selenium, self.live_server_url, self.USERNAME, self.PASSWORD)

        WebDriverWait(self.selenium, 10).until(
            EC.text_to_be_present_in_element((By.ID, "user_first_name"), "Selena")
        )
        WebDriverWait(self.selenium, 10).until(
            EC.text_to_be_present_in_element((By.ID, "user_last_name"), "Tester")
        )
        self.assertEqual(self.selenium.find_element(By.ID, "user_first_name").text, "Selena")
        self.assertEqual(self.selenium.find_element(By.ID, "user_last_name").text, "Tester")

    def test_logout_hides_logged_in_block(self):
        """After logout the 'logged_in' nav block is hidden and 'not_logged_in' is visible."""
        self.selenium.get(self.live_server_url + "/")
        _login_and_go_home(self.selenium, self.live_server_url, self.USERNAME, self.PASSWORD)

        _logout(self.selenium, self.live_server_url)

        WebDriverWait(self.selenium, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "not_logged_in"))
        )
        for el in self.selenium.find_elements(By.CLASS_NAME, "logged_in"):
            self.assertFalse(
                el.is_displayed(),
                "logged_in nav block must not be visible after logout",
            )

    def test_myesp_accessible_to_authenticated_student(self):
        """An authenticated student can reach /myesp/ without being redirected to login."""
        self.selenium.get(self.live_server_url + "/")
        _login_and_go_home(self.selenium, self.live_server_url, self.USERNAME, self.PASSWORD)

        self.selenium.get(self.live_server_url + "/myesp/")
        WebDriverWait(self.selenium, 10).until(
            lambda d: "login" not in d.current_url
        )
        self.assertNotIn(
            "login",
            self.selenium.current_url,
            "Authenticated student should not be redirected to login from /myesp/",
        )

    def test_myesp_redirects_unauthenticated_visitor(self):
        """/myesp/ redirects an unauthenticated visitor to a login form."""
        self.selenium.get(self.live_server_url + "/myesp/")
        WebDriverWait(self.selenium, 10).until(
            lambda d: (
                "login" in d.current_url
                or len(d.find_elements(By.NAME, "username")) > 0
            )
        )
        has_login_url = "login" in self.selenium.current_url
        has_login_form = len(self.selenium.find_elements(By.NAME, "username")) > 0
        self.assertTrue(
            has_login_url or has_login_form,
            "/myesp/ should redirect unauthenticated users to a login form",
        )

    def test_invalid_credentials_do_not_create_session(self):
        """Wrong password must not produce a logged-in nav state."""
        self.selenium.get(self.live_server_url + "/")
        _login(self.selenium, self.USERNAME, "definitely_wrong_password")
        # Brief pause to allow any redirect / page update to complete
        time.sleep(1.5)
        for el in self.selenium.find_elements(By.CLASS_NAME, "logged_in"):
            self.assertFalse(
                el.is_displayed(),
                "logged_in nav block must not be visible after bad login",
            )


# ---------------------------------------------------------------------------
# Admin navigation tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(
    shutil.which("firefox") or shutil.which("firefox-esr"),
    "Firefox not installed — skipping Selenium tests",
)
class AdminNavigationTest(StaticLiveServerTestCase):
    """
    Browser-level smoke tests for administrator navigation.

    Covers admin login, access to the Django /admin/ panel,
    and verification that non-admin users are denied access to /admin/.
    """

    ADMIN_PASSWORD = "adminpassword123"
    ADMIN_USERNAME = "sel_admin"
    STUDENT_PASSWORD = "studentpassword123"
    STUDENT_USERNAME = "sel_nonadmin"

    def setUp(self):
        super().setUp()
        # Superuser / admin
        self.admin, _ = ESPUser.objects.get_or_create(
            username=self.ADMIN_USERNAME,
            defaults={
                "first_name": "AdminFirst",
                "last_name": "AdminLast",
                "email": "sel_admin@example.com",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        self.admin.set_password(self.ADMIN_PASSWORD)
        self.admin.save()
        self.admin.makeRole("Administrator")

        # Regular student (no admin privileges)
        self.student, _ = ESPUser.objects.get_or_create(
            username=self.STUDENT_USERNAME,
            defaults={
                "first_name": "NonAdmin",
                "last_name": "Student",
                "email": "sel_nonadmin@example.com",
            },
        )
        self.student.set_password(self.STUDENT_PASSWORD)
        self.student.save()
        self.student.makeRole("Student")

        try:
            self.selenium = _headless_firefox()
            self.selenium.implicitly_wait(10)
        except Exception as exc:
            self.skipTest(f"Firefox WebDriver could not be started: {exc}")

    def tearDown(self):
        if hasattr(self, "selenium"):
            self.selenium.quit()
        super().tearDown()

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_admin_login_shows_name_in_nav(self):
        """Admin user logs in and their first name appears in the nav bar."""
        self.selenium.get(self.live_server_url + "/")
        _login_and_go_home(
            self.selenium, self.live_server_url, self.ADMIN_USERNAME, self.ADMIN_PASSWORD
        )

        WebDriverWait(self.selenium, 10).until(
            EC.text_to_be_present_in_element((By.ID, "user_first_name"), "AdminFirst")
        )
        self.assertEqual(
            self.selenium.find_element(By.ID, "user_first_name").text,
            "AdminFirst",
        )

    def test_admin_can_access_django_admin_panel(self):
        """Admin user reaches /admin/ and sees the 'Site administration' page title."""
        self.selenium.get(self.live_server_url + "/")
        _login_and_go_home(
            self.selenium, self.live_server_url, self.ADMIN_USERNAME, self.ADMIN_PASSWORD
        )

        self.selenium.get(self.live_server_url + "/admin/")
        WebDriverWait(self.selenium, 10).until(EC.title_contains("Site administration"))
        self.assertIn("Site administration", self.selenium.title)

    def test_non_admin_cannot_access_django_admin_panel(self):
        """A regular student user is denied access to /admin/ (no 'Site administration' title)."""
        self.selenium.get(self.live_server_url + "/")
        _login_and_go_home(
            self.selenium, self.live_server_url, self.STUDENT_USERNAME, self.STUDENT_PASSWORD
        )

        self.selenium.get(self.live_server_url + "/admin/")
        # Wait briefly for the page to settle then check title
        WebDriverWait(self.selenium, 10).until(
            lambda d: "Site administration" not in d.title
        )
        self.assertNotIn(
            "Site administration",
            self.selenium.title,
            "Non-admin student must not reach the Django admin panel",
        )
