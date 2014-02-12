from __future__ import absolute_import
import os
from urllib2 import HTTPError
import mock
import contextlib
from fabric.api import hide, run, env, settings
from fabtest import fab, vbox_urlopen, FabricAbortException
from fab_deploy.utils import run_as
from fab_deploy.db import mysql, postgres, postgis
from fab_deploy.webserver.apache import Apache
from .base import FabDeployTest
from ..utils import setup_ssh, setup_sudo
from ..test_project.fabfile import foo_site, bar_site, invalid_site, project
from ..test_project2.fabfile import foo_site as foo_site2, project as project2
from ..test_project3.fabfile import postgis_site, postgres_site, project as project3

@contextlib.contextmanager
def answer_yes():
    with mock.patch('fabric.contrib.console.confirm') as confirm:
        confirm.return_value = True # answer 'YES' for all questions
        yield


def get_file_content(remote_file):
    @run_as('root')
    def cat():
        with(hide('stdout')):
            return run('cat '+remote_file)
    return fab(cat)

def get_ports():
    @run_as('root')
    def ports():
        return run('netstat -A inet -lnp')
    return fab(ports)

def is_local_port_bound(port):
    port_string = '127.0.0.1:%s' % port
    ports = get_ports()
    return port_string in ports

class FabDeployProjectTest(FabDeployTest):
    snapshot = 'fabtest-prepared-server'
    project_dir = 'test_project'
    project = project

    def assertResponse(self, url, response, post_data = None):
        try:
            resp = vbox_urlopen(url, post_data).read()
            self.assertEqual(resp, response)
        except HTTPError, e:
            raise AssertionError(e.read())

    def assertHttpError(self, url):
        # FIXME: this should only catch BadStatusLine and urllib2.HttpError
        self.assertRaises(Exception, vbox_urlopen, url)

    def assertNoFile(self, path):
        with(settings(warn_only=True)):
            res = get_file_content(path)
        self.assertFalse(res.succeeded)

    def assertFileExists(self, path):
        with(settings(warn_only=True)):
            res = get_file_content(path)
        self.assertTrue(res.succeeded)

    def assertCommandAvailable(self, command):
        result = fab(self.project.apps.django.command_is_available, command)
        self.assertTrue(result)

    def assertCommandNotAvailable(self, command):
        result = fab(self.project.apps.django.command_is_available, command)
        self.assertFalse(result)

    def assertCommandFails(self, command):
        self.assertRaises(FabricAbortException, fab,
                          self.project.apps.django.command_is_available, command)

    def assertInstanceWorks(self, instance):
        url = 'http://%s.example.com/instance/' % instance
        self.assertResponse(url, instance)

    def assertInstanceDoesntWork(self, instance):
        url = 'http://%s.example.com/instance/' % instance
        self.assertHttpError(url)

    def setup_conf(self):
        self.cwd = os.getcwd()
        os.chdir(self.project_dir)
        fab(foo_site)

    def tearDown(self):
        os.chdir(self.cwd)
        super(FabDeployProjectTest, self).tearDown()


class ApacheSetupTest(FabDeployProjectTest):

    def assertPortBound(self, port):
        self.assertTrue(is_local_port_bound(port))

    def assertPortNotBound(self, port):
        self.assertFalse(is_local_port_bound(port))

    def test_apache_config(self):
        apacheNoConfig = Apache()
        fab(apacheNoConfig.install, confirm=False)

        # first site
        fab(foo_site)
        fab(self.project.apps.django.backend.upload_config)

        foo_port = env.conf.PORTS['apache']
        self.assertPortNotBound(foo_port)
        self.assertFileExists('/etc/apache2/sites-enabled/foo_apache.config')

        fab(apacheNoConfig.restart)
        self.assertPortBound(foo_port)

        # second site
        fab(bar_site)
        fab(self.project.apps.django.backend.upload_config)

        bar_port = env.conf.PORTS['apache']
        self.assertNotEqual(foo_port, bar_port)
        self.assertPortNotBound(bar_port)

        fab(apacheNoConfig.restart)
        self.assertPortBound(bar_port)

        # re-configuring doesn't lead to errors
        fab(self.project.apps.django.backend.upload_config)
        fab(apacheNoConfig.restart)
        self.assertPortBound(bar_port)

    def test_apache_make_wsgi(self):
        self.assertNoFile(env.conf.ENV_DIR+'/var/wsgi/foo/django_wsgi.py')
        fab(Apache(wsgi='django_wsgi.py').upload_wsgi)
        self.assertFileExists(env.conf.ENV_DIR+'/var/wsgi/foo/django_wsgi.py')


class DeployTest(FabDeployProjectTest):

    def test_deploy(self):
        # FIXME! This fails because of __getattribute__ at apps module.
        # And env.conf.APPS is not initialised at all for this moment.
        #self.assertCommandFails('syncdb')

        # deploy first site
        fab(foo_site)
        with answer_yes():
            fab(self.project.deploy)

        self.assertCommandAvailable('syncdb')
        self.assertCommandNotAvailable('syncddb')

        self.assertInstanceWorks('foo')

        # deploy second site
        fab(bar_site)

        with answer_yes():
            fab(self.project.deploy)

        self.assertInstanceWorks('bar')
        self.assertInstanceWorks('foo')

        # deploy improperly configured site
        fab(invalid_site)

        # config errors should not be silenced
        with answer_yes():
            self.assertRaises(FabricAbortException, fab, project.deploy)

        # old sites still work
        self.assertInstanceWorks('bar')
        self.assertInstanceWorks('foo')
        self.assertInstanceDoesntWork('invalid')


class CustomLayoutDeployTest(FabDeployProjectTest):
    project_dir = 'test_project2'
    project = project2

    def setUp(self):
        super(CustomLayoutDeployTest, self).setUp()

    def test_deploy(self):
        url = 'http://foo.example.com/instance/'
        fab(foo_site2)

        setup_sudo()
        setup_ssh()

        fab(mysql.create_db)

        with answer_yes():
            fab(self.project.deploy)

        self.assertResponse(url, 'foo2')

        # just check that blank push doesn't break anything
        # TODO: proper push tests
        fab(self.project.push, 'update_r', 'syncdb')
        self.assertResponse(url, 'foo2')

        # check that remove disables the site
        # TODO: more undeploy tests
        fab(self.project.remove, confirm=False)
        self.assertHttpError(url)

        # deploying project again should be possible
        fab(self.project.deploy)
        self.assertResponse(url, 'foo2')

    def test_push_callback(self):

        def before_restart():
            before_restart.called = True
        before_restart.called = False

        def my_push(*args):
            return self.project.push(*args, before_restart=before_restart)

        fab(foo_site2)

        setup_sudo()
        setup_ssh()

        fab(mysql.create_db)

        with answer_yes():
            fab(self.project.deploy)

        fab(my_push)
        self.assertTrue(before_restart.called)


class Django14LayoutDeployTest(FabDeployProjectTest):
    project_dir = 'test_project3'
    project = project3

    def post_name(self, name):
        url = 'http://baz.example.com/app/create/%s/' % name
        resp = vbox_urlopen(url, "").read()
        return resp

    def get_names(self):
        url = 'http://baz.example.com/app/get/'
        resp = vbox_urlopen(url).read()
        return resp.splitlines()

    def _check_deploy(self, db_backend):
        self.assertInstanceDoesntWork('baz')

        setup_sudo()
        setup_ssh()

        fab(db_backend.install)

        self.assertTrue(fab(db_backend.is_installed))
        fab(db_backend.install) # this shouldn't fail

        fab(db_backend.create_user)
        fab(db_backend.create_db)

        with answer_yes():
            fab(self.project.deploy)

        res = fab(db_backend.execute_sql, "select * from auth_user;")
        assert 'is_active' in res

        self.assertInstanceWorks('baz')

        self.post_name('vasia')
        self.assertEqual(self.get_names(), ['vasia'])


    def test_deploy_postgres(self):
        fab(postgres_site)
        self._check_deploy(postgres)

    def test_deploy_postgis(self):
        fab(postgis_site)
        self._check_deploy(postgis)

        url = 'http://baz.example.com/geo/distance/'
        self.assertResponse(url, '3417')
