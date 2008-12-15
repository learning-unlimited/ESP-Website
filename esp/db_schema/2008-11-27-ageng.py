#!/usr/bin/python

""" Database schema update script for ClassCategories. """

from django.db import transaction, connection

cursor = connection.cursor()


classcategories_update_sql = [
'ALTER TABLE program_classcategories ADD COLUMN symbol character(1)',
'UPDATE program_classcategories SET symbol = CAST(category AS character(1))',
'ALTER TABLE program_classcategories ALTER COLUMN symbol SET STORAGE EXTENDED',
'ALTER TABLE program_classcategories ALTER COLUMN symbol SET NOT NULL',
"""CREATE TABLE program_program_class_categories
(
  id serial NOT NULL,
  program_id integer NOT NULL,
  classcategories_id integer NOT NULL,
  CONSTRAINT program_program_class_categories_pkey PRIMARY KEY (id)
)
WITH (OIDS=TRUE)""",
'ALTER TABLE program_program_class_categories OWNER TO esp',
]

[ cursor.execute( c ) for c in classcategories_update_sql ]

from esp.program.models import Program, ClassCategories

for p in Program.objects.all():
    for cat in ClassCategories.objects.all():
        p.class_categories.add( cat )

# Don't forget to create new categories!

