
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 MIT ESP

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

__all__ = ['wildcard', 'is_wildcard']

class WildcardType(object):
    """
    Represents a wildcard. For convenience, a lot of magic functions are
    overriden.
    """

    def __call__(self, *args, **kwargs):
        return self

    def __getattribute__(self, name):
        return self

    def __setattr__(self, name, value):
        return
    def __delattr__(self, name):
        return
    def __getitem__(self, key):
        return self
    def __setitem__(self, key, value):
        return
    def __delitem__(self, key):
        return

    # Bah... I'll get the rest of these later...
    def __add__(self, other):
        return self
    def __radd__(self, other):
        return self
    def __sub__(self, other):
        return self
    def __rsub__(self, other):
        return self
    def __mul__(self, other):
        return self
    def __rmul__(self, other):
        return self
    def __div__(self, other):
        return self
    def __rdiv__(self, other):
        return self
    def __divmod__(self, other):
        return self
    def __rdivmod__(self, other):
        return self
    def __float__(self, other):
        return self
    def __floordiv__(self, other):
        return self

    def __repr__(self):
        return '<*>'

wildcard = WildcardType()

def is_wildcard(obj):
    """ Is the given object a wildcard? """
    return isinstance(obj, WildcardType)

def has_wildcard(lst):
    """ Does this given iterable contain a wildcard? """
    return any([is_wildcard(obj) for obj in lst])

def specifies_key(key_set, key):
    """ Does this key_set have a definite value for key? """
    return key_set.has_key(key) and not is_wildcard(key_set[key])

def token_list_for(key_set):
    """ Given me a list of interesting arguments for key_set. """
    return [key for key,val in key_set.items() if not is_wildcard(val)]
