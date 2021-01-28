
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

import json
import logging
logger = logging.getLogger(__name__)
import sys

from django.conf import settings
from django.db.models.base import ObjectDoesNotExist
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.template import RequestContext
from django.utils.translation import ugettext as _

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

# TODO(benkraft): replace with the django version
class Http403(Exception):
    pass


# TODO(benkraft): these should probably inherit from a common parent.
class ESPError_Log(Exception):
    pass

class ESPError_NoLog(Exception):
    pass

def ESPError(message=None, log=True):
    """ Use this to raise an error in the ESP world.
    Example usage::
        from esp.middleware import ESPError
        raise ESPError('This error will not be logged.', log=False)
    Legacy (deprecated) usage::
        raise ESPError(log=False), 'This error will not be logged.'

    Note: "log=False" is a bit of a lie -- it just means it gets logged as INFO
    rather than ERROR (and therefore doesn't go to the serverlog email archive,
    just to the on-disk log).
    TODO(benkraft): allow specifying any log level, and update all callers.
    Some of these should really be WARNINGs.
    """
    if isinstance(message, bool):
        # trying to pass a bool argument: assume they meant log rather than message
        # this should become deprecated -lua 2013-02-15
        message = None
        log = message

    if log:
        cls = ESPError_Log
    else:
        cls = ESPError_NoLog

    if message is None:
        # no message: assume legacy usage
        return cls
    else:
        return cls(message)

""" Adapted from http://www.djangosnippets.org/snippets/802/ """
class AjaxErrorMiddleware(MiddlewareMixin):
    '''Return AJAX errors to the browser in a sensible way.

    Includes some code from http://www.djangosnippets.org/snippets/650/
    '''

    # Some useful errors that this middleware will catch.
    class AjaxError(Exception):
        def __init__(self, message):
            self.message = message
            super(AjaxErrorMiddleware.AjaxError, self).__init__(message)

    class AjaxParameterMissingError(AjaxError):
        def __init__(self, param):
            super(AjaxErrorMiddleware.AjaxParameterMissingError, self).__init__(
                _('Required parameter missing: %s') % param)


    def process_exception(self, request, exception):
        #   This line has been commented out for debugging so that requests
        #   can be made using a normal browser like Firefox with UrlParams.
        if not request.is_ajax(): return

        if isinstance(exception, (ObjectDoesNotExist, Http404)):
            return self.not_found(request, exception)

        if isinstance(exception, AjaxErrorMiddleware.AjaxError):
            return self.bad_request(request, exception)

        return None


    def serialize_error(self, status, message):
        return HttpResponse(json.dumps({
                    'status': status,
                    'error': message}),
                            status=status)


    def not_found(self, request, exception):
        return self.serialize_error(404, str(exception))


    def bad_request(self, request, exception):
        return self.serialize_error(200, exception.message)


    def server_error(self, request, exception):
        if settings.DEBUG:
            import sys, traceback
            (exc_type, exc_info, tb) = sys.exc_info()
            message = "%s\n" % exc_type.__name__
            message += "%s\n\n" % exc_info
            message += "TRACEBACK:\n"
            for tb in traceback.format_tb(tb):
                message += "%s\n" % tb
            return self.serialize_error(500, message)
        else:
            return self.serialize_error(500, _('Internal error'))

AjaxError = AjaxErrorMiddleware.AjaxError


class ESPErrorMiddleware(MiddlewareMixin):
    """ This middleware handles errors appropriately.
    It will display a friendly error if there indeed was one
    (and emails the admin). This, of course, is only true if DEBUG is
    False in the settings.py. Otherwise, it doesn't do any of that.
    """

    def process_exception(self, request, exception):

        if exception == ESPError_Log or exception == ESPError_NoLog:
            # TODO(benkraft): remove remaining instances of this.
            logging.warning("Raising the exception class is deprecated, "
                            "please raise ESPError(message) instead.")

        if isinstance(exception, ESPError_Log) or exception == ESPError_Log:
            # logging.ERROR will take care of emailing the error.
            log_level = logging.ERROR
            template = 'error.html'
            status = 500
        elif (isinstance(exception, ESPError_NoLog) or
              exception == ESPError_NoLog):
            log_level = logging.INFO
            template = 'error.html'
            # TODO(benkraft): this should probably be a 4xx, since if we're not
            # bothering to log it we probably don't think it was our fault.
            status = 500
        elif isinstance(exception, Http403):
            log_level = logging.INFO
            template = '403.html'
            status = 403
        else:
            return None

        exc_info = sys.exc_info()
        logger.log(log_level, exc_info[1], exc_info=exc_info)
        context = {'error': exc_info[1]}
        try:
            # attempt to set up variables the template needs
            # - actually, some things will fail to be set up due to our
            #   silly render_to_response hack, but hopefully that will all
            #   just silently fail...
            # - alternatively, we could, I dunno, NOT GET RID OF THE SAFE
            #   TEMPLATE in main?
            context = RequestContext(request, context).flatten()
        except:
            # well, we couldn't, but at least display something
            # (actually it will immediately fail on main because someone
            # removed the safe version of the template and
            # miniblog_for_user doesn't silently fail but best not to put
            # in ugly hacks and make random variables just happen to work.)
            pass
        # TODO(benkraft): merge our various error templates (403, 500, error).
        # They're all slightly different, but should probably be more similar
        # and share code.
        response = render(request, template, context)
        response.status_code = status
        return response
