from django.db import transaction

DISABLE_TRANSACTIONS = False

# This is somewhat arbitrary, and generally conservative
ISOLATION_STRINGS_SQLITE = {0: 'DEFERRED', 1: 'IMMEDIATE', 2: 'EXCLUSIVE', 3: 'EXCLUSIVE'}

def set_isolation_level(connection, n):
    if not DISABLE_TRANSACTIONS:
        if hasattr(connection.connection, 'set_isolation_level'):
            return connection.connection.set_isolation_level(n)
        elif hasattr(connection.connection, 'isolation_level'):
            connection.connection.isolation_level = ISOLATION_STRINGS_SQLITE[n]
            return n
        else:
            assert False, "Don't know how to set isolation level for DB backend type '%s'" % (connection.connection)
            
def commit_manually(fn):
    decorated_fn = transaction.commit_manually(fn)
    def _inner(*args, **kwargs):
        if DISABLE_TRANSACTIONS:
            return fn(*args, **kwargs)
        else:
            return decorated_fn(*args, **kwargs)

    return _inner
        
