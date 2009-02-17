#!/usr/bin/python

""" Adding the field 'how did you hear about ESP?' to the student profiles """

from django.db import transaction, connection

cursor = connection.cursor()
transaction.enter_transaction_management()
print 'Updating users_studentinfo...'
cursor.execute( 'ALTER TABLE users_studentinfo ADD COLUMN heardofesp text;' )
print '    OK'
print 'Committing changes to the database...'
transaction.commit()
print '    OK'
transaction.leave_transaction_management()
print 'Done.'
