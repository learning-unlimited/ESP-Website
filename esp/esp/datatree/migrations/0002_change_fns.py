# encoding: utf-8
import datetime
import os.path
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from esp.datatree.models import install as datatree_install
from django.conf import settings


class Migration(SchemaMigration):

    depends_on = (
        ("program", "0001_initial"),
        ("users", "0010_auto__add_field_contactinfo_receive_txt_message"),
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

        with open(os.path.join(settings.PROJECT_ROOT, "esp/datatree/sql/datatree.postgresql-multiline.sql")) as f:
            db.execute(self.del_fns_str)
            db.execute(f.read())

    def backwards(self, orm):
        # The file should be reverted by now; and it's self-clobbering, so just run it again
        with open(os.path.join(settings.PROJECT_ROOT, "esp/datatree/sql/datatree.postgresql-multiline.sql")) as f:
            db.execute(self.del_fns_str)
            db.execute(f.read())

    complete_apps = ['datatree']
