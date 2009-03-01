#!/usr/bin/python

"""
Database schema update script for TeacherInfo.
Chicago wants more info about its teachers, for reimbursements.
"""

from django.db import connection, transaction

transaction.enter_transaction_management()

cursor = connection.cursor()

teacherinfo_update_sql = [
'ALTER TABLE users_teacherinfo ADD COLUMN full_legal_name character varying(128)',
'ALTER TABLE users_teacherinfo ALTER COLUMN full_legal_name SET STORAGE EXTENDED',
'ALTER TABLE users_teacherinfo ADD COLUMN university_email character varying(75)',
'ALTER TABLE users_teacherinfo ALTER COLUMN university_email SET STORAGE EXTENDED',
'ALTER TABLE users_teacherinfo ADD COLUMN student_id character varying(128)',
'ALTER TABLE users_teacherinfo ALTER COLUMN student_id SET STORAGE EXTENDED',
'ALTER TABLE users_teacherinfo ADD COLUMN mail_reimbursement boolean',
'ALTER TABLE users_teacherinfo ALTER COLUMN mail_reimbursement SET STORAGE PLAIN',
]

print 'Updating users_teacherinfo...'
[ cursor.execute( c ) for c in teacherinfo_update_sql ]
print '    OK'

print 'Committing changes to database...'
transaction.commit()
print '    OK'
transaction.leave_transaction_management()
print 'Done.'
