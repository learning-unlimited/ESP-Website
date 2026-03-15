## Code from <http://stackoverflow.com/questions/1057252/django-how-do-i-access-the-request-object-or-any-other-variable-in-a-forms-clea>
## Modified to not use (process-)global variables

import logging
logger = logging.getLogger(__name__)
import threading
_threading_local = threading.local()

from django.template import Context, RequestContext
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
    request = get_current_request()
    if request is None:
        logger.error("Couldn't use RequestContext! Falling back to Context. "
                     "This is almost certainly a bug; either Context should "
                     "be being used explicitly, or RequestContext ought to "
                     "be available here.")
        retVal = Context(*args, **kwargs)
    else:
        if 'autoescape' in kwargs:
            autoescape = kwargs['autoescape']
            del kwargs['autoescape']

            retVal = RequestContext(request, *args, **kwargs)

            retVal.autoescape = autoescape
        else:
            retVal = RequestContext(request, *args, **kwargs)
    # we need to return a dictionary
    return retVal.flatten()

class ThreadLocals(MiddlewareMixin):
    """
    Middleware that gets various objects from the
    request object and saves them in thread local storage.
    """
    def process_request(self, request):
        _threading_local.request = request
