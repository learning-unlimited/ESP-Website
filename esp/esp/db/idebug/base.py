# Database wrapper which lets us turn SQL timing/debugging on 
# and off on the production server.

import sys
from django.conf import settings

### THIS DOES: from <realfile> import *
realfile = 'django.db.backends.%s.base' % settings.REAL_DATABASE_ENGINE
__import__(realfile, globals(), locals(), [], -1)
globals().update(sys.modules[realfile].__dict__)
### 


RealDatabaseWrapper = DatabaseWrapper

class DatabaseWrapper(RealDatabaseWrapper):
    idebug = False

    def idebug_on(self):
        self.idebug = True
        self.queries = []

    def idebug_off(self):
        self.idebug = False
        self.queries = []


    # This function should mirror 
    # "django.db.backends.BaseDatabaseWrapper.cursor".
    # The only thing added is the "or self.idebug"
    def cursor(self):
        from django.conf import settings
        cursor = self._cursor()
        if settings.DEBUG or self.idebug:
            return self.make_debug_cursor(cursor)
        return cursor
