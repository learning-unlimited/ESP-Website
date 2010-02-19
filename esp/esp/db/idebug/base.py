# Database wrapper which lets us turn SQL timing/debugging on 
# and off on the production server.

from django.db.backends.postgresql.base import *

class IDebugDatabaseWrapper(DatabaseWrapper):
    idebug = False

    def idebug_on(self):
        self.idebug = True
        self.queries = []

    def idebug_off(self):
        self.idebug = False
        self.queries = []


    # This function should mirror "django.db.backends.BaseDatabaseWrapper.cursor"
    # The only thing added is the "or self.idebug"
    def cursor(self):
        from django.conf import settings
        cursor = self._cursor()
        if settings.DEBUG or self.idebug:
            return self.make_debug_cursor(cursor)
        return cursor


IDebugDatabaseWrapper.__name__ = DatabaseWrapper.__name__
DatabaseWrapper = IDebugDatabaseWrapper
