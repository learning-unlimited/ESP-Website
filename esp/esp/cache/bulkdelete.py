""" Bulk-deletable cache objects. """
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

from django.core.cache import cache
from django.db.models import signals

import string
ascii_set = string.lowercase + string.uppercase + string.digits + r'/=\:;.<>'
length = 7

def _random_string(self):
    """ It's slow, but this function will generate a very dense random object.
        (26 * 2 + 10 + 8) ** 7 == 8235430000000 different possibilities.  """
    import random
    return ''.join(random.choice(ascii_set) for x in range(length))


# For now, this isn't very general. It'll get more reasonable later
class BulkDeleteCache(object):
    """ Implements a cache that allows for dropping the entire cache. """

    global_cache_time = 86400

    @classmethod
    def _global_key(cls):
        return 'BDC::%s:_prefix_key' % cls.prefix

    @classmethod
    def _global_prefix(cls):
        key = cls._global_key()
        global_prefix = cache.get(key)
        if global_prefix is None:
            global_prefix = _random_string(7)
            cache.add(key, global_prefix, cls.global_cache_time)
        return global_prefix

    @classmethod
    def _twiddle_key(cls, key):
        return 'BDC::%s:/%s|%s' % (cls.prefix, key, cls._global_prefix())

    @classmethod
    def delete_all(cls, *args, **kwargs): # kwargs for signals
        """ Dumps everything in this cache. """
        cache.delete(cls._global_key())

    @classmethod
    def get(cls, key):
        key = cls._twiddle_key(key)
        return cache.get(key)

    @classmethod
    def set(cls, key, value, timeout_seconds=None):
        key = cls._twiddle_key(key)
        cache.set(key, value, timeout_seconds)

    @classmethod
    def add(cls, key, value, timeout_seconds=None):
        key = cls._twiddle_key(key)
        return cache.add(key, value, timeout_seconds)

    @classmethod
    def delete(cls, key):
        key = cls._twiddle_key(key)
        cache.delete(key)

    @classmethod
    def depend_on_model(cls, Model):
        """ Dump everything in this cache when Model changes. """
        signals.post_save.connect(cls.delete_all, sender=Model)
        signals.post_delete.connect(cls.delete_all, sender=Model)

