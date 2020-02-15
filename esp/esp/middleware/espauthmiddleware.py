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
import datetime

from django.conf import settings
from django.contrib import auth
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.auth.models import AnonymousUser
from django.utils.cache import patch_vary_headers
from django.utils.functional import SimpleLazyObject

from esp.users.models import AnonymousESPUser, ESPUser

__all__ = ('ESPAuthMiddleware',)

def get_user(request):
    """ Code modified from django.contrib.auth.middleware.get_user
    in order to replace the AnonymousUser with our own which has
    all the ESPUser methods. This mirrors Django's structure, where
    the auth backend only returns either a User or None, and
    AnonymousUser is inserted in auth.get_user(). In our case, the auth
    backend returns either an ESPUser or None, but auth.get_user() is less
    convenient to override since I'd still have to override this and the
    middleware's process_request() to use it, so I replace its AnonymousUser
    with an AnonymousESPUser here instead. """
    if not hasattr(request, '_cached_user'):
        user = auth.get_user(request)
        if user.is_authenticated():
            request._cached_user = user
        else:
            request._cached_user = AnonymousESPUser()
    return request._cached_user

class ESPAuthMiddleware(AuthenticationMiddleware):
    """ Much like the auth middleware except that this messes with cookie settings and such. """

    # Yes, it's necessary to override this, the get_user() is different
    # from Django's (see above).
    def process_request(self, request):
        assert hasattr(request, 'session'), "The Django authentication middleware requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."

        request.user = SimpleLazyObject(lambda: get_user(request))

    def process_response(self, request, response):
        ## This gets set if we're not supposed to modify the cookie
        if getattr(response, 'no_set_cookies', False):
            return response

        modified_cookies = False

        user = getattr(request, '_cached_user', None)
        #   Allow a view to set a newly logged-in user via the response
        if not user or not user.is_authenticated():
            new_user = getattr(response, '_new_user', None)
            if isinstance(new_user, ESPUser):
                user = new_user

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

            has_qsd_bits = user.isAdministrator()

            new_values = {'cur_username': user.username,
                          'cur_userid': user.id,
                          'cur_email': urllib.quote(user.email.encode(encoding)),
                          'cur_first_name': urllib.quote(user.first_name.encode(encoding)),
                          'cur_last_name': urllib.quote(user.last_name.encode(encoding)),
                          'cur_other_user': getattr(user, 'other_user', False) and '1' or '0',
                          'cur_retTitle': urllib.quote(ret_title.encode(encoding)),
                          'cur_admin': user.isAdministrator() and '1' or '0',
                          'cur_qsd_bits': has_qsd_bits and '1' or '0',
                          'cur_yog': user.getYOG(),
                          'cur_grade': user.getGrade(),
                          'cur_roles': urllib.quote(",".join(user.getUserTypes())),
                          }

            for key, value in new_values.iteritems():
                if request.COOKIES.get(key, "") != str(value if value else ""):
                    response.set_cookie(key, value, max_age=max_age, expires=expires,
                                        domain=settings.SESSION_COOKIE_DOMAIN,
                                        secure=settings.SESSION_COOKIE_SECURE or None)
                    modified_cookies = True

        if user and not user.is_authenticated():
            cookies_to_delete = [x for x in ('cur_username','cur_userid','cur_email',
                                         'cur_first_name','cur_last_name',
                                         'cur_other_user','cur_retTitle',
                                         'cur_admin', 'cur_roles',
                                         'cur_yog', 'cur_grade',
                                         'cur_qsd_bits') if request.COOKIES.get(x, False)]

            map(response.delete_cookie, cookies_to_delete)
            modified_cookies = (len(cookies_to_delete) > 0)

        request.session.accessed = request.session.modified  ## Django only uses this for determining whether it refreshed the session cookie (and so needs to vary on cache), and its behavior is buggy; this works around it. -- aseering 11/1/2010

        if modified_cookies:
            patch_vary_headers(response, ('Cookie',))

        return response


