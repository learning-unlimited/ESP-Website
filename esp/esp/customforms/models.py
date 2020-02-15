from __future__ import with_statement

import logging
logger = logging.getLogger(__name__)

from django.db import models, transaction, connection
from django.db.utils import DatabaseError
from esp.users.models import ESPUser
from esp.program.models import Program

class Form(models.Model):
    title = models.CharField(max_length=40, blank=True)
    description = models.TextField(blank=True)
    date_created = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(ESPUser)
    link_type = models.CharField(max_length=50, blank=True)
    link_id = models.IntegerField(default=-1)
    anonymous = models.BooleanField(default=False)
    perms = models.CharField(max_length=200, blank=True)
    success_message = models.CharField(max_length=500, blank=True)
    success_url = models.CharField(max_length=200, blank=True)

    def __unicode__(self):
        return u'%s (created by %s)' % (self.title, self.created_by.username)

class Page(models.Model):
    form = models.ForeignKey(Form)
    seq = models.IntegerField(default=-1)

    def __unicode__(self):
        return u'Page %d of %s' % (self.seq, self.form.title)

class Section(models.Model):
    page = models.ForeignKey(Page)
    title = models.CharField(max_length=40)
    description = models.CharField(max_length=140, blank=True)
    seq = models.IntegerField()

    def __unicode__(self):
        return u'Sec. %d: %s' % (self.seq, unicode(self.title))

class Field(models.Model):
    form = models.ForeignKey(Form)
    section = models.ForeignKey(Section)
    field_type = models.CharField(max_length=50)
    seq = models.IntegerField()
    label = models.CharField(max_length=200)
    help_text = models.TextField(blank=True)
    required = models.BooleanField(default=False)

    def __unicode__(self):
        return u'%s' % (self.label)

    def set_attribute(self, atype, value):
        from esp.customforms.models import Attribute
        if Attribute.objects.filter(field=self, attr_type=atype).exists():
            attr = Attribute.objects.get(field=self, attr_type=atype)
            attr.value = value
            attr.save()
        else:
            attr = Attribute.objects.create(field=self, attr_type=atype, value=value)
        return attr

class Attribute(models.Model):
    field = models.ForeignKey(Field)
    attr_type = models.CharField(max_length=80)
    value = models.TextField()

from esp.customforms.DynamicForm import *
from esp.customforms.DynamicModel import *

def install():
    logger.info("Creating customforms schema...")
    cursor = connection.cursor()
    create_schema(cursor)

def create_schema(db):
    """ Create customforms schema.

    :param db:
        The database backend you want to use (e.g. Django cursor object, or south.db.db).
    """

    # Forcing this command to run by itself in a transaction. If the
    # customforms schema already exists or the command fails for any
    # other reason, future database queries will not generate "current
    # transaction is aborted, commands ignored until end of transaction
    # block" errors.
    # Warning: This overrides the transaction management of any surrounding code.

    transaction.set_autocommit(False)
    try:
        db.execute("CREATE SCHEMA customforms")
    except:
        transaction.rollback()
    else:
        transaction.commit()
    transaction.set_autocommit(True)
