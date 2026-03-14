"""
Unit tests for esp/esp/mailman/__init__.py
"""
from unittest.mock import MagicMock, patch

from django.test import override_settings

from esp.tests.util import ProgramFrameworkTest


def _popen(stdout=b"", stderr=b""):
    """Return a mock Popen whose .communicate() returns (stdout, stderr)."""
    proc = MagicMock()
    proc.communicate.return_value = (stdout, stderr)
    return proc


_MAILMAN_ON = dict(
    USE_MAILMAN=True,
    MAILMAN_PATH="/usr/lib/mailman/bin/",
    MAILMAN_PASSWORD="test-admin-password",
)

_MAILMAN_OFF = dict(
    USE_MAILMAN=False,
    MAILMAN_PATH="/usr/sbin/",
    MAILMAN_PASSWORD="",
)