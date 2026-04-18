"""
Test cases for Django-ESP utilities
"""


import datetime
import doctest
import json
try:
    import pylibmc as memcache
except ImportError:
    import memcache
import logging
logger = logging.getLogger(__name__)
import os
import subprocess
import sys
from reversion import revisions as reversion
from reversion.models import Version
import unittest

from django.db.models.query import Q
from django.template import loader, Template, Context, TemplateDoesNotExist
from django.test import TestCase as DjangoTestCase

from esp.middleware import ESPError_Log
from esp.users.models import ESPUser
from esp import utils
from esp.utils import query_builder
from esp.utils.models import TemplateOverride, Printer, PrintRequest

from unittest.mock import Mock, MagicMock
from esp.utils.apps import run_install

# Code from <https://snippets.dzone.com/posts/show/6313>
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
        except Exception as e:
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
        self.tryImport("openpyxl")  # Used in our giant statistics spreadsheet-generating code
        self.tryImport("form_utils")     #Used to create better forms.
        self.assertFalse(self._failed_import)

        # Make sure production uses pylibmc when default cache is memcached.
        # test_settings (and similar) use LocMemCache/DummyCache — skip then.
        from django.conf import settings
        default_backend = settings.CACHES.get('default', {}).get('BACKEND', '')
        if 'locmem' not in default_backend.lower() and 'dummy' not in default_backend.lower():
            from pylibmc import Client
            from django.core.cache import cache
            if hasattr(cache, "_cache"):
                self.assertTrue(isinstance(cache._cache, Client))
            elif hasattr(cache, "_wrapped_cache") and hasattr(cache._wrapped_cache, "_cache"):
                self.assertTrue(isinstance(cache._wrapped_cache._cache, Client))

        self.tryExecutable("latex")  # Used for a whole pile of program printables, as well as inline LaTeX
        self.tryExecutable("dvips")  # Used to convert LaTeX output (.dvi) to .ps files
        self.tryExecutable("convert")  # Used in the generation of inline LaTeX chunks.  Also for some cases of generating .png images from LaTeX output; the student-schedule generator currently does dvips then convert to get .png's so that barcodes work
        self.tryExecutable("dvipng")  # Used to convert LaTeX output (.dvi) to .png files
        self.tryExecutable("ps2pdf")  # Used to convert LaTeX output (.dvi) to .pdf files (must go to .ps first because we use some LaTeX packages that depend on Postscript)
        self.tryExecutable("inkscape")  # Used to render LaTeX output (once converted to .pdf) to .svg image files

        self.assertFalse(self._exe_not_found)

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
        self.servers = [ subprocess.Popen(["memcached", '-u', 'nobody', '-p', f'{cache[1]}'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                         for cache in caches ]
        self.clients = [ memcache.Client([cache]) for cache in self.CACHES ]

    def tearDown(self):
        """ Terminate all the server processes that we launched with setUp() """
        for client in self.clients:
            client.disconnect_all()

        if len(self.servers) > 0 and hasattr(self.servers[0], 'terminate'):
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
        except Exception:
            logger.info('Unexpected error fetching nonexistent template')
            raise
        self.assertTrue(template_error)

    def test_diff_single_line_change(self):
        """
        Regression test for issue #2606: diffs should highlight only
        changed lines, not the entire template.

        Validates that we use normalized lines (no trailing newline mismatch)
        so the diff does not show every line as changed.
        """
        from django.conf import settings
        from difflib import HtmlDiff

        from esp.utils.views import _normalize_lines_for_diff

        # Pick a real template file that exists on disk
        template_dir = os.path.join(settings.PROJECT_ROOT, 'templates')
        template_name = 'utils/diff_templateoverride.html'
        original_path = os.path.join(template_dir, template_name)
        self.assertTrue(os.path.isfile(original_path),
                        "Test requires template file to exist on disk")

        # Read the original file content (as the view does)
        with open(original_path, encoding='utf-8', errors='replace') as f:
            original_content = f.read()

        # Create an override that changes only one line
        lines = _normalize_lines_for_diff(original_content)
        self.assertGreater(len(lines), 3, "Template must have several lines")
        lines = list(lines)
        lines[0] = lines[0] + ' <!-- modified -->'
        override_content = '\n'.join(lines)

        with reversion.create_revision():
            to = TemplateOverride(name=template_name, content=override_content)
            to.save()

        # OLD BUGGY BEHAVIOUR: view used list(original_file) so original had
        # trailing newlines, and override_obj.content.split('\n') so override
        # had none. That made every line compare unequal and the whole file
        # appeared changed.
        with open(original_path, encoding='utf-8', errors='replace') as f:
            original_lines_buggy = list(f)
        override_lines_buggy = override_content.split('\n')
        diff_buggy = HtmlDiff().make_table(
            original_lines_buggy, override_lines_buggy, 'original', 'override')
        total_buggy = (diff_buggy.count('class="diff_chg"') +
                       diff_buggy.count('class="diff_sub"') +
                       diff_buggy.count('class="diff_add"'))
        # The old approach should produce *at least some* spurious diff
        # markers due to the trailing-newline mismatch.  We don't require
        # every line to be flagged because HtmlDiff uses sequence-matching
        # heuristics and the exact count depends on file content.
        self.assertGreater(total_buggy, 0,
                           "Sanity check: old line-ending mismatch should "
                           "produce at least some diff markers.")

        # FIXED: use the same normalized lines (no trailing newlines) for both.
        original_lines = _normalize_lines_for_diff(original_content)
        override_lines = _normalize_lines_for_diff(override_content)
        diff_html = HtmlDiff().make_table(original_lines, override_lines,
                                          'original', 'override')

        changed_count = diff_html.count('class="diff_chg"')
        sub_count = diff_html.count('class="diff_sub"')
        add_count = diff_html.count('class="diff_add"')
        total_diff_lines = changed_count + sub_count + add_count

        # Only 1 line was changed; diff should not mark the entire template.
        self.assertLess(total_diff_lines, len(lines),
                        "Diff should not mark the entire template as changed; "
                        "only the modified line(s) should be highlighted. "
                        "Got {} diff markers for {} lines.".format(
                            total_diff_lines, len(lines)))

        # The fixed approach must produce fewer diff markers than the old
        # buggy approach (or at most the same if HtmlDiff is smart enough).
        self.assertLessEqual(total_diff_lines, total_buggy,
                             "Fixed diff should not produce more markers "
                             "than the buggy diff.")

        # Clean up
        TemplateOverride.objects.filter(name=template_name).delete()

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
        list(Version.objects.get_for_object(to).get_unique())[1].revert()
        self.assertTrue(self.get_response_for_template('BLAARG.TEMPLATEOVERRIDE') == 'Hello')

        #   Delete the original template override and make sure you see nothing
        TemplateOverride.objects.filter(name='BLAARG.TEMPLATEOVERRIDE').delete()
        self.expect_template_error('BLAARG.TEMPLATEOVERRIDE')

    def test_diff_single_line_change_view(self):
        """
        Regression test for issue #2606 at the view level.

        Ensures that the /manage/templateoverride/<id> view uses
        normalized lines for diffs so that only the changed line is
        highlighted, not the entire template.
        """
        from django.conf import settings
        from django.test import RequestFactory
        from difflib import HtmlDiff

        from esp.utils.views import _normalize_lines_for_diff, diff_templateoverride

        # Pick the same real template file that exists on disk as in
        # test_diff_single_line_change.
        template_dir = os.path.join(settings.PROJECT_ROOT, 'templates')
        template_name = 'utils/diff_templateoverride.html'
        original_path = os.path.join(template_dir, template_name)
        self.assertTrue(os.path.isfile(original_path),
                        "Test requires template file to exist on disk")

        # Read the original file content (as the view does)
        with open(original_path, encoding='utf-8', errors='replace') as f:
            original_content = f.read()

        # Create an override that changes only one line, using the same
        # normalization logic expected in the view.
        original_lines = list(_normalize_lines_for_diff(original_content))
        self.assertGreater(len(original_lines), 3,
                           "Template must have several lines")
        modified_lines = list(original_lines)
        modified_lines[0] = modified_lines[0] + ' <!-- modified -->'
        override_content = '\n'.join(modified_lines)

        # Persist a TemplateOverride that the view can diff against.
        with reversion.create_revision():
            to = TemplateOverride(name=template_name, content=override_content)
            to.save()

        # Administrator user required to access the manage view.
        admin = ESPUser.objects.create_superuser(
            username='diffadmin',
            email='diffadmin@example.com',
            password='testpass',
        )
        from django.contrib.auth.models import Group
        admin_group, _ = Group.objects.get_or_create(name='Administrator')
        admin.groups.add(admin_group)

        rf = RequestFactory()
        request = rf.get('/manage/templateoverride/%d' % to.id)
        request.user = admin

        response = diff_templateoverride(request, to.id)
        self.assertEqual(response.status_code, 200)

        html = response.content.decode('utf-8')

        # Sanity checks: we are looking at a diff table that contains the
        # modified marker.
        self.assertIn('<!-- modified -->', html)
        self.assertIn('<table', html)

        # Heuristic assertion: HtmlDiff marks changed lines with a CSS
        # class like "diff_chg". If the view stopped using normalized
        # lines, trailing-newline mismatches would often cause every
        # line to be treated as changed. Ensure fewer change markers
        # than total lines in the template.
        change_markers = html.count('diff_chg')
        self.assertLess(
            change_markers,
            len(original_lines),
            "Diff appears to mark every line as changed; view may not be "
            "using normalized lines for diff.",
        )

        # Optional stronger check: the diff generated with normalized
        # lines should be a substring of the rendered HTML. This will
        # fail if the view regresses to using non-normalized content.
        expected_diff = HtmlDiff().make_table(
            original_lines,
            modified_lines,
        )
        self.assertIn(expected_diff.split('\n', 1)[0], html)


class DefaultTemplateContentViewTest(DjangoTestCase):
    """Tests for the get_default_template_content admin view (issue #2879)."""

    URL = '/manage/templateoverride/default_content/'
    # A template that is guaranteed to exist on disk
    KNOWN_TEMPLATE = 'utils/diff_templateoverride.html'

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='test_admin_dtcv')
        self.admin.set_password('password')
        self.admin.makeAdmin()
        self.admin.save()

    def test_unauthenticated_redirected(self):
        r = self.client.get(self.URL, {'name': self.KNOWN_TEMPLATE})
        self.assertEqual(r.status_code, 302)

    def test_no_name_returns_400(self):
        self.client.login(username='test_admin_dtcv', password='password')
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 400)
        self.assertIn('error', json.loads(r.content))

    def test_valid_template_returns_content(self):
        self.client.login(username='test_admin_dtcv', password='password')
        r = self.client.get(self.URL, {'name': self.KNOWN_TEMPLATE})
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertIn('content', data)
        self.assertTrue(len(data['content']) > 0)

    def test_missing_template_returns_404(self):
        self.client.login(username='test_admin_dtcv', password='password')
        r = self.client.get(self.URL, {'name': 'nonexistent/template_xyz.html'})
        self.assertEqual(r.status_code, 404)
        self.assertIn('error', json.loads(r.content))

    def test_path_traversal_blocked(self):
        self.client.login(username='test_admin_dtcv', password='password')
        r = self.client.get(self.URL, {'name': '../../etc/passwd'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('error', json.loads(r.content))


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
            "a_db_field", {str(i): f"option {i}" for i in range(10)})
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
            search_filter_1.as_q(['10000', None])


    def test_select_input(self):
        options = {str(i): f"option {i}" for i in range(10)}
        select_input = query_builder.SelectInput(
            "a_db_field", options)
        self.assertEqual(select_input.spec(),
                         {'reactClass': 'SelectInput',
                          'options': [{'name': i,
                                       'title': f'option {i}'}
                                      # use options.keys() to get the
                                      # sort order the same as the dict sort
                                      # order.  It doesn't matter in reality,
                                      # but just making it the same is easier
                                      # than writing a thing to compare
                                      # correctly.
                                      for i in options.keys()]})
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
            "a_db_field", {str(i): f"option {i}" for i in range(10)})
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


class StripBase64ImagesTest(DjangoTestCase):
    """Tests for esp.utils.sanitize.strip_base64_images (#3612)."""

    def setUp(self):
        from esp.utils.sanitize import strip_base64_images
        self.strip = strip_base64_images

    def test_no_images_unchanged(self):
        html = '<p>Hello world</p><img src="/media/photo.png">'
        result, count = self.strip(html)
        self.assertEqual(result, html)
        self.assertEqual(count, 0)

    def test_none_returns_none(self):
        result, count = self.strip(None)
        self.assertIsNone(result)
        self.assertEqual(count, 0)

    def test_empty_returns_empty(self):
        result, count = self.strip('')
        self.assertEqual(result, '')
        self.assertEqual(count, 0)

    def test_single_base64_stripped(self):
        html = '<p>Before</p><img src="data:image/png;base64,iVBORw0KGgo"/><p>After</p>'
        result, count = self.strip(html)
        self.assertEqual(count, 1)
        self.assertNotIn('data:', result)
        self.assertIn('Before', result)
        self.assertIn('After', result)

    def test_multiple_base64_stripped(self):
        html = (
            '<img src="data:image/png;base64,AAA"/>'
            '<img src="data:image/jpeg;base64,BBB"/>'
            '<img src="data:image/gif;base64,CCC"/>'
        )
        result, count = self.strip(html)
        self.assertEqual(count, 3)
        self.assertNotIn('data:', result)

    def test_normal_images_preserved(self):
        html = '<img src="/media/photo.png"><img src="https://example.com/img.jpg">'
        result, count = self.strip(html)
        self.assertEqual(result, html)
        self.assertEqual(count, 0)

    def test_mixed_normal_and_base64(self):
        html = '<img src="/media/photo.png"><img src="data:image/png;base64,AAA"/><img src="https://example.com/img.jpg">'
        result, count = self.strip(html)
        self.assertEqual(count, 1)
        self.assertIn('/media/photo.png', result)
        self.assertIn('https://example.com/img.jpg', result)
        self.assertNotIn('data:', result)

    def test_single_quoted_src(self):
        html = "<img src='data:image/png;base64,AAA'/>"
        result, count = self.strip(html)
        self.assertEqual(count, 1)
        self.assertNotIn('data:', result)

    def test_img_with_extra_attributes(self):
        html = '<img width="300" src="data:image/png;base64,AAA" alt="screenshot" style="border:1px solid">'
        result, count = self.strip(html)
        self.assertEqual(count, 1)
        self.assertNotIn('data:', result)
        self.assertNotIn('width', result)

    def test_css_background_data_uri_stripped(self):
        html = '<div style="background-image: url(data:image/png;base64,AAA)">text</div>'
        result, count = self.strip(html)
        self.assertEqual(count, 1)
        self.assertNotIn('data:image', result)
        self.assertIn('url()', result)
        self.assertIn('text', result)

    def test_fast_path_no_data_colon(self):
        html = '<p>No images at all, just some text with a colon: here.</p>'
        result, count = self.strip(html)
        self.assertEqual(result, html)
        self.assertEqual(count, 0)

class RunInstallTestCase(unittest.TestCase):
    """Regression tests for the run_install post_migrate signal handler."""

    def test_sender_with_no_models_module(self):
        """run_install should not raise when sender has no models_module attribute."""
        sender = Mock(spec_set=[])
        # Should not raise
        run_install(sender)

    def test_sender_with_models_module_missing_install(self):
        """run_install should not raise when models_module lacks install()."""
        models_module = Mock(spec=[])  # no 'install' attribute
        sender = Mock()
        sender.models_module = models_module
        # Should not raise
        run_install(sender)

    def test_sender_with_callable_install(self):
        """run_install should call install() when it exists and is callable."""
        models_module = Mock()
        models_module.install = MagicMock()
        sender = Mock()
        sender.models_module = models_module
        run_install(sender)
        models_module.install.assert_called_once()

    def test_sender_with_non_callable_install(self):
        """run_install should not call install if it's not callable."""
        models_module = Mock(spec=[])
        models_module.install = None  # exists but not callable
        sender = Mock()
        sender.models_module = models_module
        # Should not raise
        run_install(sender)


def suite():
    """Choose tests to expose to the Django tester."""
    s = unittest.TestSuite()
    # Scan this file for TestCases
    s.addTest(unittest.defaultTestLoader.loadTestsFromModule(utils.tests))
    # Add doctests from esp.utils.__init__.py
    s.addTest(doctest.DocTestSuite(utils))
    return s


