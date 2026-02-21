"""
conftest.py — pytest-django configuration for ESP-Website.

Known compatibility issues:
- esp/users/controllers/tests/test_usersearch.py: has a class-level
  `Program.objects.get(id=88)` call that runs at import/collection time.
  This requires a specific DB fixture with that exact program ID, making it
  unsuitable for the standard test DB. Excluded via collect_ignore below.

pytest-django requires a Django settings module to be configured before
tests run. This is set via pytest.ini (DJANGO_SETTINGS_MODULE).

The @pytest.mark.django_db decorator (or django_db fixture) is required
on any test that needs database access; existing TestCase subclasses that
inherit from django.test.TestCase get database access automatically.

For parallel execution (pytest-xdist), run:
    pytest -n auto          # uses all available CPU cores
    pytest -n 4             # uses 4 worker processes

Notes on xdist compatibility:
- Each worker gets its own test database (suffixed with gw<N>)
- Tests using Django's TestCase are safe to parallelize
- Tests that share global state or write to the filesystem may need
  the @pytest.mark.xdist_group decorator to pin them to one worker
"""
import os
import django
import pytest


collect_ignore = [
    # Class-level DB call (Program.objects.get(id=88)) fires at import time.
    # This test requires a live DB with a specific fixture — not suitable for
    # the standard pytest test database. See issue #3917 for remediation notes.
    "esp/users/controllers/tests/test_usersearch.py",
]


def pytest_configure(config):
    """
    Ensure manage.py-style virtualenv activation is skipped under pytest,
    and call django.setup() so apps are ready before test collection begins.

    Without this, any test module that imports Django models at the top level
    (e.g. test_db_interface.py) raises AppRegistryNotReady during collection.
    """
    # Prevent manage.py from trying to load activate_this.py which is absent
    # in venv-based environments (it's a virtualenv-only file).
    os.environ.setdefault("VIRTUAL_ENV", "1")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")

    # Call django.setup() here so the app registry is ready before pytest
    # starts importing test modules during collection.
    from django.apps import apps
    if not apps.ready:
        django.setup()


def pytest_collection_modifyitems(config, items):
    """
    Automatically skip selenium tests unless --selenium flag is passed.
    Selenium tests live in esp/esp/seltests/ and are rarely run locally.
    """
    run_selenium = config.getoption("--selenium", default=False)
    skip_selenium = pytest.mark.skip(reason="pass --selenium to run selenium tests")

    for item in items:
        if "seltests" in str(item.fspath):
            if not run_selenium:
                item.add_marker(skip_selenium)


def pytest_addoption(parser):
    parser.addoption(
        "--selenium",
        action="store_true",
        default=False,
        help="Run selenium integration tests",
    )
