"""
Enforces the test file layout described in docs/dev/testing.rst: every test
module lives in a ``tests/`` package next to the code it covers and is named
``test_*.py`` (or ``seltests.py`` for Selenium tests). pytest.ini only
collects those names, so a misplaced or misnamed file would otherwise be
silently skipped.
"""
import os
import re

from django.test import SimpleTestCase

_ESP_PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # …/esp/esp

_COLLECTED_NAME = re.compile(r'^(test_\w*|seltests)\.py$')
_LEGACY_NAME = re.compile(r'^(tests|tests_\w*|\w*_tests)\.py$')
_TEST_METHOD = re.compile(r'^\s+def test_\w*\(', re.MULTILINE)

# Matches test_*.py but is the Django settings module, not a test file.
_NOT_TESTS = {os.path.join('esp', 'test_settings.py')}


class TestFileLayoutTest(SimpleTestCase):

    def _iter_py_files(self):
        esp_root = os.path.dirname(_ESP_PACKAGE_ROOT)
        for dirpath, dirnames, filenames in os.walk(_ESP_PACKAGE_ROOT):
            dirnames[:] = [d for d in dirnames if not d.startswith(('.', '__'))]
            for name in filenames:
                if name.endswith('.py'):
                    path = os.path.join(dirpath, name)
                    yield os.path.relpath(path, esp_root), name, os.path.basename(dirpath)

    def test_test_files_are_in_tests_packages(self):
        misplaced = [
            rel for rel, name, parent in self._iter_py_files()
            if rel not in _NOT_TESTS
            and (_LEGACY_NAME.match(name) or (_COLLECTED_NAME.match(name) and parent != 'tests'))
        ]
        self.assertEqual(misplaced, [], (
            'Move these into a tests/ package next to the code they cover, '
            'named test_<source module>.py (see docs/dev/testing.rst)'))

    def test_tests_packages_only_hold_collected_test_files(self):
        uncollected = []
        for rel, name, parent in self._iter_py_files():
            if parent != 'tests' or _COLLECTED_NAME.match(name):
                continue
            with open(os.path.join(os.path.dirname(_ESP_PACKAGE_ROOT), rel)) as f:
                if _TEST_METHOD.search(f.read()):
                    uncollected.append(rel)
        self.assertEqual(uncollected, [], (
            'These files define test methods but pytest will not collect them; '
            'rename them to test_*.py'))
