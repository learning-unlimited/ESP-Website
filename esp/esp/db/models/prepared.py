from django.conf import settings
from django.db.models.query import QuerySet, EmptyResultSet
from django.db.models.sql.query import GET_ITERATOR_CHUNK_SIZE
from django.db.models.manager import Manager
from django.db.models import Model
from django.db import backend, connection, transaction

__all__ = ['ProcedureManager']

""" dictfetchmany:
    Function borrowed from psycopg1 so that we can support
    other database backends that don't define dictfetchmany.
"""
def _build_dict(cursor, row):
    res = {}
    for i in range(len(cursor.description)):
        res[cursor.description[i][0]] = row[i]
    return res
    
def dictfetchmany(cursor, size):
    if hasattr(cursor, 'dictfetchmany'):
        return cursor.dictfetchmany(size)
    else:
        res = []
        rows = cursor.fetchmany(size)
        for row in rows:
            res.append(_build_dict(cursor, row))
        return res

class PreparedStatementError(Exception):
    pass

class QuerySetLimitationError(PreparedStatementError):
    pass

class InvalidSQLProcedure(PreparedStatementError):
    pass


if 'mysql' in settings.DATABASES['default']['ENGINE'].lower():
    prepared_command = 'CALL'
    db_mysql = True
else:
    prepared_command = 'SELECT * FROM'
    db_mysql = False

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

        rows = dictfetchmany(cursor, GET_ITERATOR_CHUNK_SIZE)

        retVal = []

        while rows:
            for row in rows:
                retVal.append(row)
            rows = dictfetchmany(cursor, GET_ITERATOR_CHUNK_SIZE)

        return retVal

    def filter_by_procedure(self, proc_name, *proc_params):
        """ Use this to get a QuerySetPrepared of objects by a
        database procedure.
        """
        query_set = self.get_query_set()
        proc_query_set = QuerySetPrepared()
        proc_query_set.__dict__.update(query_set.__dict__)

        # Dirty ugly hack to deal with "None" arguments.
        # If we don't do this, our procedure gets passed the string "None"
        new_params = []
        for param in proc_params:
            if None not in (param, getattr(param, 'id', True)):
                new_params.append(clean_param(param))
            else:
                new_params.append(-10)

        # Here's the more-efficient Python 2.5 equivalent to the above for-loop:
        #new_params = [(clean_param(param) if param != None and getattr(param, 'id', True) != None else -10) for param in proc_params]

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
