from django.db.models.query import Q as DjangoQ, QNot as DjangoQNot, QAnd as DjangoQAnd, QOr as DjangoQOr, QOperator as DjangoQOperator, parse_lookup
from django.utils.datastructures import SortedDict

class QOperator(DjangoQOperator):
    "Base class for QAnd and QOr"
    def __init__(self, *args):
        self.inside_or = False
        self.set_or    = False
        
        self.args = args

    def set_OR(self, or_value):
        """ Set the value of .inside_or """
        for val in self.args:
            self.inside_or = or_value
            self.set_or    = True

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

        joins, where, params = SortedDict(), [], []
        for val in self.args:
            joins2, where2, params2 = val.get_sql(opts)
            joins.update(joins2)
            where.extend(where2)
            params.extend(params2)


        if where:
            return joins, ['(%s)' % self.operator.join(where)], params
        return joins, [], params

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

    def some_OR_exists(self):
        return False

    def set_OR(self, value):
        self.set_or = True
        self.inside_or = value
    

    def __init__(self, **kwargs):
        self.inside_or = False
        self.set_or    = False
        self.kwargs = kwargs

    def __and__(self, other):
        return QAnd(self, other)

    def __or__(self, other):
        return QOr(self, other)

    def get_sql(self, opts):

        if self.inside_or:
            join_text = 'LEFT OUTER JOIN'
        else:
            join_text = 'INNER JOIN'
        
        joins, where, params = parse_lookup(self.kwargs.items(), opts)
        joins2 = joins
        
        for item, key in joins.items():
            joins2[item] = (key[0], join_text, key[2])

        return joins2, where, params

class QNot(QOperator, DjangoQNot):
    "Encapsulates NOT (...) queries as objects"
    def __init__(self, q):
        "Creates a negation of the q object passed in."
        self.q = q

    def get_sql(self, opts):
        joins, where, params = self.q.get_sql(opts)
        where2 = ['(NOT (%s))' % " AND ".join(where)]
        return joins, where2, params
