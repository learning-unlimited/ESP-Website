
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
""" ESP's own implementation of the Q objects as spelled out by django. """

from django.db.models.query import Q as DjangoQ, QAnd as DjangoQAnd, QOr as DjangoQOr, QOperator as DjangoQOperator, QNot as DjangoQNot, parse_lookup
from django.utils.datastructures import SortedDict

class qlist(list):
    def count(self):
        return len(self)
    
    def filter(self, *args, **kwargs):
        if len(self) == 0:
            return []
        model = type(self[0])

        return model.objects.filter(id__in = [x.id for x in self]).filter(*args, **kwargs)

def replaceDict(string, dict):
    " Will take a dictioary and an arbitrary string, and replace the string with the dictioary."
    if len(dict) == 0:
        return string
    
    curDict = dict.copy()
    keys = curDict.keys()
    keys.sort(lambda x,y: cmp(len(y), len(x)))
    key = keys[0]
    val = curDict[key]

    del curDict[key]

    offset  = 0
    strings = [string]

    
    while strings[-1].find(key) != -1:
        loc = strings[-1].find(key)
        
        strings.append(strings[-1][len(key) + loc:])

        strings[-2] = strings[-2][:loc]
        

    return val.join([replaceDict(s,curDict) for s in strings])
    

    

class QSplit(DjangoQ):
    " Encapsulates a single JOIN-type query into one object "
    set_or = False

    def __init__(self, q):
        " Creates a single Q-ish object that separates itself from other Q objects. "
        self.q = q

    def set_OR(self, or_value):
        """ Set the value of .inside_or """

        if self.set_or:
            return
        
        self.set_or    = True

        self.q.set_OR(or_value) # set the value for all the children


    def some_OR_exists(self):
        """ Returns true if an OR exists. """
        return self.q.some_OR_exists()

    def get_sql(self, opts):
        from django.conf import settings

        tick = settings.DATABASE_ENGINE == 'mysql' and "`" or '"'
        
        joins, where, params = self.q.get_sql(opts)
        key_replace = {}
        joins2      = {}
        where2      = []
        

        for key, val in joins.items():
            cur_key = key.strip(tick)
            cur_val = '%s__%s' % (key.strip(tick), hash(self))
            
            key_replace[cur_key] = cur_val

            joins2['%s%s%s' % (tick, cur_val, tick)] = val

            

        for key, val in joins2.items():
            joins2[key] = (val[0],val[1],replaceDict(val[2],key_replace))
            
        for key, val in joins2.items():
            joins2[key] = val

        where2 = [replaceDict(clause, key_replace) for clause in where]


        return joins2, where2, params

class QNot(DjangoQNot):
    "Encapsulates NOT (...) queries as objects"
    set_or = False
    
    def __init__(self, q):
        "Creates a negation of the q object passed in."
        self.q = q

    def get_sql(self, opts):
        joins, where, params = self.q.get_sql(opts)
        where2 = ['(NOT (%s))' % " AND ".join(where)]
        return joins, where2, params

    def set_OR(self, or_value):
        """ Set the value of .inside_or """

        if self.set_or:
            return
        
        self.set_or    = True

        self.q.set_OR(or_value) # set the value for all the children


    def some_OR_exists(self):
        """ Returns true if an OR exists. """
        return self.q.some_OR_exists()


class QOperator(DjangoQOperator):
    "Base class for QAnd and QOr"
    inside_or = False
    set_or    = False

    def set_OR(self, or_value):
        """ Set the value of .inside_or """

        if self.set_or:
            return
        
        self.inside_or = or_value # set this value
        self.set_or    = True

        
        for val in self.args:
            val.set_OR(or_value) # set the value for all the children

    def some_OR_exists(self):
        """ Returns true if an OR exists. """
        
        if type(self) == QOr:
            return True
        
        for val in self.args:
            if val.some_OR_exists():
                return True

        return False
            
        
    def get_sql(self, opts):

        if not self.set_or:
            some_OR_exists = self.some_OR_exists()
            self.set_OR(some_OR_exists)

        self.set_or = False # remove the fact that we know if we're OR'd
        
        return super(QOperator, self).get_sql(opts)


class QAnd(QOperator, DjangoQAnd):
    "Encapsulates a combined query that uses 'AND'."
    operator = ' AND '
    def __or__(self, other):
        return QOr(self, other)

    def __and__(self, other):
        if isinstance(other, QAnd):
            return QAnd(*(self.args+other.args))
        elif isinstance(other, (Q, QOr)):
            return QAnd(*(self.args+(other,)))
        else:
            raise TypeError, other

class QOr(QOperator, DjangoQOr):
    "Encapsulates a combined query that uses 'OR'."
    operator = ' OR '
    def __and__(self, other):
        return QAnd(self, other)

    def __or__(self, other):
        if isinstance(other, QOr):
            return QOr(*(self.args+other.args))
        elif isinstance(other, (Q, QAnd)):
            return QOr(*(self.args+(other,)))
        else:
            raise TypeError, other

class Q(DjangoQ):
    "Encapsulates queries as objects that can be combined logically."
    inside_or = False # Whether or not this Q is inside an or
    set_or    = False

    def some_OR_exists(self):
        return False

    def set_OR(self, value):
        if not self.set_or:
            self.inside_or = value
            self.set_or    = True

    def __and__(self, other):
        return QAnd(self, other) # not django's QAnd

    def __or__(self, other):
        return QOr(self, other) # not django's QOr

    def get_sql(self, opts):

        if self.inside_or:
            join_text = 'LEFT OUTER JOIN'
        else:
            join_text = 'INNER JOIN'
        
        joins, where, params = parse_lookup(self.kwargs.items(), opts)
        joins2 = joins
        where2 = where

        for item, key in joins.items():
            if self.inside_or:
                where2 += [key[2]]
            
            joins2[item] = (key[0], join_text, key[2])
        #assert False, key
        self.set_or = False # remove the fact that we know if we're OR'd
        
        return joins2, where2, params


