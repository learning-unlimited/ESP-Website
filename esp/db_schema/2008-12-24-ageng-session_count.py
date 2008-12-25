#!/usr/bin/python

""" Database schema update script for ClassSubject.session_count """

from django.db import connection, transaction
from esp.program.models import ClassSubject
import sys

transaction.enter_transaction_management()

cursor = connection.cursor()

# Check for existence of program_class.session_count.
# No, I don't understand this code; I got it from here:
# <http://www.postgresqlforums.com/forums/viewtopic.php?f=10&t=152>
cursor.execute( """SELECT COUNT(*)
FROM pg_catalog.pg_stat_user_tables as t, pg_catalog.pg_attribute a
WHERE t.relid = a.attrelid
AND a.attname='session_count' AND t.relname='program_class'""" )


if cursor.fetchall()[0][0] == 1:
    print 'Column already exists. Skipping column creation.'
else:
    print 'Adding column...'
    for c in ['ALTER TABLE program_class ADD COLUMN session_count integer',
              'ALTER TABLE program_class ALTER COLUMN session_count SET STORAGE PLAIN']:
        cursor.execute( c )
    print '    OK'

# Now go through and make sure ClassSubjects have session_count set.
print 'Looking for classes where session_count is None...'
unsetclasses = ClassSubject.objects.filter(session_count__isnull=True)
for c in unsetclasses:
    c.session_count=1
    c.save()
if unsetclasses.count() > 0:
    print '    OK'
else:
    print '    OK (no writes necessary)'

# Once that's done, it's safe to prohibit further empty values.
# This lets us make convenient assumptions elsewhere.
print 'Setting NOT NULL on program_class.session_count...'
cursor.execute( 'ALTER TABLE program_class ALTER COLUMN session_count SET NOT NULL' )
print '    OK'

print 'Committing changes to database...'
transaction.commit()
print '    OK'
transaction.leave_transaction_management()
print 'Done.'
