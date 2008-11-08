"""
This Q object is responsible for handling the low-level SQL queries for
Trees.
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
from copy import deepcopy
from django.utils import tree

from django.db import connection, models, transaction
from django.db.models.sql.where import WhereNode
from django.db.models.sql.constants import LOOKUP_SEP
from django.db.models.query_utils import Q, QueryWrapper
from django.core.exceptions import FieldError


DataTree = None

__all__ = ('QTree',)

def _import_datatree():
    global DataTree
    if not DataTree:
        from esp.datatree.models import DataTree, GetNode, QTree, get_lowest_parent, StringToPerm, PermToString
direction_map = {
    'below': ('gte', 'lte'),
    'above': ('lte', 'gte'),
    'aboveonly': ('lt', 'gte'),
    'belowonly': ('gt', 'lte'),
}

# How to negate the query:
REVERSE = {
    'below': 'aboveonly',
    'above': 'belowonly',
    'aboveonly': 'below',
    'belowonly': 'above',
}

COLUMNS = ['rangestart', 'rangeend']
TOKENS = [-10111, -10141]
WHERE_QUERY = u'%%s.%%s %s (SELECT %%s FROM %%s WHERE %%s = %%%%s)'

qn = connection.ops.quote_name

class QTree(Q):
    """
    The QTree object allows one to filter using Tree semantics.

    This adds two new query types:
        ancestor and descendant.

    Suppose you have a DataTree item, x.
    To get all of the objects with a datatree whose anscestor is x, do:
        descendants = DataTree.objects.filter(QTree(ancestor = x))

    """
    kwargs = {}

    def __init__(self, **kwargs):
        _import_datatree()

        if not kwargs:
            raise ValueError("DataTree filter requires at least one filter expression.")

        for key, value in kwargs.items():
            query_type = key.rsplit(LOOKUP_SEP, 1)[-1]
            if query_type[-3:] == '_id':
                query_type = query_type[:-3]
            if query_type not in direction_map:
                raise FieldError("%r must be one of %s." %
                                 (query_type, direction_map.keys()))
            if not isinstance(value, (DataTree, int, long)) :
                raise ValueError("%r must be a DataTree or int object." % value)
        super(QTree, self).__init__(**kwargs)

    def add_to_query(self, query, used_aliases):
        """
        This function actually does the magic of adding the necessary
        information to the query object.
        """
        _import_datatree()
        query.pre_sql_setup()

        for item in self.children:
            self._handle_filter(query, item, used_aliases)

    def _handle_filter(self, query, item, used_aliases):
        # The generic strategy here is:
        # 1. Let Django's SQL system handle all the joins etc
        #    by adding the rangestart and rangeend filters with
        #    dummy data.
        # 2. Iterate over the where tree to pickup the spurious
        #    where clauses generated in (1), and replace them with
        #    appropriate SubWhereNode objects that have their own SQL.

        filter, value = item
        qtype = filter.rsplit(LOOKUP_SEP, 1)
        if len(qtype) == 1:
            qtype = qtype[0]
            query_first = ''
        else:
            query_first = qtype[0] + '__'
            qtype = qtype[1]

        if qtype[-3:] == '_id':
            qtype = qtype[:-3]

        if self.negated:
            qtype = REVERSE[qtype]

        new_q = Q(**{
                LOOKUP_SEP.join((query_first + 'rangestart',
                                direction_map[qtype][0])): TOKENS[0],
                LOOKUP_SEP.join((query_first + 'rangeend',
                                direction_map[qtype][1])): TOKENS[1],
                })
        query.add_q(new_q)
        self._update_where(query, query.where, value)

    def _update_where(self, query, where, value):
        _import_datatree()
        qn = query.quote_name_unless_alias
        new_children = []
        datatree_id = getattr(value, 'id', value)

        if not hasattr(where, 'children'):
            where.children = []
        for child in where.children:
            # We go through each of the children, and look for the ones with:
            #  (i) At least 1 parameter.
            #  (ii) That parameter being equal to the token and the column being equal to the right column
            #       for it to have been generated above.

            if hasattr(child, 'as_sql'):
                # Skip over it, it's not a standard where node.
                self._update_where(query, child, value)
                new_children.append(child)
                continue

            table_alias, name, db_type, lookup_type, value_annot, params = child
            if params:
                for i in range(len(COLUMNS)):
                    if child[1] == COLUMNS[i] and child[5][0] == TOKENS[i]:
                        new_child = list(child)
                        where_query = WHERE_QUERY % (connection.operators[child[3]][:-3])
                        
                        symbols = (child[0], child[1], child[1],
                                   DataTree._meta.db_table,
                                   DataTree._meta.pk.column)
                        new_children.append(SubWhereNode(where_query, symbols, [datatree_id]))
                        break
                else:
                    self._update_where(query, child, value)
                    new_children.append(child)
            else:
                self._update_where(query, child, value)
                new_children.append(child)
        where.children = new_children

    def _combine(self, other, conn):
        # Since this has its own as_sql() function, we have to wrap
        # this inside another Q() to handle the tree traversals.
        # This is pretty easy to do, just call Q(obj).
        if not isinstance(other, Q):
            raise TypeError(other)
        if isinstance(other, QTree):
            other = Q(other)
        obj = Q(deepcopy(self))
        obj.add(other, conn)
        return obj

    def __invert__(self):
        obj = deepcopy(self)
        obj.negated = not self.negated
        obj.children = deepcopy(self.children)
        return obj

    # Fortunately Python can allow us to redefine behavior the other way.
    def __rand__(self, other):
        return self._combine(other, self.AND)

    def __ror__(self, other):
        return self._combine(other, self.OR)


class SubWhereNode(object):
    def __init__(self, query, cols=(), params=()):
        self.query = query
        self.cols = list(cols)
        self.params = params

    def as_sql(self, qn):
        query = self.query % (tuple(map(qn, map(str, self.cols))))
        return query, self.params

    def relabel_aliases(self, change_map, node=None):
        # We have to implement our own relabel_aliases since this isn't a tuple object.
        if self.cols[0] in change_map:
            self.cols[0] = change_map[self.cols[0]]
