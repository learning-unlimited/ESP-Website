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

from django.contrib.auth.middleware import LazyUser, AuthenticationMiddleware
from esp.utils.get_user import get_user

__all__ = ('ESPAuthMiddleware',)

ESPUser = None
get_user_django = None

class ESPLazyUser(LazyUser):
    def __get__(self, request, obj_type=None):
        global get_user_django, ESPUser
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
