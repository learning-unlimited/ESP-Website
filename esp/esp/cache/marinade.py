""" Converts a set of arguments to a string """
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 MIT ESP

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

from django.db.models import Model
from django.contrib.auth.models import AnonymousUser

def marinade_dish(arg):
    if isinstance(arg, Model):
        if not isinstance(arg, AnonymousUser) and arg.id is None:
            import random
            # TODO: Make this log something
            print "PASSING UNSAVED MODEL!!! ERROR!!! CACHING CODE SHOULD NOT BE ENABLED!!!"
            # Do the right thing anyway
            return str(random.randint(0,999999))
        return str(arg.id)
    if hasattr(arg, '__marinade__'):
        return arg.__marinade__()
    return str(arg)

def incorporate_given(argspec, args, kwargs):
    if argspec[0] is None:
        return
    for name, val in zip(argspec[0], args):
        kwargs[name] = val
    num_nargs = len(argspec[0])
    num_sargs = len(args)
    num_match = min(num_nargs, num_sargs)
    return args[num_match:]

def incorporate_defaults(argspec, kwargs):
    if argspec[0] is None or argspec[3] is None:
        return
    num_args = len(argspec[0])
    num_defs = len(argspec[3])
    for i in range(num_defs):
        arg = argspec[0][num_args-1 - i]
        if not kwargs.has_key(arg):
            kwargs[arg] = argspec[3][num_defs-1 - i]

def normalize_args(argspec, args, kwargs):
    kwargs = kwargs.copy()
    rest_args = incorporate_given(argspec, args, kwargs)
    incorporate_defaults(argspec, kwargs)
    return kwargs, rest_args

def args_to_key(argspec, kwargs, rest_args):
    # TODO: don't make so many copies?
    kwargs = kwargs.copy()
    ans = '|'

    if argspec[0] is not None:
        for named_arg in argspec[0]:
            ans += marinade_dish(kwargs[named_arg])
            ans += '|'
            del kwargs[named_arg] # don't duplicate these
    ans += '/r|'

    if rest_args is not None:
        for arg in rest_args:
            ans += marinade_dish(arg)
            ans += '|'
    ans += '/k|'

    for key in sorted(kwargs.keys()):
        ans += '%s=%s|' % (key, marinade_dish(kwargs[key]))
    return ans

# It's kinda like pickling, but not quite
def marinade(func, args, kwargs):
    """ Given a function, args, and kwargs, return a cache key """
    # TODO: don't recompute this one all the time
    import inspect
    argspec = inspect.getargspec(func)

    kwargs, rest_args = normalize_args(argspec, args, kwargs)

    return args_to_key(argspec, kwargs, rest_args)
