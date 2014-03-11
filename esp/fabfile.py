from fab_deploy import *
from fab_deploy.project import WebProject
from abc import ABCMeta, abstractmethod
from taskset import TaskSet, task_method
from fab_deploy.utils import update_env, define_host
from fab_deploy.django import Django
from fab_deploy.webserver.apache import Apache
from fab_deploy.webserver.nginx import Nginx
from fabric.operations import local,put
from fabric.api import *
from fabric.contrib import files

env.user='vmuser'
env.password = 'opensesame'#CHANGEME

class CustomWebProject(WebProject):
    @task_method
    def full_deploy(self):
        """ Prepares server and deploys the project. """
        os = utils.detect_os()
        system.prepare()
        self.install_web_servers()
        self.install_databases()
        self.deploy()

apps = dict(django=Django(Nginx(), Apache(wsgi='django_wsgi.py'), local_config='local_settings.py'))
CustomWebProject(apps=apps).expose_to_current_module()

COMMON_OPTIONS = dict(
        DB_BACKEND = 'postgres',
        DB_USER = 'esp_dbuser',
        DB_PASSWORD = 'password',#CHANGE ME
        DB_ROOT_PASSWORD = 'password',#CHANGE ME
        DB_NAME = 'esp_db',
        VCS = 'git',
        GIT_BRANCH = 'fabric-deployment',
        LOCAL_CONFIG = 'esp/local_settings.py',
        PIP_REQUIREMENTS_PATH = 'esp/requirements',
        APACHE_PORT = 50001,
        PROJECT_PATH = 'esp',
        SUDO_USER = 'price',
        INSTANCE_NAME = 'esp',

    )

@define_host('price@localhost', COMMON_OPTIONS)
def staging():
    return dict(
        DEBUG = True,
        CONFIG_TEMPLATES_PATHS = ['config_templates/dev',
                                  'config_templates'],
    )

@define_host('vmuser@localhost', COMMON_OPTIONS)
def production():
    return dict(
        DEBUG = False,
        CONFIG_TEMPLATES_PATHS = ['esp/config_templates/production',
                                  'esp/config_templates'],
    )


staging()
# production()
