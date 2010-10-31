"""
The DataTree organizes the ESP site into a heirarchal structure that
can do some pretty interesting things pretty fast.
"""
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
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
from django.db import models, connection, transaction
from esp.datatree.sql.set_isolation_level import *

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps

from collections import deque

__all__ = ('serializable',)

# TODO: Make this thread-safe using locals/thread dict ...
#       [Read django.db.transaction.py for an easy example.]
isolation_levels = deque([1])

def serializable(func):
    def _serializable(self, *args, **kwargs):
        try:
            transaction.commit()
        except:
            pass
        self.cursor = None
        set_isolation_level(connection, 2)
        isolation_levels.append(2)
        try:
            return func(self, *args, **kwargs)
        finally:
            try:
                transaction.commit()
            except:
                pass
            if len(isolation_levels) < 2:
                set_isolation_level(connection, 1)
            else:
                level = isolation_levels.pop()
                old_level = isolation_levels[-1]
                set_isolation_level(connection, old_level)
    return wraps(func)(_serializable)
