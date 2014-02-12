# coding: utf-8
from __future__ import absolute_import

from fabric.context_managers import settings, hide
from fabric.operations import sudo
from taskset import task_method

from fab_deploy.db.postgres import Postgres
from fab_deploy import utils
from fab_deploy import system

# The script is from django:
# https://docs.djangoproject.com/en/1.4/_downloads/create_template_postgis-debian.sh
_SCRIPT = """
GEOGRAPHY=0
POSTGIS_SQL=postgis.sql

# For Ubuntu 8.x and 9.x releases.
if [ -d "/usr/share/postgresql-8.3-postgis" ]
then
    POSTGIS_SQL_PATH=/usr/share/postgresql-8.3-postgis
    POSTGIS_SQL=lwpostgis.sql
fi

# For Ubuntu 10.04
if [ -d "/usr/share/postgresql/8.4/contrib" ]
then
    POSTGIS_SQL_PATH=/usr/share/postgresql/8.4/contrib
fi

# For Ubuntu 10.10 (with PostGIS 1.5)
if [ -d "/usr/share/postgresql/8.4/contrib/postgis-1.5" ]
then
    POSTGIS_SQL_PATH=/usr/share/postgresql/8.4/contrib/postgis-1.5
    GEOGRAPHY=1
fi

# For Ubuntu 11.10 / Linux Mint 12 (with PostGIS 1.5)
if [ -d "/usr/share/postgresql/9.1/contrib/postgis-1.5" ]
then
    POSTGIS_SQL_PATH=/usr/share/postgresql/9.1/contrib/postgis-1.5
    GEOGRAPHY=1
fi

createdb -E UTF8 template_postgis && \
( createlang -d template_postgis -l | grep plpgsql || createlang -d template_postgis plpgsql ) && \
psql -d postgres -c "UPDATE pg_database SET datistemplate='true' WHERE datname='template_postgis';" && \
psql -d template_postgis -f $POSTGIS_SQL_PATH/$POSTGIS_SQL && \
psql -d template_postgis -f $POSTGIS_SQL_PATH/spatial_ref_sys.sql && \
psql -d template_postgis -c "GRANT ALL ON geometry_columns TO PUBLIC;" && \
psql -d template_postgis -c "GRANT ALL ON spatial_ref_sys TO PUBLIC;"

if ((GEOGRAPHY))
then
    psql -d template_postgis -c "GRANT ALL ON geography_columns TO PUBLIC;"
fi
"""

class PostGis(Postgres):

    POSTGIS_TEMPLATE_SCRIPT = _SCRIPT

    @task_method
    @utils.run_as_sudo
    def install(self):
        """ Installs PostgreSQL + postgis. """
        packages = 'gdal-bin postgresql-8.4-postgis postgresql-server-dev-8.4'
        system.aptitude_install(packages)

    @utils.run_as_sudo
    @utils.inside_src
    def create_postgis_template(self):
        """ Installs postgis database template """
        with settings(hide('stdout')):
            sudo(self.POSTGIS_TEMPLATE_SCRIPT, user=self.SUPERUSER)

    @task_method
    def create_db(self, db_name=None, db_user=None, root_password=None, template=None):
        """ Creates empty PostGIS-enabled database """
        if template is None:
            with settings(warn_only=True):
                self.create_postgis_template()
            template = 'template_postgis'
        return super(PostGis, self).create_db(db_name, db_user, root_password, template)


instance = PostGis()
__all__ = instance.expose_to_current_module()