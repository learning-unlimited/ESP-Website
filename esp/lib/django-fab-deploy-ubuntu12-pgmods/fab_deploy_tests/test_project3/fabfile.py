from fab_deploy.utils import define_host
from fab_deploy.webserver.apache import Apache
from fab_deploy.webserver.nginx import Nginx
from fab_deploy.django import Django
from fab_deploy.project import WebProject

COMMON = dict(
    CONFIG_TEMPLATES_PATHS=['test_project3/config_templates'],
    PIP_REQUIREMENTS_PATH = 'test_project3/reqs/',

    DB_USER = 'baz',
    DB_PASSWORD = '123',
    VCS = 'none',
    SERVER_NAME = 'baz.example.com'
)

apps = dict(
    django=Django(
        Nginx(config='nginx.config'), 
        Apache(config='apache.config', wsgi='django_wsgi.py'),
        local_config='test_project3/config.py',
        remote_config='test_project3/config.server.py'
    )
)
project = WebProject(apps=apps).expose_as_module('project')

@define_host('baz@127.0.0.1:2222', COMMON)
def postgres_site():
    return dict(
        DB_BACKEND = 'postgres',
        DJANGO_DB_ENGINE = 'django.db.backends.postgresql_psycopg2',
    )


@define_host('baz@127.0.0.1:2222', COMMON)
def postgis_site():
    return dict(
        DB_BACKEND = 'postgis',
        DJANGO_DB_ENGINE = 'django.contrib.gis.db.backends.postgis',
    )

