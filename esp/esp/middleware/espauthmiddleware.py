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
  Email: web-team@lists.learningu.org
"""

from django.conf import settings
from django.contrib.auth.middleware import LazyUser, AuthenticationMiddleware
from esp.utils.get_user import get_user

__all__ = ('ESPAuthMiddleware',)

ESPUser = None
get_user_django = None

class ESPLazyUser(LazyUser):
    def __get__(self, request, obj_type=None):
        global get_user_django, ESPUser, get_user
        if not hasattr(request, '_cached_user'):
            if get_user is None or ESPUser is None:                
                from django.contrib.auth import get_user as get_user_django
                from esp.users.models import ESPUser

            SESSION_KEY = '_auth_user_id'

            if request.session.has_key(SESSION_KEY):
                user_id = request.session[SESSION_KEY]
                try:
                    user = get_user(user_id)
                except ESPUser.DoesNotExist:
                    pass
                
            if not user:                
                request._cached_user = ESPUser(get_user_django(request))
                request._cached_user.updateOnsite(request)
            else:
                request._cached_user = user

        return request._cached_user

class ESPAuthMiddleware(object):
    """ Much like the auth middleware except that this returns an ESPUser. """

    def process_request(self, request):
        assert hasattr(request, 'session'), "The Django authentication middleware requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."
        request.__class__.user = ESPLazyUser()
        return None

    def process_response(self, request, response):
        from esp.users.models import ESPUser

        user = getattr(request, '_cached_user', None)
            
        if user and user.id:
            if settings.SESSION_EXPIRE_AT_BROWSER_CLOSE:
                max_age = None
                expires = None
            else:
                max_age = settings.SESSION_COOKIE_AGE
                expires = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=settings.SESSION_COOKIE_AGE), "%a, %d-%b-%Y %H:%M:%S GMT")
            ret_title = ''
            try:
                ret_title = request.session['user_morph']['retTitle']
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
                          'cur_admin': ESPUser(user).isAdministrator() and '1' or '0',
                          'cur_grade': ESPUser(user).getGrade(),
                          }

            for key, value in new_values.iteritems():
                if request.COOKIES.get(key, "") != str(value):
                    response.set_cookie(key, value, max_age=max_age, expires=expires,
                                        domain=settings.SESSION_COOKIE_DOMAIN,
                                        secure=settings.SESSION_COOKIE_SECURE or None)

        else:
            map(response.delete_cookie, ('cur_username','cur_email',
                                         'cur_first_name','cur_last_name',
                                         'cur_other_user','cur_retTitle',
                                         'cur_admin'))
        return response

        
