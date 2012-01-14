# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from esp.datatree.models import install as datatree_install

class Migration(SchemaMigration):

    depends_on = (
        ("program", "0001_initial"),
        ("users", "0001_initial"),
    )
    
    #   Added IF EXISTS in case the initial data fixture was deferred and hasn't been loaded yet.
    del_fns_str = """
DROP FUNCTION IF EXISTS class__get_enrolled(integer, integer);
DROP FUNCTION IF EXISTS userbit__bits_get_qsc(integer, integer, timestamp with time zone, timestamp with time zone);
DROP FUNCTION IF EXISTS userbit__bits_get_qsc_root(integer, integer, timestamp with time zone, timestamp with time zone, integer);
DROP FUNCTION IF EXISTS userbit__bits_get_user(integer, integer, timestamp with time zone, timestamp with time zone);
DROP FUNCTION IF EXISTS userbit__bits_get_user_real(integer, integer, timestamp with time zone, timestamp with time zone);
DROP FUNCTION IF EXISTS userbit__bits_get_verb(integer, integer, timestamp with time zone, timestamp with time zone);
DROP FUNCTION IF EXISTS userbit__bits_get_verb_root(integer, integer, timestamp with time zone, timestamp with time zone, integer);
DROP FUNCTION IF EXISTS userbit__user_has_perms(integer, integer, integer, timestamp with time zone, boolean);
"""

    def forwards(self, orm):
        #   Force instantiation of datatree initial data if it wasn't already there
        print 'Populating initial datatree...'
        datatree_install()

        try:
            with open("datatree/sql/datatree.postgresql-multiline.sql") as f:
                db.execute(self.del_fns_str)
                db.execute(f.read())
        except Exception, e:
            print "Error:  Exception occurred while migrating PL/PgSQL functions:"
            print e
            print "This migration will only work properly with PostgreSQL; it's not needed with other backends."
            
    def backwards(self, orm):
        # The file should be reverted by now; and it's self-clobbering, so just run it again
        try:
            with open("datatree/sql/datatree.postgresql-multiline.sql") as f:
                db.execute(self.del_fns_str)
                db.execute(f.read())
        except Exception, e:
            print "Error:  Exception occurred while migrating PL/PgSQL functions:"
            print e
            print "This migration will only work properly with PostgreSQL; it's not needed with other backends."
            
    complete_apps = ['datatree']
