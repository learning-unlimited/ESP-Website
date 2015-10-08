
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

""" 
This is a hack job of a test runner, intended for verifying that the code works against
an existing database that may have interesting configuration and data history in it.
This is important because Tags and TemplateOverrides affect the performance and
behavior of each site, and the default test suite may not catch them since it runs against
a "clean" database.

The code you see below is mostly copied from Django's default test runner; the only
modification was to create the database using the PostgreSQL command:
    CREATE DATABASE test_foo WITH TEMPLATE foo;
to copy foo (the production database) into test_foo (the test database, which will be
destroyed).  The syncdb and migrate commands are not run, though maybe this should
be added as an option.

To use, set TEST_RUNNER = 'esp.utils.testing.InPlaceTestSuiteRunner' in local_settings.py.

This code is under development.  Status history:
-   7/10/2011: Initial commit, code can be used to run test suite, but results in lots of
    test errors.  Need to figure out which are due to bugs and which are due to pre-existing
    data.
"""

from django.conf import settings
from django.test.simple import DjangoTestSuiteRunner, build_suite, build_test
from django.test.runner import dependency_ordered, reorder_suite
from django.db import connections
from django.db.utils import ConnectionHandler
from django.db.backends.creation import BaseDatabaseCreation
from django.utils import unittest
from django.test.testcases import TestCase
from django.db.models import get_app, get_apps
import sys

EXCLUDED_APPS = getattr(settings, 'TEST_EXCLUDE', [])

class ExcludeTestSuiteRunner(DjangoTestSuiteRunner):
    """Test runner to exclude apps from general testing."""
    def build_suite(self, *args, **kwargs):
        suite = super(ExcludeTestSuiteRunner, self).build_suite(*args, **kwargs)
        if not args[0]:
            tests = []
            for case in suite:
                pkg = case.__class__.__module__.split('.')[0]
                if pkg not in EXCLUDED_APPS:
                    tests.append(case)
            suite._tests = tests 
        return suite

class InPlaceTestSuiteRunner(DjangoTestSuiteRunner, BaseDatabaseCreation):

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        suite = unittest.TestSuite()

        if test_labels:
            print test_labels
            for label in test_labels:
                print label
                if '.' in label:
                    suite.addTest(build_test(label))
                else:
                    app = get_app(label)
                    suite.addTest(build_suite(app))
        else:
            print 'Filtering applications to test...'
            for app in get_apps():
                if isinstance(app.__package__, basestring) and app.__package__.startswith('esp.'):
                    print '  Adding: %s' % app.__package__
                    suite.addTest(build_suite(app))
                else:
                    print '  Skipping: %s' % app.__package__

        if extra_tests:
            for test in extra_tests:
                suite.addTest(test)

        return reorder_suite(suite, (TestCase,))

    def _create_test_db(self, verbosity, autoclobber):
        "Internal implementation - creates the test db tables."
        suffix = self.sql_table_creation_suffix()

        orig_database_name = self.connection.settings_dict['NAME']
        test_database_name = self._get_test_db_name()

        qn = self.connection.ops.quote_name

        # Create the test database and connect to it. We need to autocommit
        # if the database supports it because PostgreSQL doesn't allow
        # CREATE/DROP DATABASE statements within transactions.
        cursor = self.connection.cursor()
        self.set_autocommit()
        try:
            cursor.execute("CREATE DATABASE %s WITH TEMPLATE %s %s" % (qn(test_database_name), orig_database_name, suffix))
        except Exception, e:
            sys.stderr.write("Got an error creating the test database: %s\n" % e)
            if not autoclobber:
                confirm = raw_input("Type 'yes' if you would like to try deleting the test database '%s', or 'no' to cancel: " % test_database_name)
            if autoclobber or confirm == 'yes':
                try:
                    if verbosity >= 1:
                        print "Destroying old test database '%s'..." % self.connection.alias
                    cursor.execute("DROP DATABASE %s" % qn(test_database_name))
                    cursor.execute("CREATE DATABASE %s WITH TEMPLATE %s %s" % (qn(test_database_name), orig_database_name, suffix))
                except Exception, e:
                    sys.stderr.write("Got an error recreating the test database: %s\n" % e)
                    sys.exit(2)
            else:
                print "Tests cancelled."
                sys.exit(1)

        return test_database_name

    def create_test_db(self, verbosity=1, autoclobber=False):
        """
        Creates a test database, prompting the user for confirmation if the
        database already exists. Returns the name of the test database created.
        
        Modified to use template of existing database.
        """

        test_database_name = self._get_test_db_name()

        if verbosity >= 1:
            test_db_repr = ''
            if verbosity >= 2:
                test_db_repr = " ('%s')" % test_database_name
            print "Creating test database for alias '%s'%s..." % (self.connection.alias, test_db_repr)

        self._create_test_db(verbosity, autoclobber)

        self.connection.close()
        self.connection.settings_dict["NAME"] = test_database_name

        # Confirm the feature set of the test database
        self.connection.features.confirm()

        # Get a cursor (even though we don't need one yet). This has
        # the side effect of initializing the test database.
        cursor = self.connection.cursor()

        return test_database_name


    def setup_databases(self, **kwargs):
        from django.db import connections, DEFAULT_DB_ALIAS

        # First pass -- work out which databases actually need to be created,
        # and which ones are test mirrors or duplicate entries in DATABASES
        mirrored_aliases = {}
        test_databases = {}
        dependencies = {}
        for alias in connections:
            connection = connections[alias]
            if connection.settings_dict['TEST_MIRROR']:
                # If the database is marked as a test mirror, save
                # the alias.
                mirrored_aliases[alias] = connection.settings_dict['TEST_MIRROR']
            else:
                # Store a tuple with DB parameters that uniquely identify it.
                # If we have two aliases with the same values for that tuple,
                # we only need to create the test database once.
                item = test_databases.setdefault(
                    connection.creation.test_db_signature(),
                    (connection.settings_dict['NAME'], [])
                )
                item[1].append(alias)

                if 'TEST_DEPENDENCIES' in connection.settings_dict:
                    dependencies[alias] = connection.settings_dict['TEST_DEPENDENCIES']
                else:
                    if alias != DEFAULT_DB_ALIAS:
                        dependencies[alias] = connection.settings_dict.get('TEST_DEPENDENCIES', [DEFAULT_DB_ALIAS])

        # Second pass -- actually create the databases.
        old_names = []
        mirrors = []
        for signature, (db_name, aliases) in dependency_ordered(test_databases.items(), dependencies):
            # Actually create the database for the first connection
            self.connection = connections[aliases[0]]
            old_names.append((self.connection, db_name, True))
            
            """ Mod by Michael Price - use original database as template when creating new one """
            #   test_db_name = connection.creation.create_test_db(self.verbosity, autoclobber=not self.interactive)
            test_db_name = self.create_test_db(self.verbosity, autoclobber=not self.interactive)
            
        for alias, mirror_alias in mirrored_aliases.items():
            mirrors.append((alias, connections[alias].settings_dict['NAME']))
            connections[alias].settings_dict['NAME'] = connections[mirror_alias].settings_dict['NAME']

        return old_names, mirrors
