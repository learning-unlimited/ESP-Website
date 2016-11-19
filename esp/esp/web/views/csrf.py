import re

from django.http import HttpResponseForbidden
from django.template import Context, Template
from django.conf import settings
from django.views.csrf import csrf_failure as django_csrf_failure

def csrf_failure(request, reason=""):
    """
    View used when request fails CSRF protection
    """
    from django.middleware.csrf import REASON_NO_REFERER
    c = {'DEBUG': settings.DEBUG and request.user.isAdministrator(),
         'reason': reason,
         'no_referer': reason == REASON_NO_REFERER
        }

    # We wrap our custom csrf_failure in a try-block, and fall back to
    # Django's global default view in the case of an exception, since we need
    # to be able to reliably display the error message.

    try:
        from esp.utils.web import render_to_response
        from esp.program.models import Program

        prog_re = r'^[-A-Za-z0-9_ ]+/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)'
        match = re.match(prog_re, request.path)
        if match:
            one, two = match.groups()
            try:
                prog = Program.by_prog_inst(one, two)
            except Program.DoesNotExist:
                prog = None
        else:
            prog = None

        response = render_to_response('403_csrf_failure.html', request, c)
        response = HttpResponseForbidden(response.content, content_type=response['Content-Type'])

    except Exception:
        response = django_csrf_failure(request, reason=reason)

    return response

