
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2010 by the individual contributors
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

from django.db.backends.postgresql_psycopg2.base import DatabaseWrapper as Psycopg2DatabaseWrapper, CursorWrapper
from django.db.backends.postgresql_psycopg2.base import DatabaseError, IntegrityError
from psycopg2 import OperationalError

import thread
#   Global, protected by lock...
connection_cache = {}
connection_cache_lock = thread.allocate_lock()

import re

DEBUG_PRINT = False

#   From http://code.activestate.com/recipes/576698-transparently-execute-sql-queries-as-prepared-stat/
#   Modified to use _execute, store cache locally, print statements, etc.
class PrepCursorMixin(object):
    '''
    mix in with dbapi cursor class
    
    formatRe fishes out all format specifiers for a given paramstyle
    this one works with paramstyles 'format' or 'pyformat'
    '''
    formatRe = re.compile('(\%s|\%\([\w\.]+\)s)', re.DOTALL)

    def __init__(self, *a, **kw):
        connection_cache_lock.acquire()
        self.conn_id = self.cursor.connection.get_backend_pid()
    
        if self.conn_id not in connection_cache:
            if DEBUG_PRINT: print '%s Reset cache for connection' % self.conn_id
            connection_cache[self.conn_id] = {}
            #   Flush existing prepared statements in case the connection has the same hash
            self._execute('DEALLOCATE ALL')

        self.prepCache = connection_cache[self.conn_id]

        if DEBUG_PRINT: 
            #   Check for consistency with prepared statements in DB? Too much overhead...
            self._execute('SELECT COUNT(*) FROM pg_prepared_statements')
            num_prepared = self.fetchall()[0][0]
            print '%s initializing cursor, %d prepared on connection, %d prepared in DB' % (self.conn_id, len(self.prepCache), num_prepared) 

        connection_cache_lock.release()

    def executeps(self, cmd, args=None):
        '''
        execute a command using a prepared statement.
        '''
        #   If we can't get a lock, give up and just execute the query.
        #   No point deadlocking over this.
        if not connection_cache_lock.acquire(0):
            return self._execute(cmd, args)

        #   Also don't bother preparing anything other than SELECTs.
        if not cmd.startswith('SELECT'):
            connection_cache_lock.release()
            return self._execute(cmd, args)
            
        prepStmt = self.prepCache.get(cmd)
        if prepStmt is None:
            cmdId = "ps_%d" % (len(self.prepCache) + 1)  
            # unique name for new prepared statement
            prepStmt = self.prepCache[cmd] = \
                       self.prepareStatement(cmd, cmdId)
            
            if DEBUG_PRINT: print '%d Prepared statement %s for %s...' % (self.conn_id, cmdId, cmd[:30])
        connection_cache_lock.release()
        
        if DEBUG_PRINT: print '%d Using prepared statement %s...' % (self.conn_id, prepStmt[:30])
        
        return self._execute(prepStmt, args)

    def prepareStatement(self, cmd, cmdId):
        '''
        translate a sql command into its corresponding 
        prepared statement, and execute the declaration.
        '''
        specifiers = []

        def replaceSpec(mo):
            specifiers.append(mo.group())
            return '$%d' % len(specifiers)

        replacedCmd = self.formatRe.sub(replaceSpec, cmd)
        prepCmd = 'prepare %s as %s' % (cmdId, replacedCmd)

        if len(specifiers) == 0:    # no variable arguments
            execCmd = 'execute %s' % cmdId

        else:       # set up argument slots in prep statement
            execCmd = 'execute %s(%s)' % (cmdId, ', '.join(specifiers))

        self._execute(prepCmd)
        return execCmd

    def executemanyps(self, cmd, seq_of_parameters):
        '''
        prepared statement version of executemany.
        '''
        for p in seq_of_parameters:
            self.executeps(cmd, p)

        # Don't want to leave the value of the last execute() call
        try:
            self.rowcount = -1 
        except TypeError:   # fooks with psycopg
            pass
#   End of ActiveState snippet

class PreparedCursor(PrepCursorMixin, CursorWrapper):
    """ Wrap the cursor class from the Psycopg2 backend so that it prepares
        queries.
    """
    def __init__(self, cursor):
        self.cursor = cursor
        super(PreparedCursor, self).__init__()

    def _execute(self, query, args=None):
        #   print 'Executing: %s (args=%s)' % (query, args)
        self.cursor.execute(query, args)
        
    def execute(self, query, args=None):
        self.executeps(query, args)
    
    def executemany(self, query, args):
        self.executemanyps(query, args)
        
#   Adapted from http://groups.google.com/group/django-users/msg/6aa7e3e367121e6a

#   This wrapper forces reuse of this connection by every cursor created by 
#   the process.
connection = None

class DatabaseWrapper(Psycopg2DatabaseWrapper):
    def _cursor(self, *args, **kwargs):
        global connection
        if connection is not None and self.connection is None:
            try: # Check if connection is alive
                connection.cursor().execute('SELECT 1')
            except OperationalError: # The connection is not working, need reconnect
                connection = None
            else:
                self.connection = connection
        cursor = super(DatabaseWrapper, self)._cursor(*args, **kwargs)
        if connection is None and self.connection is not None:
            connection = self.connection
        return PreparedCursor(cursor)
    
    def close(self):
        if self.connection is not None:
            self.connection.commit()
            self.connection = None
