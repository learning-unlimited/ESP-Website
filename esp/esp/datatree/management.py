from __future__ import with_statement

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


from django.dispatch import dispatcher
from django.db.models import signals 
from esp.datatree import models as datatree
from esp.utils.custom_cache import custom_cache

have_already_installed = False

def post_syncdb(sender, app, **kwargs):
    global have_already_installed
    if app == datatree and not have_already_installed:
        with custom_cache():
            have_already_installed = True

            print "Installing esp.datatree initial data..."
            datatree.install()

            from django.db import connection
            cursor = connection.cursor()
            f = open("datatree/sql/datatree.postgresql-multiline.sql")
            cursor.execute(f.read())
            f.close()
        
signals.post_syncdb.connect(post_syncdb)

