import re

from django.http import HttpResponseForbidden
from django.template import Context, Template
from django.conf import settings
from django.core.mail import mail_admins
from django.views.csrf import csrf_failure as django_csrf_failure

def email_admins(request, reason):
    """
    Tell the admins about a CSRF failure, so we know who is getting them.

    This is written by hand instead of logging through AdminEmailHandler: the
    request is rejected before any view runs, so its POST data (passwords
    included) would be emailed unredacted.
    """
    try:
        user = getattr(request, 'user', None)
        username = user.username if user is not None and user.is_authenticated else 'anonymous'
        message = ('User: %s\nRequest: %s %s\nReason: %s\nReferer: %s\nUser agent: %s\n'
                   % (username, request.method, request.path, reason,
                      request.META.get('HTTP_REFERER', ''),
                      request.META.get('HTTP_USER_AGENT', '')))
        mail_admins('CSRF failure: %s' % request.path, message, fail_silently=True)
    except Exception:
        # Never let the email stop the error page from being shown.
        pass

def csrf_failure(request, reason=""):
    """
    View used when request fails CSRF protection
    """
    from django.middleware.csrf import REASON_NO_REFERER
    c = {'DEBUG': settings.DEBUG and request.user.isAdministrator(),
         'reason': reason,
         'no_referer': reason == REASON_NO_REFERER
        }

    if not settings.DEBUG:
        email_admins(request, reason)

    # We wrap our custom csrf_failure in a try-block, and fall back to
    # Django's global default view in the case of an exception, since we need
    # to be able to reliably display the error message.

    try:
        from esp.utils.web import render_to_response
        from esp.program.models import Program

        prog_re = r'^/?[-A-Za-z0-9_ ]+/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)'
        match = re.match(prog_re, request.path)
        prog = None
        if match:
            one, two = match.groups()
            try:
                prog = Program.by_prog_inst(one, two)
            except Program.DoesNotExist:
                prog = None

        c['prog'] = prog

        response = render_to_response('403_csrf_failure.html', request, c)
        # render_to_response() hands back an unrendered TemplateResponse, whose
        # content is not available until it has been rendered. Reading .content
        # first raises ContentNotRenderedError, which the except clause below
        # would quietly turn into Django's default error page. render() is a
        # no-op once the content is baked, so it is safe to call without
        # inspecting is_rendered, which not every render-capable type defines.
        if hasattr(response, 'render'):
            response.render()
        response = HttpResponseForbidden(str(response.content, encoding='UTF-8'),
                                         content_type=response['Content-Type'])

    except Exception:
        response = django_csrf_failure(request, reason=reason)

    return response

