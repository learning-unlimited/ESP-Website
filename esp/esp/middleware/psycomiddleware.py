from platform import architecture

if architecture()[0] != '32bit':
    raise Exception("Don't use this on non-32-bit platforms")

# let ImportError propagate at module load time so that people can notice and fix it
import psyco
import re
from django.contrib.auth.middleware import AuthenticationMiddleware
psyco.cannotcompile(re.compile)
psyco.cannotcompile(AuthenticationMiddleware.process_request)        
#psyco.profile(0.25)
psyco.full()

class PsycoMiddleware(object):
    """
    This middleware enables the psyco extension module which can massively
    speed up the execution of any Python code.
    """
    def process_request(self, request):
        return None
