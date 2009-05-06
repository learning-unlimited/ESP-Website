#!/usr/bin/python

"""
Database Schema Tracker

    $ ./db_schema_done.py

Updates [DATABASE_NAME]-current-schema tag to HEAD.
Run this if and only if everything db_schema_notify.py lists has been handled.
"""

import sys, os
from esp.settings import DATABASE_NAME

# Tag for keeping track of current schema
TAG_NAME = '%s-current-schema' % DATABASE_NAME

os.system( 'git tag -f %s HEAD' % TAG_NAME )
print 'Tag %s now points to HEAD.\nThanks for handling the schema update!' % TAG_NAME
