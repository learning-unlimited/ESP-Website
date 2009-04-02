
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

__all__ = ['register_cache', 'cache_by_uid', 'dump_all_caches', 'caches_locked']

all_caches = {}

def register_cache(cache_obj):
    all_caches[cache_obj.uid] = cache_obj

def cache_by_uid(uid):
    return all_caches.get(uid, None)

def dump_all_caches():
    for c in all_caches.values():
        c.delete_all()

def _finalize_caches():
    for c in all_caches.values():
        c.run_all_delayed()
        print c.pretty_name

_caches_locked = False
def caches_locked():
    return _caches_locked

def _lock_caches():
    global _caches_locked
    _caches_locked = True
