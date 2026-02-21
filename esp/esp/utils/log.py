import logging

from django.conf import settings


class RequireInScript(logging.Filter):
    def filter(self, record):
        return settings.IS_IN_SCRIPT


class RequireNotInScript(logging.Filter):
    def filter(self, record):
        return not settings.IS_IN_SCRIPT
