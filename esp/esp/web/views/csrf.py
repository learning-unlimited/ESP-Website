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

        prog = None
        path_parts = request.path.lstrip('/').split('/')
        if len(path_parts) >= 3:
            program_url = '/'.join(path_parts[1:3])
            prog = Program.objects.filter(url=program_url).first()
        
        c['prog'] = prog
        if prog:
            request.program = prog

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

