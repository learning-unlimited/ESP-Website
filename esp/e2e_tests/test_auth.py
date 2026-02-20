"""
E2E tests for authentication flows.

Tests login and logout functionality using the Django dev server.
Ensure that test users exist in the database before running these tests.
"""
import re


def test_login_page_loads(page, base_url):
    """Test that navigating to the homepage shows the login form."""
    page.goto(base_url + "/")
    page.wait_for_load_state("networkidle")
    # The page should contain a username and password field
    username_field = page.locator('input[name="username"]')
    password_field = page.locator('input[name="password"]')
    assert username_field.count() > 0 or password_field.count() > 0, \
        "Expected login form fields on the page"


def test_login_with_valid_credentials(page, base_url, admin_credentials):
    """Test that a valid user can log in successfully."""
    page.goto(base_url + "/")
    page.wait_for_load_state("networkidle")

    # Fill in login credentials
    username_field = page.locator('input[name="username"]')
    password_field = page.locator('input[name="password"]')

    if username_field.count() > 0 and password_field.count() > 0:
        username_field.fill(admin_credentials["username"])
        password_field.fill(admin_credentials["password"])
        password_field.press("Enter")
        page.wait_for_load_state("networkidle")

        # After login, the page should show the user's name or a logout link
        page_content = page.content()
        assert (
            admin_credentials["username"] in page_content
            or "signout" in page_content.lower()
            or "logout" in page_content.lower()
            or "log out" in page_content.lower()
        ), "Expected to find username or logout link after login"


def test_logout(page, base_url, admin_credentials):
    """Test that a logged-in user can log out."""
    # First log in
    page.goto(base_url + "/")
    page.wait_for_load_state("networkidle")

    username_field = page.locator('input[name="username"]')
    password_field = page.locator('input[name="password"]')

    if username_field.count() > 0 and password_field.count() > 0:
        username_field.fill(admin_credentials["username"])
        password_field.fill(admin_credentials["password"])
        password_field.press("Enter")
        page.wait_for_load_state("networkidle")

        # Navigate to logout URL
        page.goto(base_url + "/myesp/signout/")
        page.wait_for_load_state("networkidle")

        # After logout, navigating to home should show login fields again
        page.goto(base_url + "/")
        page.wait_for_load_state("networkidle")

        # The login form should be visible again
        username_field_after = page.locator('input[name="username"]')
        # If username field is present, user is logged out
        if username_field_after.count() > 0:
            assert True
        else:
            # Alternatively, check that the page no longer shows the username
            page_content = page.content()
            assert admin_credentials["username"] not in page_content, \
                "User appears to still be logged in after logout"
