"""
Test cases for Django-ESP utilities
"""

from __future__ import with_statement

import datetime
import doctest
try:
    import pylibmc as memcache
except:
    import memcache
import logging
logger = logging.getLogger(__name__)
import os
import subprocess
import sys
from reversion import revisions as reversion
import unittest

from django.db.models.query import Q
from django.template import loader, Template, Context, TemplateDoesNotExist
from django.test import TestCase as DjangoTestCase

from esp.middleware import ESPError_Log
from esp.users.models import ESPUser
from esp import utils
from esp.utils import query_builder
from esp.utils.models import TemplateOverride, Printer, PrintRequest


# Code from <http://snippets.dzone.com/posts/show/6313>
# My understanding is that snippets from this site are public domain,
# though I've had trouble finding documentation to clarify this.
def find_executable(executable, path=None):
    """Try to find 'executable' in the directories listed in 'path' (a
    string listing directories separated by 'os.pathsep'; defaults to
    os.environ['PATH']).  Returns the complete filename or None if not
    found
    """
    if path is None:
        path = os.environ['PATH']
    paths = path.split(os.pathsep)
    extlist = ['']
    if os.name == 'os2':
        (base, ext) = os.path.splitext(executable)
        # executable files on OS/2 can have an arbitrary extension, but
        # .exe is automatically appended if no dot is present in the name
        if not ext:
            executable = executable + ".exe"
    elif sys.platform == 'win32':
        pathext = os.environ['PATHEXT'].lower().split(os.pathsep)
        (base, ext) = os.path.splitext(executable)
        if ext.lower() not in pathext:
            extlist = pathext
    for ext in extlist:
        execname = executable + ext
        if os.path.isfile(execname):
            return execname
        else:
            for p in paths:
                f = os.path.join(p, execname)
                if os.path.isfile(f):
                    return f
    else:
        return None

class DependenciesTestCase(unittest.TestCase):
    def tryImport(self, mod):
        try:
            foo = __import__(mod)
        except Exception, e:
            logger.info("Error importing required module '%s': %s", mod, e)
            self._failed_import = True

    def tryExecutable(self, exe):
        if not find_executable(exe):
            logger.info("Executable not found:  '%s'", exe)
            self._exe_not_found = True

    def testDeps(self):
        self._failed_import = False
        self._exe_not_found = False

        self.tryImport("django")  # If this fails, we lose.
        self.tryImport("PIL")  # Needed for Django Image fields, which we use for (among other things) teacher bio's
        self.tryImport("PIL._imaging")  # Internal PIL module; PIL will import without it, but it won't have a lot of the functionality that we need
        self.tryImport("pylibmc")  # We currently depend specifically on the "pylibmc" Python<->memcached interface library.
        self.tryImport("DNS")  # Used for validating email address hostnames.  Imports as DNS, but the package and egg are named "pydns".
        self.tryImport("json")  # Used for some of our AJAX magic
        self.tryImport("psycopg2")  # Used for talking with PostgreSQL.  Someday, we'll support psycopg2, but not today...
        self.tryImport("xlwt")  # Used in our giant statistics spreadsheet-generating code
        self.tryImport("form_utils")     #Used to create better forms.
        self.assert_(not self._failed_import)

        # Make sure that we're actually using pylibmc.
        # Note that this requires a patch to Django (or Django version 1.3 or later).
        # Patch can be found at:  <http://code.djangoproject.com/ticket/11675>
        from pylibmc import Client
        from django.core.cache import cache
        if hasattr(cache, "_cache"):
            self.assert_(isinstance(cache._cache, Client))
        elif hasattr(cache, "_wrapped_cache") and hasattr(cache._wrapped_cache, "_cache"):
            self.assert_(isinstance(cache._wrapped_cache._cache, Client))

        self.tryExecutable("latex")  # Used for a whole pile of program printables, as well as inline LaTeX
        self.tryExecutable("dvips")  # Used to convert LaTeX output (.dvi) to .ps files
        self.tryExecutable("convert")  # Used in the generation of inline LaTeX chunks.  Also for some cases of generating .png images from LaTeX output; the student-schedule generator currently does dvips then convert to get .png's so that barcodes work
        self.tryExecutable("dvipng")  # Used to convert LaTeX output (.dvi) to .png files
        self.tryExecutable("ps2pdf")  # Used to convert LaTeX output (.dvi) to .pdf files (must go to .ps first because we use some LaTeX packages that depend on Postscript)
        self.tryExecutable("inkscape")  # Used to render LaTeX output (once converted to .pdf) to .svg image files

        self.assert_(not self._exe_not_found)

class MemcachedTestCase(unittest.TestCase):
    """
    Test-case implementation that starts and manages a few memcached processes
    to be used by test functions.
    Note that this is not itself a collection of test cases,
    it's meant to be subclassed as needed.
    """

    CACHES = [ "127.0.0.1:11218" ]

    def setUp(self):
        """ Launch memcached instances for all the caches listed in CACHES """
        caches = [ x.split(':') for x in self.CACHES ]
        self.servers = [ subprocess.Popen(["memcached", '-u', 'nobody', '-p', '%s' % cache[1]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                         for cache in caches ]
        self.clients = [ memcache.Client([cache]) for cache in self.CACHES ]

    def tearDown(self):
        """ Terminate all the server processes that we launched with setUp() """
        for client in self.clients:
            client.disconnect_all()

        if len(self.servers) > 0 and hasattr(self.servers[0], 'terminate'):  # You can't terminate processes prior to Python 2.6, they (hopefully) get killed off on their own when the test run finishes
            for server in self.servers:
                server.terminate()  # Sends SIGTERM, telling the servers to terminate
            for server in self.servers:
                server.wait()       # After we've told all the servers to terminate, wait for them to all actually stop.


class MemcachedKeyLengthTestCase(DjangoTestCase):
    """ Grab a ridiculous URL and make sure the status code isn't 500. """
    def runTest(self):
        response = self.client.get('/l' + 'o'*256 + 'ngurl.html')
        self.assertTrue(response.status_code != 500, 'Ridiculous URL not handled gracefully.')


class TemplateOverrideTest(DjangoTestCase):
    def get_response_for_template(self, template_name):
        template = loader.get_template(template_name)
        return template.render({})

    def expect_template_error(self, template_name):
        template_error = False
        try:
            self.get_response_for_template(template_name)
        except TemplateDoesNotExist:
            template_error = True
        except:
            logger.info('Unexpected error fetching nonexistent template')
            raise
        self.assertTrue(template_error)

    def test_overrides(self):
        #   Try to render a page from a nonexistent template override
        #   and make sure it doesn't exist
        self.expect_template_error('BLAARG.NOTANACTUALTEMPLATE')

        #   Create a template override and make sure you can see it
        with reversion.create_revision():
            to = TemplateOverride(name='BLAARG.TEMPLATEOVERRIDE', content='Hello')
            to.save()
        self.assertTrue(self.get_response_for_template('BLAARG.TEMPLATEOVERRIDE') == 'Hello')

        #   Save an update to the template override and make sure you see that too
        with reversion.create_revision():
            to.content = 'Goodbye'
            to.save()
        self.assertTrue(self.get_response_for_template('BLAARG.TEMPLATEOVERRIDE') == 'Goodbye')

        #   Revert the update to the template and make sure you see the old version
        list(reversion.get_for_object(to).get_unique())[1].revert()
        self.assertTrue(self.get_response_for_template('BLAARG.TEMPLATEOVERRIDE') == 'Hello')

        #   Delete the original template override and make sure you see nothing
        TemplateOverride.objects.filter(name='BLAARG.TEMPLATEOVERRIDE').delete()
        self.expect_template_error('BLAARG.TEMPLATEOVERRIDE')


class QueryBuilderTest(DjangoTestCase):
    maxDiff = None
    def test_query_builder(self):
        # Use Printer/PrintRequest to test, since they're simple and in the
        # same app.

        # Clean out any printers from other tests, and create our own.
        Printer.objects.all().delete()
        self.assertEqual(Printer.objects.count(), 0)
        happy_printer = Printer.objects.create(name="Happy")
        slow_printer = Printer.objects.create(name="Sad")
        sad_printer = Printer.objects.create(name="Slow")
        nice_user = ESPUser.objects.create(username="nice_user")
        mean_user = ESPUser.objects.create(username="mean_user")
        now = datetime.datetime.now()
        PrintRequest.objects.create(printer=happy_printer, user=nice_user,
                                    time_executed=now)
        PrintRequest.objects.create(printer=happy_printer, user=nice_user,
                                    time_executed=now)
        PrintRequest.objects.create(printer=happy_printer, user=nice_user,
                                    time_executed=now)
        PrintRequest.objects.create(printer=sad_printer, user=mean_user)
        PrintRequest.objects.create(printer=sad_printer, user=mean_user)
        PrintRequest.objects.create(printer=slow_printer, user=nice_user,
                                    time_executed=now)
        PrintRequest.objects.create(printer=slow_printer, user=mean_user)
        PrintRequest.objects.create(printer=slow_printer, user=mean_user)
        PrintRequest.objects.create(printer=slow_printer, user=mean_user)
        PrintRequest.objects.create(printer=slow_printer, user=mean_user)
        PrintRequest.objects.create(printer=slow_printer, user=mean_user)
        PrintRequest.objects.create(printer=slow_printer, user=mean_user)

        name_filter = query_builder.SearchFilter(
            'named', 'named', [query_builder.TextInput('name')])
        has_ever_printed_filter = query_builder.SearchFilter(
            'has ever printed', 'has ever printed',
            [query_builder.ConstantInput(
                Q(printrequest__time_executed__isnull=False))])
        always_works_filter = query_builder.SearchFilter(
            'always works', 'always works',
            [query_builder.ConstantInput(
                Q(printrequest__time_executed__isnull=True))],
            inverted=True)
        print_query_builder = query_builder.QueryBuilder(
            Printer.objects.all(),
            [name_filter, has_ever_printed_filter, always_works_filter])

        self.assertEqual(
            print_query_builder.spec(), {
                'englishName': 'printers',
                'filterNames': ['named', 'has ever printed', 'always works'],
                'filters': {
                    'named': name_filter.spec(),
                    'has ever printed': has_ever_printed_filter.spec(),
                    'always works': always_works_filter.spec()
                }})
        self.assertEqual(
            # printers named Happy
            print_query_builder.as_queryset(
                {'filter': 'named', 'negated': False, 'values': ['Happy']}
            ).get(),
            happy_printer)
        self.assertEqual(
            # printers not named Happy
            print_query_builder.as_queryset(
                {'filter': 'named', 'negated': True, 'values': ['Happy']}
            ).distinct().count(),
            2)
        self.assertEqual(
            # printers that have never printed
            print_query_builder.as_queryset(
                {'filter': 'has ever printed', 'negated': True,
                 'values': [None]}
            ).get(),
            sad_printer)
        self.assertEqual(
            # printers that always work
            print_query_builder.as_queryset(
                {'filter': 'always works', 'negated': False, 'values': [None]}
            ).get(),
            happy_printer)
        self.assertEqual(
            # printers named Happy that have never printed
            print_query_builder.as_queryset(
                {'filter': 'and', 'negated': False, 'values': [
                    {'filter': 'has ever printed', 'negated': True,
                     'values': [None]},
                    {'filter': 'named', 'negated': False, 'values': ['Happy']}
                ]}
            ).distinct().count(),
            0)
        self.assertEqual(
            # printers that are not (named Happy and have never printed)
            print_query_builder.as_queryset(
                {'filter': 'and', 'negated': True, 'values': [
                    {'filter': 'has ever printed', 'negated': True,
                     'values': [None]},
                    {'filter': 'named', 'negated': False, 'values': ['Happy']}
                ]}
            ).distinct().count(),
            3)
        self.assertEqual(
            # printers that are not (named Happy and always work)
            print_query_builder.as_queryset(
                {'filter': 'and', 'negated': True, 'values': [
                    {'filter': 'named', 'negated': False, 'values': ['Happy']},
                    {'filter': 'always works', 'negated': False,
                     'values': [None]}
                ]}
            ).distinct().count(),
            2)
        self.assertEqual(
            # printers that are named Happy and always work
            print_query_builder.as_queryset(
                {'filter': 'and', 'negated': False, 'values': [
                    {'filter': 'named', 'negated': False, 'values': ['Happy']},
                    {'filter': 'always works', 'negated': False,
                     'values': [None]}
                ]}
            ).get(),
            happy_printer)
        self.assertEqual(
            # printers that are named Happy or always work
            print_query_builder.as_queryset(
                {'filter': 'or', 'negated': False, 'values': [
                    {'filter': 'named', 'negated': False, 'values': ['Happy']},
                    {'filter': 'always works', 'negated': False,
                     'values': [None]}
                ]}
            ).get(),
            happy_printer)
        self.assertEqual(
            # printers that are neither named Happy nor always work
            print_query_builder.as_queryset(
                {'filter': 'or', 'negated': True, 'values': [
                    {'filter': 'named', 'negated': False, 'values': ['Happy']},
                    {'filter': 'always works', 'negated': False,
                     'values': [None]}
                ]}
            ).distinct().count(),
            2)
        self.assertEqual(
            # printers that have ever printed or are named Happy
            print_query_builder.as_queryset(
                {'filter': 'or', 'negated': False, 'values': [
                    {'filter': 'has ever printed', 'negated': True,
                     'values': [None]},
                    {'filter': 'named', 'negated': False, 'values': ['Happy']}
                ]}
            ).distinct().count(),
            2)
        self.assertEqual(
            # printers that have neither printed nor are named Happy
            print_query_builder.as_queryset(
                {'filter': 'or', 'negated': True, 'values': [
                    {'filter': 'has ever printed', 'negated': True,
                     'values': [None]},
                    {'filter': 'named', 'negated': False, 'values': ['Happy']}
                ]}
            ).get(),
            slow_printer)

        rendered = Template("""
            {% load query_builder %}
            {% render_query_builder qb %}
        """).render(Context({'qb': print_query_builder}))
        self.assertIn("has ever printed", rendered)
        self.assertIn("always works", rendered)

    def test_search_filter(self):
        select_input = query_builder.SelectInput(
            "a_db_field", {str(i): "option %s" % i for i in range(10)})
        trivial_input = query_builder.ConstantInput(Q(a="b"))

        search_filter_1 = query_builder.SearchFilter(
            "instance", "the instance", [select_input, trivial_input])
        self.assertEqual(search_filter_1.spec(),
                         {'name': 'instance', 'title': 'the instance',
                          'inputs': [select_input.spec(),
                                     trivial_input.spec()]})
        self.assertEqual(str(search_filter_1.as_q(['1', None])),
                         str(Q(a_db_field='1') & Q(a="b")))
        with self.assertRaises(ESPError_Log):
            search_filter_1.as_q(['10000',None])


    def test_select_input(self):
        select_input = query_builder.SelectInput(
            "a_db_field", {str(i): "option %s" % i for i in range(10)})
        self.assertEqual(select_input.spec(),
                         {'reactClass': 'SelectInput',
                          'options': [{'name': i,
                                       'title': 'option %s' % i}
                                      # do set(map(str, range(10))) to get the
                                      # sort order the same as the dict sort
                                      # order.  It doesn't matter in reality,
                                      # but just making it the same is easier
                                      # than writing a thing to compare
                                      # correctly.
                                      for i in set(map(str,range(10)))]})
        # Q objects don't have an __eq__, so they don't compare as equal.  But
        # comparing their str()s seems to work reasonably well.
        self.assertEqual(str(select_input.as_q('5')), str(Q(a_db_field='5')))
        with self.assertRaises(ESPError_Log):
            select_input.as_q('10000')

    def test_trivial_input(self):
        trivial_input = query_builder.ConstantInput(Q(a="b"))
        self.assertEqual(trivial_input.spec(), {'reactClass': 'ConstantInput'})
        self.assertEqual(str(trivial_input.as_q(None)), str(Q(a="b")))

    def test_optional_input(self):
        select_input = query_builder.SelectInput(
            "a_db_field", {str(i): "option %s" % i for i in range(10)})
        optional_input = query_builder.OptionalInput(select_input)
        self.assertEqual(optional_input.spec(),
                         {'reactClass': 'OptionalInput', 'name': '+',
                          'inner': select_input.spec()})
        self.assertEqual(str(optional_input.as_q(None)), str(Q()))
        self.assertEqual(str(optional_input.as_q({'inner': '5'})),
                         str(Q(a_db_field='5')))

    def test_datetime_input(self):
        datetime_input = query_builder.DatetimeInput("a_db_field")
        self.assertEqual(datetime_input.spec(),
                         {'reactClass': 'DatetimeInput', 'name': 'a db field'})
        self.assertEqual(
            str(datetime_input.as_q(
                {'comparison': 'before', 'datetime': '11/30/2015 23:59'})),
            str(Q(a_db_field__lt=datetime.datetime(2015, 11, 30, 23, 59))))
        self.assertEqual(
            str(datetime_input.as_q(
                {'comparison': 'after', 'datetime': '11/30/1995 00:59'})),
            str(Q(a_db_field__gt=datetime.datetime(1995, 11, 30, 0, 59))))
        self.assertEqual(
            str(datetime_input.as_q(
                {'comparison': '', 'datetime': '11/01/2015 23:59'})),
            str(Q(a_db_field=datetime.datetime(2015, 11, 1, 23, 59))))
        with self.assertRaises(ValueError):
            datetime_input.as_q(
                {'comparison': '', 'datetime': '11/41/2015 23:59'})

    def test_text_input(self):
        text_input = query_builder.TextInput("a_db_field")
        self.assertEqual(text_input.spec(),
                         {'reactClass': 'TextInput', 'name': 'a db field'})
        self.assertEqual(str(text_input.as_q("foo bar baz")),
                         str(Q(a_db_field="foo bar baz")))


def suite():
    """Choose tests to expose to the Django tester."""
    s = unittest.TestSuite()
    # Scan this file for TestCases
    s.addTest(unittest.defaultTestLoader.loadTestsFromModule(utils.tests))
    # Add doctests from esp.utils.__init__.py
    s.addTest(doctest.DocTestSuite(utils))
    return s



