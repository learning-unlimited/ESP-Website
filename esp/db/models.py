""" ESP's own implementation of the Q objects as spelled out by django. """

from django.db.models.query import Q as DjangoQ, QAnd as DjangoQAnd, QOr as DjangoQOr, QOperator as DjangoQOperator, QNot, parse_lookup
from django.utils.datastructures import SortedDict

class qlist(list):
    def count(self):
        return len(self)
    
    def filter(self, *args, **kwargs):
        if len(self) == 0:
            return []
        model = type(self[0])

        return model.objects.filter(id__in = [x.id for x in self]).filter(*args, **kwargs)
        


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
        
        for item, key in joins.items():
            joins2[item] = (key[0], join_text, key[2])

        self.set_or = False # remove the fact that we know if we're OR'd
        
        return joins2, where, params

