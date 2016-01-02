from django.core.management.color import color_style, no_style
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models.loading import get_apps
from django.db import connection
from django.core.management.sql import sql_indexes

import logging
logger = logging.getLogger(__name__)
import re
from optparse import make_option

index_re = re.compile('CREATE INDEX \"(.*?)\" ON \"(.*?)\" \(\"(.*?)\"\);')
#'CREATE INDEX "django_admin_log_user_id" ON "django_admin_log" ("user_id");'

#Gets you the current tables in Postgres
CURRENT_INDEX_SQL = """
SELECT c.relname as "Name",
 c2.relname as "Table"
FROM pg_catalog.pg_class c
     JOIN pg_catalog.pg_roles r ON r.oid = c.relowner
     LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     LEFT JOIN pg_catalog.pg_index i ON i.indexrelid = c.oid
     LEFT JOIN pg_catalog.pg_class c2 ON i.indrelid = c2.oid
WHERE c.relkind IN ('i','')
  AND n.nspname <> 'pg_catalog'
  AND n.nspname !~ '^pg_toast'
  AND pg_catalog.pg_table_is_visible(c.oid)
ORDER BY 1,2;
"""

class Command(BaseCommand):
    help = "Find the missing indexes in the database that Django thinks we should have."
    output_transaction = True
    option_list = BaseCommand.option_list + (
        make_option('--show', dest='show', default=False,
                    action="store_true", help='Show Changes'),
    )

    def handle(self, *args, **options):
        all_indexes = []
        proposed_indexes = {}
        index_sql = {}
        for app in get_apps():
            all_indexes.append(u'\n'.join(sql_indexes(app,
                                                      no_style(),
                                                      connection)).encode('utf-8'))
        #Sort out all the proposed indexes by table.
        for index in all_indexes:
            indice = index.split('\n')
            for ind in indice:
                try:
                    match = index_re.search(ind)
                    name, table, field = match.groups()
                    if table in proposed_indexes:
                        proposed_indexes[table].append(name)
                    else:
                        proposed_indexes[table] = [name]
                    if name in index_sql:
                        index_sql[name].append(ind)
                    else:
                        index_sql[name] = [ind]
                except:
                    pass

        #Now get all the real indexes.
        indexes = {}
        cursor = connection.cursor()
        vals = cursor.execute(CURRENT_INDEX_SQL)
        sql_back = cursor.fetchall()
        for row in sql_back:
            name, table = row
            if table in indexes:
                indexes[table].append(name)
            else:
                indexes[table] = [name]

        #For all the proposed indexes, see if they exist
        #If not, tell us!
        for prop_name, prop_tables in proposed_indexes.items():
            for table in prop_tables:
                try:
                    if not table in indexes[prop_name]:
                        if not options['show']:
                            logger.info("(%s, %s) is missing", prop_name, table)
                        else:
                            for index in index_sql[table]:
                                if prop_name in index:
                                    logger.info(index)
                except KeyError:
                    if not options['show']:
                        logger.info("No Indexes for %s in original db", prop_name)
                    else:
                        for index in index_sql[table]:
                            if table in index:
                                logger.info(index)

