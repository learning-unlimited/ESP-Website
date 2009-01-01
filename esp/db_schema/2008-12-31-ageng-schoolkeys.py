#!/usr/bin/python

""" Add "k12school" as a foreign key to StudentInfo and EducatorInfo. """

from django.db import transaction, connection

sqllist = [
    'ALTER TABLE users_studentinfo ADD COLUMN k12school_id integer',
    'ALTER TABLE users_studentinfo ALTER COLUMN k12school_id SET STORAGE PLAIN',
    """CREATE INDEX users_studentinfo_k12school_id
        ON users_studentinfo USING btree (k12school_id)""",
    'ALTER TABLE users_educatorinfo ADD COLUMN k12school_id integer',
    'ALTER TABLE users_educatorinfo ALTER COLUMN k12school_id SET STORAGE PLAIN',
    """CREATE INDEX users_educatorinfo_k12school_id
        ON users_educatorinfo USING btree (k12school_id)""",
    ]

cursor = connection.cursor()
transaction.enter_transaction_management()
print 'Updating users_studentinfo and users_educatorinfo...'
for c in sqllist:
    cursor.execute( c )
print '    OK'
print 'Committing changes to the database...'
transaction.commit()
print '    OK'
transaction.leave_transaction_management()
print 'Done.'
