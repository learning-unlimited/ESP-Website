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


def sentry_secret_filter(secrets):
    """ A sentry_sdk hook, for both before_send and before_breadcrumb, that
    replaces each of 'secrets' with '[Filtered]' wherever it appears in an
    event or breadcrumb. sentry_sdk's own scrubbing goes by variable and field
    names, but a secret can be anywhere: a frame's local variables (e.g.
    esp.mailman's create_list, whose newlist arguments include the list admin
    password) or a subprocess breadcrumb, which records the whole command line
    and is attached to any later event. Empty secrets are ignored. """
    secrets = [s for s in secrets if s]

    def redact(value):
        if isinstance(value, str):
            for secret in secrets:
                value = value.replace(secret, '[Filtered]')
            return value
        if isinstance(value, dict):
            return {k: redact(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [redact(v) for v in value]
        return value

    def hook(event_or_crumb, hint):
        return redact(event_or_crumb) if secrets else event_or_crumb
    return hook
