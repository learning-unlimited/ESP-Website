#!/usr/bin/python

""" Database schema update script for ClassSubject.session_count """

from django.db import connection, transaction
from esp.program.models import ClassSubject
import sys

transaction.enter_transaction_management()

cursor = connection.cursor()


print 'Updating program_programmodule (Program Modules)...'
cursor.execute( 'ALTER TABLE program_programmodule ALTER COLUMN aux_calls TYPE varchar(1024)' )
print '    OK'

scrmi_update_sql = [
'ALTER TABLE modules_studentclassregmoduleinfo ADD COLUMN signup_verb_id integer',
'ALTER TABLE modules_studentclassregmoduleinfo ALTER COLUMN signup_verb_id SET STORAGE PLAIN',
'ALTER TABLE modules_studentclassregmoduleinfo ADD COLUMN use_priority boolean',
'ALTER TABLE modules_studentclassregmoduleinfo ALTER COLUMN use_priority SET STORAGE PLAIN',
'ALTER TABLE modules_studentclassregmoduleinfo ALTER COLUMN use_priority SET DEFAULT false',
'ALTER TABLE modules_studentclassregmoduleinfo ADD COLUMN priority_limit integer',
'ALTER TABLE modules_studentclassregmoduleinfo ALTER COLUMN priority_limit SET STORAGE PLAIN',
'ALTER TABLE modules_studentclassregmoduleinfo ALTER COLUMN priority_limit SET DEFAULT 3',
]

print 'Updating modules_studentclassregmoduleinfo...'
[ cursor.execute( c ) for c in scrmi_update_sql ]
print '    OK'

print 'Committing changes to database...'
transaction.commit()
print '    OK'
transaction.leave_transaction_management()
print 'Done.'
