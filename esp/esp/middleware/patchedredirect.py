from django.contrib.redirects import RedirectFallbackMiddleware
from django.http import HttpResponseRedirect


class PatchedRedirectFallbackMiddleware(RedirectFallbackMiddleware):
    """Uses a 302 instead of Django's default 301."""
    response_redirect_class = HttpResponseRedirect
