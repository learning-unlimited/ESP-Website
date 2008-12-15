#!/usr/bin/python

""" Database schema update script to fix ClassSubject durations. """


from django.db import transaction, connection

cursor = connection.cursor()


# SO I probably don't actually need this cast...
classsubject_update_sql = [
'ALTER TABLE program_class RENAME COLUMN duration TO duration_float',
'ALTER TABLE program_class ADD COLUMN duration numeric(5,2)',
'ALTER TABLE program_class ALTER COLUMN duration SET STORAGE MAIN',
'UPDATE program_class SET duration = CAST(duration_float AS numeric(5,2))',
'ALTER TABLE program_class DROP COLUMN duration_float',
]

[ cursor.execute( c ) for c in classsubject_update_sql ]

