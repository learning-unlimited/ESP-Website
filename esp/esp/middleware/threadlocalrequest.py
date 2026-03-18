## Code from <http://stackoverflow.com/questions/1057252/django-how-do-i-access-the-request-object-or-any-other-variable-in-a-forms-clea>
## Modified to not use (process-)global variables

import logging
logger = logging.getLogger(__name__)
import threading
_threading_local = threading.local()

from django.template import Context
try:
    from django.template import RequestContext
except ImportError:
    # Django 3.0+ removed RequestContext
    RequestContext = None

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

def get_current_request():
    return getattr(_threading_local, 'request', None)

def clear_current_request():
    """Remove the thread-local request, if any.

    Useful in tests where a stale request may reference a rolled-back user.
    """
    if hasattr(_threading_local, 'request'):
        del _threading_local.request

def AutoRequestContext(*args, **kwargs):
    """
    Create a context with access to the current request.

    This function is compatible with both Django 2.2 (with RequestContext)
    and Django 3.0+ (without RequestContext).

    Args:
        *args: Arguments to pass to the context constructor
        **kwargs: Keyword arguments (including optional 'autoescape')

    Returns:
        A dictionary-like context object
    """
    request = get_current_request()
    autoescape = kwargs.pop('autoescape', None)

    if request is None:
        logger.error("Couldn't access request! Falling back to basic Context. "
                     "This is almost certainly a bug; either Context should "
                     "be being used explicitly, or the request ought to "
                     "be available here.")
        retVal = Context(*args, **kwargs)
    else:
        if RequestContext is not None:
            # Django 2.2 and earlier: Use RequestContext
            retVal = RequestContext(request, *args, **kwargs)
            if autoescape is not None:
                retVal.autoescape = autoescape
            # Flatten to get a dictionary
            retVal = retVal.flatten()
        else:
            # Django 3.0+: RequestContext is not available
            # Build context using the engine's configured context_processors
            from django.template.context import make_context
            from django.conf import settings

            # Start with provided context data
            ctx_data = {}
            if args and isinstance(args[0], dict):
                ctx_data.update(args[0])

            # Use the template engine's make_context to apply all configured processors
            try:
                engine = settings.TEMPLATES[0]['ENGINE']
                context_processors = settings.TEMPLATES[0].get('OPTIONS', {}).get('context_processors', [])
                retVal = make_context(ctx_data, request=request)
                # make_context applies context processors, so we're done
            except Exception:
                # Fallback if engine config is not available
                ctx_data['request'] = request
                retVal = ctx_data

    # We need to return a dictionary-like object
    if isinstance(retVal, dict):
        return retVal
    else:
        # For RequestContext, convert to dict
        return dict(retVal)

class ThreadLocals(MiddlewareMixin):
    """
    Middleware that gets various objects from the
    request object and saves them in thread local storage.
    """
    def process_request(self, request):
        _threading_local.request = request
