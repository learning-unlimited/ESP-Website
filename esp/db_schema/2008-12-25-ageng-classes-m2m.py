#!/usr/bin/python

""" Replace the ClassSubject <-> ClassSection ManyToMany with a One-to-Many. """

from django.db import transaction, connection

sqllist = [
    'ALTER TABLE program_classsection ADD COLUMN parent_class_id integer',
    'ALTER TABLE program_classsection ALTER COLUMN parent_class_id SET STORAGE PLAIN',
    """CREATE INDEX program_classsection_parent_class_id
        ON program_classsection USING btree (parent_class_id)""",
    """UPDATE program_classsection SET parent_class_id = l.classsubject_id
        FROM program_class_sections l
        WHERE program_classsection.id = l.classsection_id""",
    'ALTER TABLE program_classsection ALTER COLUMN parent_class_id SET NOT NULL',
    #'DROP TABLE program_class_sections',
    ]

cursor = connection.cursor()
transaction.enter_transaction_management()
print 'Updating program_classsection...'
for c in sqllist:
    cursor.execute( c )
print '    OK'
print 'Committing changes to the database...'
transaction.commit()
print '    OK'
transaction.leave_transaction_management()
print 'Done.'
