
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""

import datetime
from django.conf import settings

class Http403(Exception):
    pass

class ESPError_Log(Exception):
    pass

class ESPError_NoLog(Exception):
    pass

def ESPError(log=True):
    """ Use this to raise an error in the ESP world.
    Example usage::
        from esp.middleware import ESPError
        raise ESPError(False), 'This error will not be logged.'
    """
    if log:
        return ESPError_Log
    else:
        return ESPError_NoLog
 

class ESPErrorMiddleware(object):
    """ This middleware handles errors appropriately.
    It will display a friendly error if there indeed was one
    (and emails the admin). This, of course, is only true if DEBUG is
    False in the settings.py. Otherwise, it doesn't do any of that.
    """

    def process_response(self, request, response):
        user = getattr(request, '_cached_user', -1)
        if user == -1:
            return response

        if user and user.id:
            if settings.SESSION_EXPIRE_AT_BROWSER_CLOSE:
                max_age = None
                expires = None
            else:
                max_age = settings.SESSION_COOKIE_AGE
                expires = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=settings.SESSION_COOKIE_AGE), "%a, %d-%b-%Y %H:%M:%S GMT")
            ret_title = ''
            try:
                ret_title = request.session['user_morth']['retTitle']
            except KeyError:
                pass

            # URL-encode some data since cookies don't like funny characters. They
            # make the chocolate chips nervous.
            # : see public/media/scripts/content/user_data.js
            import urllib
            encoding = request.encoding
            if encoding is None:
                encoding = settings.DEFAULT_CHARSET
            new_values = {'cur_username': user.username,
                          'cur_email': urllib.quote(user.email.encode(encoding)),
                          'cur_first_name': urllib.quote(user.first_name.encode(encoding)),
                          'cur_last_name': urllib.quote(user.last_name.encode(encoding)),
                          'cur_other_user': getattr(user, 'other_user', False) and '1' or '0',
                          'cur_retTitle': ret_title,
                          
                          }

            for key, value in new_values.iteritems():
                response.set_cookie(key, value, max_age=max_age, expires=expires,
                                    domain=settings.SESSION_COOKIE_DOMAIN,
                                    secure=settings.SESSION_COOKIE_SECURE or None)

        else:
            map(response.delete_cookie, ('cur_username','cur_email',
                                         'cur_first_name','cur_last_name',
                                         'cur_other_user','cur_retTitle'))
        return response

    def process_exception(self, request, exception):
        from django.shortcuts import render_to_response
        from django.conf import settings
        from django.core.mail import mail_admins
        
        import sys

        debug = settings.DEBUG  # get the debug value
        
        exc_info = sys.exc_info()
        if isinstance(exception, ESPError_Log) or exception == ESPError_Log:
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
                # We're going to 'try' everything
                from esp.dblog.models import Log
                new_log = Log(text        = str(exc_info[1]),
                              extra       = str(request_repr),
                              stack_trace = str(traceback))
                new_log.save()

            except:
                # we just won't do anything if we can't log it...
                pass

        elif isinstance(exception, Http403):
            context = {'error': exc_info[1]}
            try:
                context['request'] = request
            except:
                pass
            return render_to_response('403.html', context)


        if isinstance(exception, ESPError_NoLog) or exception == ESPError_NoLog \
                or isinstance(exception, ESPError_Log) or exception == ESPError_Log: # No logging, just output
            context = {'error': exc_info[1]}
            try:
                context['request'] = request
            except:
                pass
                
            return render_to_response('error.html', context)  # Will use a pretty ESP error page...
        return None

            
    def _get_traceback(self, exc_info=None):
        "Helper function to return the traceback as a string"
        import traceback
        return '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))

