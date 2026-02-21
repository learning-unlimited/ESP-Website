from __future__ import absolute_import

from django.conf import settings
from django.http import HttpResponse, JsonResponse

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object


SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


class MaintenanceReadOnlyModeMiddleware(MiddlewareMixin):

    def _is_enabled(self):
        return bool(getattr(settings, "MAINTENANCE_READ_ONLY", False))

    def _banner_message(self):
        return getattr(
            settings,
            "MAINTENANCE_READ_ONLY_BANNER_MESSAGE",
            "Maintenance: Read-only mode is enabled. Saving is temporarily disabled.",
        )

    def _is_exempt_path(self, path):
        prefixes = getattr(settings, "MAINTENANCE_READ_ONLY_EXEMPT_PATH_PREFIXES", ())
        for p in prefixes:
            if path.startswith(p):
                return True
        return False

    def _user_is_adminish(self, user):
        if not user or not getattr(user, "is_authenticated", False):
            return False
        try:
            if hasattr(user, "isAdministrator") and user.isAdministrator():
                return True
        except Exception:
            pass
        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            return True
        return False

    def process_request(self, request):
        if not self._is_enabled():
            return None
        if request.method in SAFE_METHODS:
            return None
        if self._is_exempt_path(request.path):
            return None
        if self._user_is_adminish(getattr(request, "user", None)):
            return None
        msg = self._banner_message()
        accept = (request.META.get("HTTP_ACCEPT") or "").lower()
        xrw = (request.META.get("HTTP_X_REQUESTED_WITH") or "").lower()
        wants_json = ("application/json" in accept) or (xrw == "xmlhttprequest")
        if wants_json:
            return JsonResponse({"detail": msg}, status=503)
        return HttpResponse(msg, status=503, content_type="text/plain; charset=utf-8")
