""" Boohoo, the cache is sad... """
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

import traceback

from django.core.mail import mail_admins

from esp.cache.registry import caches_locked

__all__ = ['warn_if_loaded']

DEFAULT_SUBJECT = 'ERROR: Uninitialized cache.'
DEFAULT_MESSAGE = \
"""
For the purposes of signal creation, caches must be loaded when the server
imports everything. You probably created a cache in a module Django doesn't
know about. Just explicitly import this module in the __init__.py of some
installed app.

For future signals, files in models.py under any INSTALLED_APPS are
automatically imported. Also, in our code, views.py tend to be as well.

The cache in question has emptied itself for safety, so nothing has caught on
fire, but please address this issue.

Another possibility is that esp.urls is being imported. This calls
admin.autodiscover() and interferes with the cache loading mechanism because
Django lacks a well-thought-out signal mechanism. If you need esp.urls, move
things around so that you don't.
"""

def warn_if_loaded(subject=DEFAULT_SUBJECT, message=DEFAULT_MESSAGE):
    if caches_locked():
        message += '\n--------\n'
        for line in traceback.format_stack():
            message += line
        print message
        mail_admins(subject, message, fail_silently=True)
        return True
    return False
