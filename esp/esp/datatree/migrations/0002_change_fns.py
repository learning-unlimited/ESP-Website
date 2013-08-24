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

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    complete_apps = ['datatree']
