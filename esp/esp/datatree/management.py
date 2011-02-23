from __future__ import with_statement

__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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

from django.db.models import signals
from esp.datatree import models as datatree
from esp.utils.custom_cache import custom_cache
from esp.utils.migration import missing_db_table
from esp.program import models as program_models
from esp.users import models as users_models

have_already_installed = False

def post_syncdb(sender, app, **kwargs):
    global have_already_installed
    if app == datatree and not have_already_installed:     
       with custom_cache():
            have_already_installed = True

            #   Check that required tables exist.
            if missing_db_table(program_models.ClassSubject, check_fields=False):
                raise Exception('DataTree post_syncdb missing table %s' % 'program_models.ClassSubject')
                
            if missing_db_table(users_models.UserBit, check_fields=False):
                raise Exception('Warning: DataTree post_syncdb missing table %s' % 'users_models.UserBit')

            print "Installing esp.datatree initial data..."
            datatree.install()

            from django.db import connection
            cursor = connection.cursor()
            f = open("datatree/sql/datatree.postgresql-multiline.sql")
            cursor.execute(f.read())
            f.close()
        
signals.post_syncdb.connect(post_syncdb)

