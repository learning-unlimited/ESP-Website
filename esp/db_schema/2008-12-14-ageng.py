#!/usr/bin/python

""" Change director email fields from 64 to 75, to support full-length EmailField. """

from django.db import transaction, connection

cursor = connection.cursor()


directoremail_update_sql = [
'ALTER TABLE program_program ALTER COLUMN director_email TYPE varchar(75)',
'ALTER TABLE modules_classregmoduleinfo ALTER COLUMN director_email TYPE varchar(75)',
]

[ cursor.execute( c ) for c in directoremail_update_sql ]

