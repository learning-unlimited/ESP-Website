"""
The DataTree organizes the ESP site into a heirarchal structure that
can do some pretty interesting things pretty fast.
"""
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

from django.db import models, connection, transaction, DatabaseError
from django.core.cache import cache

from esp.datatree.sql.query_utils import *
from esp.datatree.sql.constants import *
from esp.datatree.sql.transaction import *

__all__ = ('DataTreeManager',)

# Globals
qn = connection.ops.quote_name
CACHE_TIME = 86400


# SQL TEMPLATES
# Alter the ranges
sql__change_ranges = """
UPDATE %(table)s SET
  rangestart = (CASE WHEN rangestart >= %(lefttest)s THEN
                          rangestart %(offset)s ELSE
                          rangestart END),
  rangeend = (CASE WHEN rangeend >= %(righttest)s THEN
                        rangeend %(offset)s ELSE
                        rangeend END)
WHERE
  rangestart >= %(lefttest)s OR rangeend >= %(righttest)s
"""

# Get the bounds efficiently
sql__get_bounds = """
SELECT %(query)s FROM
 (
   (SELECT rangeend AS upper, (SELECT rangeend FROM %(table)s WHERE id = %%s) - rangeend - '%%s' AS diff FROM %(table)s WHERE parent_id = %%s)
  UNION
   (SELECT rangestart AS upper, rangeend - rangestart - %%s AS diff FROM %(table)s WHERE id = %%s)
 ) AS a
"""

# Insertion
sql__create = """
INSERT INTO %(table)s (name, friendly_name, parent_id, uri, uri_correct, lock_table, range_correct, rangestart, rangeend%(extracols)s)
VALUES (%%s, %%s, %%s, %%s, %%s, %%s, %%s, (%(rangestart)s), (%(rangeend)s)%(extravals)s)
"""

class DataTreeManager(models.Manager):
    cursor = None

    @property
    def qt(self):
        if hasattr(self, '_qt'):
            return self._qt
        return qn(self.model._meta.db_table)

    # Public Interface
    def get(self, *args, **kwargs):
        """
        Returns a DataTree node given the filter specification.
        If the get is only by URI, then a special function
        is used.
        """
        old_kwargs = kwargs.copy()
        if 'uri' in kwargs:
            uri = kwargs.pop('uri', None)
            create = kwargs.pop('create', False)
            if not (len(args) or len(kwargs)):
                return self._get_by_uri(uri=uri, create=create)
        return super(DataTreeManager, self).get(*args, **kwargs)

    @transaction.commit_manually
    @serializable
    def create(self, name, parent, id=None, uri=None, start_size=None, friendly_name=None):
        """
        Create a new DataTree node.
        This will go to great lengths to insert a node safetly into the Tree.
        """

        cursor, created = self.__get_cursor(cache=True, return_created=True)

        opts = self.model._meta
        parent_id = getattr(parent, 'id', parent)

        if not start_size:
            start_size = self.model.START_SIZE

        if not friendly_name:
            friendly_name = name

        # Update the ranges to make sure we fit.
        # Don't use the ranges (we'll update them below to avoid race conditions).
        self.new_ranges(parent, start_size, get_ranges=False)

        if not uri:
            if not isinstance(parent, self.model):
                parent = self.get(id=parent_id)

            uri = self.model.DELIMITER.join((parent.get_uri(), name))
            uri_correct = True

        else:
            uri_correct = True

        id = self._insert_object(name, friendly_name, parent_id, uri, uri_correct, start_size, id=id, force_insert=True)

        transaction.commit()

        connection.connection.set_isolation_level(1)
        node = self.get(id = id)

        if created:
            self.__unset_cursor()

        return node

    def rebuild_tree(self):
        # TODO: Implement this.
        raise NotImplementedError("Need to do this ... ")

    def get_root(self):
        # TODO: Implement this cleaner.
        return self.model.root()

    @transaction.commit_manually
    @serializable
    def new_ranges(self, parent, size=None, get_ranges=True):
        """
        Expand the parent to contain at least size + 1 open slots.
        Returns those ranges. Though you probably don't want to use them.
        """
        if not size:
            size = self.model.START_SIZE
        parent_id = getattr(parent, 'id', parent)
        size_needed = self._expansion_required(parent_id, size)
        if size_needed:
            if not isinstance(parent, self.model):
                parent = self.get(id=parent_id)

            double_range = parent.rangeend - parent.rangestart

            self._change_ranges(parent,
                                left=UPPER,
                                change_size=max(size_needed, double_range))

        if not get_ranges:
            return

        sql = sql__get_bounds % {'table': self.qt, 'query': "MAX(upper) + 1"}

        cursor = self.__get_cursor()
        cursor.execute(sql, [parent_id, 0, parent_id, 0, parent_id])
        result = cursor.fetchone()
        transaction.commit()
        return result[0], result[0] + size - 1

    def exists_violators(self, queryset=False, override=False):
        """
        Returns whether or not there are any violators of the range constraints.
        If queryset=True, returns a queryset to represent this.
        """
        if not override:
            return False
        # these are a list of functions which return violators
        range_sign_sql = self.extra(where = ['rangestart >= rangeend']).values('id')

        if queryset:
            range_sign_sql = range_sign_sql.query.as_sql()[0]
            limit = ""
        else:
            range_sign_sql = range_sign_sql[:1].query.as_sql()[0]
            limit = " LIMIT 1"

        range_nodes_sql = """
SELECT %s.id FROM %s
  INNER JOIN %s AS parent_tree
    ON %s.parent_id = parent_tree.id
WHERE
  %s.rangestart <= parent_tree.rangestart
  OR
  %s.rangeend > parent_tree.rangeend%s""" % \
            (self.qt, self.qt, self.qt, self.qt, self.qt, self.qt, limit)

        cursor = self.__get_cursor()
        full_sql = "SELECT * FROM ((%s) UNION (%s)) AS a%s" % (range_sign_sql, range_nodes_sql, limit)
        cursor.execute(full_sql)
        if not queryset:
            return bool(cursor.fetchall())
        ids = [x[0] for x in cursor.fetchall()]
        return self.filter(id__in = ids)


    def fix_tree_if_broken(self, override=False):
        " This will fix all the broken nodes in the table. "
        if self.model.FIXING_TREE:
            return

        self.model.FIXING_TREE = True

        if not self.exists_violators():
            self.model.FIXING_TREE = False
            return False

        if not override:
            import sys
            sys.stderr.write("TREE IS BROKEN?\n===========================\n!!!!\n")
            raise Exception()

        res = self.exists_violators(queryset=True)
        total = self.count()
        num_bad = res.count()
        if float(num_bad) / float(total) < self.model.PERCENT_BAD:
            # if the tree is "insertable"
            for parent in res.filter(child_set__isnull=False):
                parent.reinsert()

            if not self.exists_violators():
                self.model.FIXING_TREE = False
                return True

        # Performing a full on rebuild.
        self.rebuild_tree()

        self.model.FIXING_TREE = False
        return True

    # Private methods:
    def _expansion_required(self, node, room_required):
        """
        Returns 0 if there is enough room in this node for the
        required space. The amount required otherwise.
        """
        id = getattr(node, 'id', node)
        sql = sql__get_bounds % {
            'table': self.qt,
            'query': "MIN(diff)",
            }

        params = [id, room_required + 1, id, room_required + 1, id]

        cursor = self.__get_cursor()
        cursor.execute(sql, params)
        result = cursor.fetchall()

        if result[0][0] < 0:
            return -result[0][0]
        else:
            return 0

    def _insert_object(self, name, friendly_name, parent_id, uri, uri_correct, start_size, id=None, force_insert=True):
        opts = self.model._meta
        cursor = self.__get_cursor()
        if id:
            extracols = ', id'
            extravals = ', %s'
            if force_insert:
                self.filter(id=id).delete()
        else:
            extracols = ''
            extravals = ''

        sql = sql__create % {
            'table': self.qt,
            'rangestart': sql__get_bounds % {'table': self.qt, 'query': "MAX(upper) + 1"},
            'rangeend': sql__get_bounds % {'table': self.qt, 'query': "MAX(upper) + %s"},
            'extracols': extracols,
            'extravals': extravals,
            }

        if uri:
            uri = uri.strip(self.model.DELIMITER)
        else:
            from random import randint
            uri = "BadURI/%d" % randint(0, 100000)

        params = [name, friendly_name, parent_id, uri, uri_correct, 0, True]
        params += [parent_id, 0, parent_id, 0, parent_id]
        params += [start_size, parent_id, 0, parent_id, 0, parent_id]

        if id:
            params.append(id)

        cursor.execute(sql, params)
        if id:
            return id
        else:
            return connection.ops.last_insert_id(cursor, opts.db_table, opts.pk.name)

    def _change_ranges(self, node, left=LOWER, change_size=-WIDTH):
        """
        Alter the ranges of the table by the rules given:

         - node is the node to do the movement around.
         - left is where the left of the move occurs.
         - change_size is the size of the offset. if WIDTH or -WIDTH, then the
                      width of the node being used is taken into consideration.

        Example:

        A: 1    6
        B:  2  5
        C:   34

        Suppose we wanted to add 4 ranges after C (between 4 and 5).
        We would call:
            _change_ranges(<B>, left=UPPER, change_size=4)
        This means: anything >= 5, move by 4 upward.

        Then we get:
        
        A: 1          10
        B:  2        9
        C:   34

        Leaving B with room to grow.

        Now suppose sometime later, we want B to go away. First we remove its descendants.
        Then, we are left with:

        A: 1         10
        B:  2       9

        Now we call:
            _change_ranges(<B>, left=LOWER, change_size=-WIDTH)

        This means: anything >= 2, move by (9 - 2 + 1) downward.

        So we get: (10 - 8 is 2...)
        A: 12
        """
        id = getattr(node, 'id', node)

        params = []

        if left == LOWER:
            # We move from the lower side of this node.
            test = "(SELECT rangestart FROM %s WHERE id = %%s)" % self.qt
        elif left == UPPER:
            test = "(SELECT rangeend FROM %s WHERE id = %%s)" % self.qt
        else:
            raise AttributeError("Invalid input for _change_ranges. Must be one of LOWER | UPPER.")

        if isinstance(change_size, NodeWidthRep):
            # We use the width of the node for the length.
            offset = "%s (SELECT rangeend - rangestart + 1 FROM %s WHERE id = %%s)" % (change_size, self.qt)
            params = [id, id, id, id, id, id]
        elif isinstance(change_size, (int, long)):
            if change_size < 0:
                offset = "- %s"
            else:
                offset = "+ %s"
            params = [id, abs(change_size), id, abs(change_size), id, id]
        else:
            raise AttributeError("Invalid type for the change_size. Must be an integer or WIDTH.")

        sql = sql__change_ranges % {
            'table': self.qt,
            'lefttest': test,
            'righttest': test,
            'offset': offset,
            }

        cursor = self.__get_cursor()
        cursor.execute(sql, params)

    def _get_by_uri(self, uri, create=False, depth=0):
        delimiter = self.model.DELIMITER
        uri = uri.strip(delimiter)
        cache_key = 'GetNode%s' % uri

        # First use cache:
        if not depth and CACHE_TIME:
            node = cache.get(cache_key)
            if node:
                return node

        # Try to get it directly.
        try:
            return super(DataTreeManager, self).get(uri=uri, uri_correct=True)
        except self.model.DoesNotExist:
            pass

        if not uri:
            return self.get_root()

        pieces = uri.split(delimiter)
        if len(pieces) > self.model.MAX_DEPTH:
            raise self.model.MaxDepthExceeded("You cannot go more than %s levels." % self.model.MAX_DEPTH)

        cur_name = pieces.pop()
        parent_uri = delimiter.join(pieces)
        parent = self._get_by_uri(parent_uri, create, depth + 1)

        try:
            node = super(DataTreeManager, self).get(parent=parent,
                                                    name=cur_name)
            if not depth and CACHE_TIME:
                cache.set(cache_key, node, CACHE_TIME)
            return node

        except self.model.DoesNotExist:
            pass

        if not create:
            raise self.model.DoesNotExist("No node by uri %r" % uri)

        node = None
        for i in range(10):
            try:
                node = self.create(name=cur_name, friendly_name=cur_name, parent=parent,
                                   start_size= 2 * (depth + 1))
            except DatabaseError, e:
                if 'could not serialize access' in str(e.message):
                    continue
                if 'deadlock detected' in str(e.message):
                    continue
                raise e
            if node is not None:
                break
        else:
            raise DatabaseError("Unable to commit to database.")

        if not depth and CACHE_TIME:
            cache.set(cache_key, node, CACHE_TIME)
        return node


    # Very Private methods
    def __get_cursor(self, cache=False, return_created=False):
        if self.cursor is not None:
            if return_created:
                return self.cursor, False
            else:
                return self.cursor
        cursor = connection.cursor()
        if cache:
            self.cursor = cursor
        if return_created:
            return cursor, True
        else:
            return cursor

    def __unset_cursor(self):
        self.cursor = None
