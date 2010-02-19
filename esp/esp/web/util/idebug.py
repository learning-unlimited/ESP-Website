
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

from django.conf import settings
from esp.users.models import ESPUser
from django.db import models
from django.db import connection
from django.core.cache import cache

CUSTOM_DEBUG_PRINT = { 
        'django.core.handlers.wsgi.WSGIRequest':  [ 'method', 'GET', 'POST', 'COOKIES', 'META' ]
    }

#
# If idebug is enabled and the user is authorized to see debug info, then
# show it to them (load it into the context)
#
def idebug_hook(request, context):

    if not request.idebug:
        return

    # Exit quickly if we're not logged in and no GET flag was given
    logged_in = hasattr(request, 'user') and hasattr(request, 'session') and request.user.is_authenticated()
    has_idebug = 'idebug' in request.GET
    if not logged_in and not has_idebug:
        return

    is_admin = logged_in and ESPUser(request.user).isAdministrator()

    idebug_pw = request.GET['idebug'] if has_idebug else ''
    show = False

    if 'idebug' in request.session:
        show = request.session['idebug']

    if is_admin and has_idebug and idebug_pw == '':
        show = True

    if is_admin and has_idebug and (idebug_pw in ('1', 'on', 'yes', 'True')):
        show = True
        request.session['idebug'] = True

    if idebug_pw in ('0', 'off', 'no', 'False'):
        show = False
        request.session['idebug'] = False

    if len(settings.IDEBUG_PASSWORD) > 4 and (idebug_pw == settings.IDEBUG_PASSWORD):
        show = True

    if not show:
       return

    idebug_data = list()

    # Add the query info first, so we don't capture queries performed during context dump
    for q in connection.queries:
        idebug_data.append( ('QUERY', '(%ss) %s' % (q['time'], q['sql']) ) )

    # Add in cache info
    if hasattr(cache, 'queries'):
        for q in cache.queries:
            idebug_data.append( ('CACHE', '%s(\'%s\') = \'%s\'' % (q['method'], q['key'], q['value']) ) )

    # Loop through the context and dump the contents intelligently
    for subdict in context:
      for k,v in subdict.iteritems():
        idebug_data.append( (k, debug_print(k, v)) )

    context['idebug'] = idebug_data
    return


MAX_DEPTH = 5
def debug_print(name, val, depth = 0):
    import string    

    dspace = "    "*depth
    typename = string.split(str(type(val)))[1][1:-2]
    if name:
        ret = dspace + "%s (%s) = " % (name, typename)
    else:
        ret = dspace + "(%s) " % (typename,)

    if depth > MAX_DEPTH:
        ret += str(val)
    elif val is None:
        ret += "None"
    elif isinstance(val, bool):
        ret += "True" if val else "False"
    elif isinstance(val, (str,unicode)):
        proper = val.replace('\n', '\\n')
        if len(proper) > 160:
            ret += "'" + proper[0:160] + "...'"
        else:
            ret += "'" + proper + "'"
    elif isinstance(val, (int,float,long,complex)):
        ret += str(val)
    elif isinstance(val, list):
        ret += str(val)
    elif isinstance(val, tuple):
        ret += str(val)
    elif isinstance(val, (set,frozenset)):
        ret += str(val)
    elif isinstance(val, models.Model):
        ret += "\n"
        for f in val._meta.fields:
            if hasattr(val, f.name):
              ret += debug_print(f.name, getattr(val, f.name, None), depth + 1)
            else:
              ret += debug_print(f.name, None, depth + 1)
    elif isinstance(val, dict):
        ret += "\n"
        for k,v in val.iteritems():
            ret += debug_print(k, v, depth+1)
    elif typename in CUSTOM_DEBUG_PRINT:
        rule = CUSTOM_DEBUG_PRINT[typename]
        if isinstance(rule, list):
            ret += "\n"
            for k in rule:
                ret += debug_print(k, getattr(val, k, None), depth + 1)
    else:
        ret += str(val)

    ret += "\n"

    return ret

