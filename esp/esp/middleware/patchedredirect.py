from django.contrib.redirects.middleware import RedirectFallbackMiddleware
from django.http import HttpResponseRedirect, HttpResponseNotFound


class PatchedRedirectFallbackMiddleware(RedirectFallbackMiddleware):
    """Uses a 302 instead of Django's default 301."""
    response_redirect_class = HttpResponseRedirect
    response_gone_class = HttpResponseNotFound
