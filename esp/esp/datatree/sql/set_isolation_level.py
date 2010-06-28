from django.db import transaction

DISABLE_TRANSACTIONS = False


def set_isolation_level(connection, n):
    if not DISABLE_TRANSACTIONS:
        return connection.connection.set_isolation_level(n)

def commit_manually(fn):
    decorated_fn = transaction.commit_manually(fn)
    def _inner(*args, **kwargs):
        if DISABLE_TRANSACTIONS:
            return fn(*args, **kwargs)
        else:
            return decorated_fn(*args, **kwargs)

    return _inner
        
