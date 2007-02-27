from django.db.models.query import Q as DjangoQ, QNot as DjangoQNot, QAnd as DjangoQAnd, QOr as DjangoQOr, QOperator as DjangoQOperator, parse_lookup


class QOperator(DjangoQOperator):
    "Base class for QAnd and QOr"
    def __init__(self, *args):
        self.args = args

    def get_sql(self, opts):
        joins, where, params = SortedDict(), [], []
        for val in self.args:
            joins2, where2, params2 = val.get_sql(opts)
            joins.update(joins2)
            where.extend(where2)
            params.extend(params2)
        if where:
            return joins, ['(%s)' % self.operator.join(where)], params
        return joins, [], params

class QAnd(DjangoQAnd):
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

class QOr(DjangoQOr):
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
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __and__(self, other):
        return QAnd(self, other)

    def __or__(self, other):
        return QOr(self, other)

    def get_sql(self, opts):
        return parse_lookup(self.kwargs.items(), opts)

class QNot(DjangoQNot):
    "Encapsulates NOT (...) queries as objects"
    def __init__(self, q):
        "Creates a negation of the q object passed in."
        self.q = q

    def get_sql(self, opts):
        joins, where, params = self.q.get_sql(opts)
        where2 = ['(NOT (%s))' % " AND ".join(where)]
        return joins, where2, params
