
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
from esp.users.models import UserBit
from esp.middleware   import ESPError
from django.contrib.auth.decorators import login_required

def UserHasPerms(branch, verb, error_msg = 'You do not have permission to view this page.', log = False):
    """ This should be used as a decorator. It checks to see if a user has the verb
        on the branch and will complain according to the error_msg.                 """


    def _checkUserDecorator(func):

        @login_required
        def _checkUser(request, *args, **kwargs):

            if not UserBit.UserHasPerms(qsc = branch, verb = verb, user = request.user):
                raise ESPError(log), error_msg

            return func(request, *args, **kwargs)


        return _checkUser

    return _checkUserDecorator


