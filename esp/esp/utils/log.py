from __future__ import absolute_import
import logging

from django.conf import settings


class RequireInScript(logging.Filter):
    def filter(self, record):
        return settings.IS_IN_SCRIPT


class RequireNotInScript(logging.Filter):
    def filter(self, record):
        return not settings.IS_IN_SCRIPT


class SkipHttp404(logging.Filter):
    """Drop django.request log records for plain 404s (e.g. bot/scanner noise),
    while still letting 5xx errors and everything else through to Sentry."""
    def filter(self, record):
        return getattr(record, 'status_code', None) != 404


class SkipDjango110DeprecationWarning(logging.Filter):
    """Drop py.warnings records for the RemovedInDjango110Warning deprecation
    spam (old Django 1.x-era code), while leaving other warnings (e.g. numpy
    RuntimeWarning) and all other loggers untouched."""
    def filter(self, record):
        return 'RemovedInDjango110Warning' not in record.getMessage()
