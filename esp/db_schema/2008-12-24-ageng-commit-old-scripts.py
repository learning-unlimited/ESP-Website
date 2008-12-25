#!/usr/bin/python

""" Database schema update script to fix ClassSubject durations. """


from __future__ import with_statement
from django.db import transaction

transaction.enter_transaction_management()

print 'Updating program_class.duration...'
with open('../db_schema/2008-12-13-ageng.py', 'r') as f:
	exec f
print '    OK'

print 'Updating director_email fields to varchar(75)...'
with open('../db_schema/2008-12-14-ageng.py', 'r') as f:
	exec f
print '    OK'

print 'Committing changes to database...'
transaction.commit()
print '    OK'
transaction.leave_transaction_management()
print 'Done.'
