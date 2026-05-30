"""
conftest.py for esp/esp/program/modules/tests/

The test files in this directory are named after the module they test
(e.g. programprintables.py, studentreg.py) rather than using pytest's
standard test_*.py convention. Django's test runner discovers TestCase
subclasses regardless of filename, but pytest only collects files that
match the python_files patterns in pytest.ini.

The pytest_collect_file hook below explicitly collects the non-standard
named .py files in this directory so pytest finds the same tests as
manage.py test. Files matching pytest's built-in python_files pattern
(test_*.py) are intentionally excluded here since pytest collects those
natively, avoiding double-collection.
"""
import pytest
from pathlib import Path

_THIS_DIR = Path(__file__).parent


def pytest_collect_file(parent, file_path):
    """
    Collect non-standard named .py files in this directory (e.g.
    programprintables.py, studentreg.py) that pytest would otherwise miss.

    Skips test_*.py files — pytest's built-in collection handles those.
    Scoped to this directory only to avoid accidentally collecting non-test
    .py files elsewhere in the project.
    """
    # ajaxstudentreg.py imports django_selenium which is not installed.
    # It must be skipped at collection time to avoid a ModuleNotFoundError.
    _SKIP = {"__init__.py", "conftest.py", "ajaxstudentreg.py"}
    if (
        file_path.suffix == ".py"
        and file_path.parent == _THIS_DIR
        and file_path.name not in _SKIP
        and not file_path.name.startswith(".")
        and not file_path.name.startswith("test_")
    ):
        return pytest.Module.from_parent(parent, path=file_path)
