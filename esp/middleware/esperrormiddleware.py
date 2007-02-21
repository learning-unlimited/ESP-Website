from esp.middleware.statsmiddleware import *
from esp.middleware.esperrormiddleware import *

class ESPError_Log(Exception):
    pass

class ESPError_NoLog(Exception):
    pass

def ESPError(log = True):
    """ Use this to raise an error in the ESP world.
        Example usage:

        from esp.middleware import ESPError
        raise ESPError(False), 'This error will not be logged.'
    """
    if log:
        return ESPError_Log
    else:
        return ESPError_NoLog
 


class ESPErrorMiddleware(object):
    """
       This middleware handles errors appropriately. It will display a friendly error if
       there indeed was one (and emails the admin). This, of course, is only true if DEBUG is
       False in the settings.py. Otherwise, it doesn't do any of that.
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):       
        from django.shortcuts import render_to_response
        from django.conf import settings
        from django.core.mail import mail_admins
        
        import sys

        debug = settings.DEBUG  # get the debug value

        if debug:
            return view_func(request, *view_args, **view_kwargs)
        else:
            try:
                return view_func(request, *view_args, **view_kwargs)
            except:
                # most of this is from django.core.handlers.base
                exc_info = sys.exc_info()

                if exc_info[0] == ESPError_Log: # are we going to log this?
                    # Subject of the email
                    subject = 'Error (%s IP): %s' % ((request.META.get('REMOTE_ADDR') in \
                                                    settings.INTERNAL_IPS and 'internal' or 'EXTERNAL'), \
                                                    getattr(request, 'path', ''))
                
                    try:
                        request_repr = repr(request)
                    except:
                        request_repr = "Request repr() unavailable"


                    # get a friendly traceback
                    traceback = self._get_traceback(exc_info)

                    # Message itself
                    message = "%s\n\n%s" % (traceback, request_repr)

                    # Now we send the email
                    mail_admins(subject, message, fail_silently=True)

                    # Now we store the error into the database:
                    try:
                        # We're going to 'try' everything in case the db is fvck'd
                        from esp.dblog.models import Log

                        new_log = Log(text        = str(exc_info[1]),
                                      extra       = str(request_repr),
                                      stack_trace = str(traceback))
                        new_log.save()

                    except:
                        # we just won't do anything if we can't log it...
                        exc_info2 = sys.exc_info()
                        
                        raise exc_info2[0], exc_info2[1], exc_info2[2]
                        pass

                    context = {'error': exc_info[1]}
                    try:
                        context['request'] = request
                    except:
                        pass
                
                    return render_to_response('error.html', context)  # Will use a pretty ESP error page...

                elif exc_info[0] == ESPError_NoLog: # No logging, just output
                    
                    context = {'error': exc_info[1]}
                    try:
                        context['request'] = request
                    except:
                        pass
                
                    return render_to_response('error.html', context)  # Will use a pretty ESP error page...

                else:
                    
                    raise exc_info[0], exc_info[1], exc_info[2]
                


            
    def _get_traceback(self, exc_info=None):
        "Helper function to return the traceback as a string"
        import traceback
        return '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
