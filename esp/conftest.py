"""
conftest.py — pytest-django configuration for ESP-Website.

pytest-django integration:
- DJANGO_SETTINGS_MODULE is set in pytest.ini.
- pytest-django's auto-detection of the Django project (django_find_project)
  is disabled in pytest.ini because our triple-`esp` directory layout
  (/app/esp outer dir, /app/esp/esp inner package) causes the parent-walk
  heuristic to add the wrong directory to sys.path when pytest is invoked
  with a positional file argument.
- Instead, pytest.ini's `pythonpath = .` puts /app/esp on sys.path during
  pytest's early config init — before pytest-django's initial-conftest hook
  runs, which is the timing it needs.

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
import django
import pytest

collect_ignore = []


def pytest_configure(config):
    """
    Call django.setup() so the app registry is ready before pytest starts
    importing test modules during collection.

    Without this, any test module that imports Django models at the top level
    (e.g. test_db_interface.py) raises AppRegistryNotReady during collection.
    """
    from django.apps import apps
    if not apps.ready:
        django.setup()

def pytest_addoption(parser):
    parser.addoption(
        "--selenium",
        action="store_true",
        default=False,
        help="Run selenium integration tests",
    )

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

