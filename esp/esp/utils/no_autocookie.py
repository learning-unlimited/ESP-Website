#!/usr/bin/python
from functools import wraps

def disable_csrf_cookie_update(fn):
    """
    If a user doesn't have a CSRF cookie, Django's csrf middleware
    will automatically add one, and will add "Vary: Cookie" to the
    view's HTTP headers.
    Some pages served by Django are meant to be ~static, and so
    should have neither behavior.  This decorator will prevent the
    csrf middleware from doing either.
    """
    @wraps(fn)
    def wrapped(*args, **kwargs):
        response = fn(*args, **kwargs)
        response.csrf_processing_done = True
        return response
    return wrapped


