"""
Shared fixtures for Playwright E2E tests.

These fixtures provide common setup for all E2E tests, including
base URL configuration and test user creation.

Usage:
    Start the Django dev server before running tests:
        cd esp && python manage.py runserver

    Then run the E2E tests:
        pytest e2e_tests/ --headed
"""
import pytest


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the running Django dev server."""
    return "http://localhost:8000"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context with a larger viewport for testing."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }


@pytest.fixture()
def admin_credentials():
    """Return credentials for an admin user.

    Note: The admin user must exist in the database. You can create one via:
        python manage.py createsuperuser
    or by using Django's ORM in a setup script.
    """
    return {
        "username": "admin",
        "password": "admin",
    }


@pytest.fixture()
def student_credentials():
    """Return credentials for a student user.

    Note: The student user must exist in the database.
    """
    return {
        "username": "student",
        "password": "student",
    }
