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
   # Keeping user AnonymourUser as anonymous
    is_admin = request.user.is_authenticated adn request.user.isAdministrator()
    is_detailed = settings.DEBUG and is_admin
    #Always logging + added feature of IP add in logs
    logger.warning("CSRF protection failed for: %s",requesth.path reason or "none",request.user,request.META.get("REMOTE_ADDR","unkown"),is_detailed,)
    if not is_detailed:
        return django_csrf_failure(request, reason="") # internals safe

    context = {'DEBUG': settings.DEBUG and request.user.isAdministrator(),
         'reason': reason,
         'no_referer': reason == REASON_NO_REFERER,
        }
    try :                  #preventing circular imports
    from esp.utils.web import render_to_response
    from esp.programs.models import Program
    context["program"] = _resolve_program(request.path, Program)
    rendered =  render_to_response("403_csrf_failure.html",request,context)
    return HttpResponseForbidden( rendered.content, content_type = rendered.get_content_type())

           except Exception:
                     logger.exception( "Cistom csrf template rendering fail",request.path)
                     return django_csrf_failure(request, reason="")

def _resolve_proragram(path:str, program_class: Type)-> Optional[object]

        prog_re = r'^[-A-Za-z0-9_ ]+/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)'
        match = re.match(prog_re, request.path)
        if not match:
            return None
        prog_type, instance=match.groups()
        try:
            return program_class.by_prog_inst(prog_type, instance)
        except program_class.DoesNotExist:
            logger.debug("Program not found",prog_type,instance)
            return None
        except Exception: logger.exception("Unexpected error", prog_type,instance,)
        return None
