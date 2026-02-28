import re , logging
from typing import Optional,Type
from django.conf import settings
from django.http import HttpRequest, HttpResponseForbidden
from django.middleware.csrf import REASON_NO_REFERER
from django.views.csrf import csrf_failure as django_csrf_failure

logger = logging.getLogger(__name__)

def csrf_failure(request: HttpRequest,reason: str="")->HttpResponseForbidden:
    """
    Custom CSRF failure handler with branded page for program URLs.

    Behavior:
    - Logs every failure with path, reason, user, and IP for observability.
    - Production / non-admin: minimal disclosure, fast fallback to Django default.
    - DEBUG + admin only: rich branded 403 page with program context.
    - Falls back to Django default on any rendering error, always with a log.
    """

   # Guard: is_authenticated prevents AnonymousUser.isAdministrator() from blowing up
    is_admin = request.user.is_authenticated and request.user.isAdministrator()
    is_detailed = settings.DEBUG and is_admin
    # Always log every CSRF failure, regardless of user or mode.
    # IP included: useful for detecting attack patterns or repeat offenders.
    logger.warning("CSRF failure: path='%s' reason='%s' user=%s ip=%s detailed=%s",request.path, reason or "none",request.user,request.META.get("REMOTE_ADDR","unknown"),is_detailed,)
    if not is_detailed:
        return django_csrf_failure(request, reason="") # internals safe

    context = {'DEBUG': settings.DEBUG and request.user.isAdministrator(),
         'reason': reason,
         'no_referer': reason == REASON_NO_REFERER,
        }
    try:
    # Deferred imports — safer for a last-resort error handler.
    # If esp modules fail to load, we fall back gracefully rather than
    # crashing the entire handler at module load time.
        from esp.utils.web import render_to_response
        from esp.program.models import Program
        context["program"] = _resolve_program(request.path, Program)
        rendered =  render_to_response("403_csrf_failure.html",request,context)
        return HttpResponseForbidden( rendered.content, content_type = rendered.get_content_type())

    except Exception:
                     logger.exception( "Custom CSRF template rendering failed path='%s', falling back to Django default",request.path)
                     return django_csrf_failure(request, reason=reason)


def _resolve_program(path:str, program_class: Type)-> Optional[object]:
    """
        Attempts to extract a Program instance from a URL path.

        Expects paths of the form:
            <anchor>/<prog_type>/<prog_instance>/...

        Returns None if:
        - Path doesn't match the expected pattern
        - Program doesn't exist in the database
        - Any unexpected error occurs during resolution

        Note: prog_type and prog_instance must be URL-safe (alphanumeric, hyphens, underscores).
        Spaces are excluded intentionally — program URLs should be slugified.
        """

    prog_re = r'^[-A-Za-z0-9_ ]+/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)'
    match = re.match(prog_re, path)
    if not match:
                 return None
    prog_type, instance=match.groups()
    try:
        return program_class.by_prog_inst(prog_type, instance)
    except program_class.DoesNotExist:
            logger.debug("Program not found for prog_type='%s' instance='%s'",prog_type,instance)
            return None
    except Exception: logger.exception("Unexpected error resolving program for prog_type='%s' instance='%s'", prog_type,instance,)
    return None
