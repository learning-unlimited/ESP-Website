
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

import sys

from django.conf import settings
from django.core.mail import mail_admins, EmailMultiAlternatives
from django.views import debug

from django.template import defaultfilters
from django.db.models.query import QuerySet

# All of those exceptions we need to check against
from django import http
from django.core import exceptions
from esp.middleware.esperrormiddleware import ESPError_NoLog, Http403, AjaxError

__all__ = ('PrettyErrorEmailMiddleware',)

class PrettyErrorEmailMiddleware(object):
    """ This middleware will catch exceptions and--- instead of the
    normal less useful debug errors sent ---will send out the technical 500
    error response.

    To install, be sure to place this middleware near the beginning
    of the MIDDLEWARE_CLASSES setting in your settings file.
    This will make sure that it doesn't accidentally catch errors
    you were meaning to catch with other middleware.
    """

    ADMINS = None
    # A tuple of exceptions to ignore and *not* send email for:
    IGNORE_EXCEPTIONS = (http.Http404, Http403, ESPError_NoLog, SystemExit, AjaxError, exceptions.PermissionDenied)

    def process_request(self, request):
        """ In case a previous view wiped out the ADMINS variable,
        it'd be nice to resurrect it before the next request is handled.
        """
        if not settings.ADMINS and PrettyErrorEmailMiddleware.ADMINS:
            settings.ADMINS = PrettyErrorEmailMiddleware.ADMINS


    def process_exception(self, request, exception):
        if not PrettyErrorEmailMiddleware.ADMINS:
            PrettyErrorEmailMiddleware.ADMINS = settings.ADMINS

        if settings.DEBUG:
            return

        # If this is an error we don't want to hear about, just return.
        if isinstance(exception, self.IGNORE_EXCEPTIONS) or \
                exception in self.IGNORE_EXCEPTIONS:
            return

        try:
            # Add the technical 500 page.
            exc_info = sys.exc_info()

            subject = 'Error (%s IP): %s' % ((request.META.get('REMOTE_ADDR')
                                              in settings.INTERNAL_IPS and 'internal'
                                              or 'EXTERNAL'), request.path)
            try:
                request_repr = repr(request)
            except:
                request_repr = "Request repr() unavailable"

            message = "%s\n\n%s" % (self._get_traceback(exc_info), request_repr)

            # We have to register a new pprint function.
            defaultfilters.register.filter(safe_filter(defaultfilters.pprint))

            debug_response = debug.technical_500_response(request, *exc_info)

            msg = EmailMultiAlternatives(settings.EMAIL_SUBJECT_PREFIX \
                                             + subject, message,
                                         settings.SERVER_EMAIL,
                                         [a[1] for a in
                                          PrettyErrorEmailMiddleware.ADMINS])

            msg.attach_alternative(debug_response.content, 'text/html')
            msg.send(fail_silently=True)
        except Exception, e:
            return
        else:
            # Now that ADMINS is empty, we shouldn't get a second email.
            settings.ADMINS = ()

        return

    def _get_traceback(self, exc_info=None):
        "Helper function to return the traceback as a string"
        import traceback
        return '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))


class SafeReprQuerySet(QuerySet):
    """ This QuerySet class will be safe to `repr`.
    That means:
        1. If the QuerySet object passed is already evaluated, repr will behave as before.
        2. If the QuerySet object has not been evaluated, repr will be the SQL.

    Example usage::

        >>> if isinstance(qs, QuerySet):
        >>>     qs = SafeReprQuerySet.from_queryset(qs)
        >>> print repr(qs)
    """

    @classmethod
    def from_queryset(cls, queryset):
        """ Take a queryset and create a SafeReprQuerySet from it. """
        assert isinstance(queryset, QuerySet), "from_queryset requires a QuerySet object, recieved %r" % queryset
        new_queryset = queryset._clone(klass=cls, _result_cache=queryset._result_cache)
        new_queryset._old_class = queryset.__class__
        return new_queryset

    def __repr__(self):
        """ Return a representation of this object that doesn't evaluate the SQL. """
        old_class = self._old_class.__name__
        if self._result_cache:
            return QuerySet.__repr__(self)

        try:
            select, sql, params = self._get_sql_clause()
            sql = ("SELECT " + (self._distinct and "DISTINCT " or "") + ",".join(select) + sql)
            try:
                return '<%s SQL:%r>' % (old_class, sql % tuple(params))
            except:
                return '<%s SQL:%r>' % (old_class, [sql, params])
        except:
            return '<%s object>' % old_class


def safe_filter(old_method):
    """ This decorator will clean the value to make sure that
    if it's a QuerySet, it will become a SafeReprQuerySet prior
    to being sent to the actual filter.
    """
    if getattr(old_method, '_saferepr', False):
        return old_method

    def _safe_func(value, *args, **kwargs):
        if isinstance(value, QuerySet):
            value = SafeReprQuerySet.from_queryset(value)
        return old_method(value)
    _safe_func.__name__ = old_method.__name__
    _safe_func.__doc__ = old_method.__doc__
    _safe_func._saferepr = True
    _safe_func.is_safe = getattr(old_method, 'is_safe', False)

    return _safe_func
