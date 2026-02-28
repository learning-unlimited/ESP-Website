import re , logging
from typing import Optional,Tyoe
from django.conf import settings
from django.http import HttpRequest, HttpResponseForbidden
from django.middleware.csrf import REASON_NO_REFERRER
from django.views.csrf import csrf_failure as django_csrf_failure
logger = logging.getLogger(__name__)
def csrf_failure(request: HttpRequest,reason: str="")
    """
    View used when request fails CSRF protection
    """

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
        response = HttpResponseForbidden(str(response.content, encoding='UTF-8'),
                                         content_type=response['Content-Type'])

    except Exception:
        response = django_csrf_failure(request, reason=reason)

    return response

