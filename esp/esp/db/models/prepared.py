from django.conf import settings
from django.db.models.query import QuerySet, EmptyResultSet
from django.db.models.sql.query import GET_ITERATOR_CHUNK_SIZE
from django.db.models.manager import Manager
from django.db.models import Model
from django.db import backend, connection, transaction

__all__ = ['ProcedureManager']

class PreparedStatementError(Exception):
    pass

class QuerySetLimitationError(PreparedStatementError):
    pass

class InvalidSQLProcedure(PreparedStatementError):
    pass


if 'mysql' in settings.DATABASE_ENGINE.lower():
    prepared_command = 'CALL'
    db_mysql = True
else:
    prepared_command = 'SELECT * FROM'
    db_mysql = False

class QuerySetPrepared(QuerySet):
    """A QuerySet that represents the resultset of
    a procedure -- either through MySQL's CALL
    or PostgreSQL's stored functions.

    USAGE
    =====
    To obtain one of these objects, simply
    do::

        result = Model.objecs.filter_by_procedure('procedure_name',arg1, ...)

    LIMITATIONS
    ===========
    Since there are a lot of limitations in MySQL with stored procedures,
    you cannot do much with this. You cannot filter, exclude, order, or
    otherwise modify this query.
    """

    def __init__(self, *args, **kwargs):
        """ Define the procedure variables. """
        self._proc_params = ()
        self._proc_name = ''
        super(QuerySetPrepared, self).__init__(*args, **kwargs)
    
    def iterator(self):
        """ Like the Django iterator except is used for calling stored
        procedures.
        """
        # set the params that we're going to call the stored procedure of
        proc_params = self._proc_params

        proc_name = self._proc_name

        try:
            select, sql, params = self._get_sql_clause()
        except EmptyResultSet:
            raise StopIteration

        index_start = len(sql)

        for token in (' ORDER BY ', ' WHERE ', ' LIMIT ',):
            current_index = sql.find(token)
            if current_index != -1 and current_index < index_start:
                index_start = current_index

        if index_start == len(sql) or db_mysql:
            where_clause = ''
        else:
            where_clause = sql[index_start:].replace('"%s".' % self.model._meta.db_table, '')

        cursor = connection.cursor()
        cursor.execute("%s %s(%s)%s" % (prepared_command,
                                        proc_name,
                                        ', '.join('%s' for x in proc_params),
                                        where_clause),
                        proc_params+params)

        model_keys = [f.column for f in self.model._meta.fields]

        while 1:
            rows = cursor.dictfetchmany(GET_ITERATOR_CHUNK_SIZE)
            if not rows:
                raise StopIteration
            for row in rows:
                # very simple "return result of procedure"
                try:
                    args = [row[model_key] for model_key in model_keys]
                except KeyError:
                    raise InvalidSQLProcedure("'%s' does not provide the all the correct columns for the model, %s" %
                                              (proc_name, tuple(model_keys)))
                object_ = self.model(*args)
                object_.__dict__.update(row)
                yield object_


    def count(self):
        """ Counts the number of objects this queryset represents. """
        if self._result_cache is not None:
            return len(self._result_cache)
                # since we're using a stored procedure/prepared statement,
        # we cannot use COUNT

        if db_mysql:
            return len(self._get_data())
        else:

            counter = self._clone()

            offset = counter.query.high_mark
            limit = counter.query.low_mark

            
            cursor = connection.cursor()
            cursor.execute('SELECT COUNT(*) FROM %s(%s)' % (self._proc_name,
                                                            ', '.join('%s' for x in self._proc_params)),
                           self._proc_params)
            count = cursor.fetchone()[0]

            if offset:
                count = max(0, count-offset)
            if limit:
                count = min(limit, count)

            return count

    def complain(self, *args, **kwargs):
        raise QuerySetLimitationError("You cannot perform this operation on a query that uses prepared statements or stored procedures.")

    def complain_optionally(method):
        """ Complain only if the database backend is MySQL. """

        if db_mysql:
            return QuerySet.complain
        else:
            return method

    # These functions are not allowed when used with MySQL's Stored Procedures
    _filter_or_exclude = complain_optionally(QuerySet._filter_or_exclude)
    complex_filter = complain_optionally(QuerySet.complex_filter)
    order_by = complain_optionally(QuerySet.order_by)
    distinct = complain_optionally(QuerySet.distinct)

    # These functions will not work with any of this.
    values = complain
    dates = complain
    delete = complain
    extra = complain
    select_related = complain
    in_bulk = complain

    def __getitem__(self, k):
        if db_mysql:
            return self._get_data().__getitem__(k)
        else:
            return super(QuerySetPrepared, self).__getitem__(k)

    def _clone(self, klass=None, **kwargs):
        """ Clone this queryset to a new one. """
        if klass is None:
            klass = self.__class__
        c = super(QuerySetPrepared, self)._clone(klass, **kwargs)

        c._proc_name = self._proc_name
        c._proc_params = self._proc_params
        return c


class ProcedureManager(Manager):

    """ ``ProcedureManager`` allows Django Models to easily call
    procedures from the database. This manager exposes two
    additional functions to ``Model.objects``::

      - ``values_from_procedure``: Returns a list of tuples that were
                                   returned from the call.

      - ``filter_by_procedure``: Returns a ``QuerySetPrepared`` that represents
                                 the list of objects returned by that procedure.

    USAGE
    =====

    To use, simply add the objects statement in your model. For example::

        class Article(models.Model):
            objects = ProcedureManager()

    Then just call it like any filter::

        Article.objects.filter_by_procedure('articles_with_author', request.user)
    """

    def values_from_procedure(self, proc_name, *proc_params):
        """ Return whatever a result of a procedure is.

        The proc_name is the name of a stored procedure or function.

        This will return a list of dictionaries representing the
        rows and columns of the result.
        """
        new_params = [clean_param(param) for param in proc_params]

        cursor = connection.cursor()
        cursor.execute("%s %s(%s)" % (prepared_command,
                                      proc_name,
                                      ', '.join('%s' for x in new_params)),
                       new_params)

        rows = cursor.dictfetchmany(GET_ITERATOR_CHUNK_SIZE)

        retVal = []

        while rows:
            for row in rows:
                retVal.append(row)
            rows = cursor.dictfetchmany(GET_ITERATOR_CHUNK_SIZE)

        return retVal

    def filter_by_procedure(self, proc_name, *proc_params):
        """ Use this to get a QuerySetPrepared of objects by a
        database procedure.
        """
        query_set = self.get_query_set()
        proc_query_set = QuerySetPrepared()
        proc_query_set.__dict__.update(query_set.__dict__)

        new_params = [clean_param(param) for param in proc_params]

        proc_query_set._proc_name   = proc_name
        proc_query_set._proc_params = new_params

        del query_set

        return proc_query_set


def clean_param(param):
    if hasattr(param, '_get_pk_val'):
        # has a pk value -- must be a model
        return str(param._get_pk_val())
    
    if callable(param):
        # it's callable, should call it.
        return str(param())

    return str(param)
