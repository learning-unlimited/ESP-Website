#!/usr/bin/python

""" Drop the dead column program_programmodule.check_call. """

from django.db import transaction, connection

cursor = connection.cursor()
transaction.enter_transaction_management()
print 'Updating program_programmodule...'
cursor.execute( 'ALTER TABLE program_programmodule DROP COLUMN check_call' )
print '    OK'
print 'Committing changes to the database...'
transaction.commit()
print '    OK'
transaction.leave_transaction_management()
print 'Done.'
