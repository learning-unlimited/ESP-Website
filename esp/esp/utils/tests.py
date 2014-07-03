"""
Test cases for Django-ESP utilities
"""

from __future__ import with_statement

import unittest
import doctest
import subprocess

try:
    import pylibmc as memcache
except:
    import memcache

import os
import sys
from esp.utils.defaultclass import defaultclass
from esp import utils
from django.conf import settings
from esp.utils.models import TemplateOverride

from django.test import TestCase as DjangoTestCase

from django.core.management import call_command
from django.core.cache.backends.base import default_key_func
from django.db.models import loading

from django.template import loader, Template, Context, TemplateDoesNotExist
import reversion

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
            print "Error importing required module '%s': %s" % (mod, e)
            self._failed_import = True
    
    def tryExecutable(self, exe):
        if not find_executable(exe):
            print "Executable not found:  '%s'" % exe
            self._exe_not_found = True

    def testDeps(self):
        self._failed_import = False
        self._exe_not_found = False
        
        self.tryImport("django")  # If this fails, we lose.
        self.tryImport("PIL")  # Needed for Django Image fields, which we use for (among other things) teacher bio's
        self.tryImport("PIL._imaging")  # Internal PIL module; PIL will import without it, but it won't have a lot of the functionality that we need
        self.tryImport("pylibmc")  # We currently depend specifically on the "pylibmc" Python<->memcached interface library.
        self.tryImport("DNS")  # Used for validating e-mail address hostnames.  Imports as DNS, but the package and egg are named "pydns".
        self.tryImport("simplejson")  # Used for some of our AJAX magic
        self.tryImport("icalendar")  # Currently not significantly used, but we have some hanging imports.  Originally used for exporting .ics calendar files, usable by many calendaring applications; we may do this again at some point.
        self.tryImport("flup")  # Used for interfacing with lighttpd via FastCGI
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
        self.servers = [ subprocess.Popen(["memcached", '-u', 'nobody', '-p', '%s' % cache[1]], stderr=open(os.devnull, "w"))
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
        self.failUnless(response.status_code != 500, 'Ridiculous URL not handled gracefully.')


class DefaultclassTestCase(unittest.TestCase):
    def testDefaultclass(self):
        """ Verify that defaultclass correctly lets you select out a custom instance of a class """
        class kls(object):
            @classmethod
            def get_name(cls):
                return cls.__name__
            def get_hi(self):
                return "hi!"
                
        kls = defaultclass(kls)

        myKls = kls()
        self.assertEqual(myKls.get_name(), "kls")
        self.assertEqual(myKls.get_hi(), "hi!")
        self.assertEqual(kls.get_name(), "kls")

        myKls2 = kls[0]()
        self.assertEqual(myKls.get_name(), "kls")

        class otherKls(kls.real):
            pass

        myOtherKls = otherKls()
        self.assertEqual(myOtherKls.get_name(), "otherKls")
        
        kls[0] = otherKls
    
        myOtherKls2 = kls[0]()
        self.assertEqual(myOtherKls2.get_name(), "otherKls")
        
class DBOpsTestCase(DjangoTestCase):
    def testSyncdb(self):
        loading.cache.loaded = False
        call_command('syncdb', verbosity=0)
    def testMigrate(self):
        loading.cache.loaded = False
        call_command('migrate', verbosity=0)
        
class TemplateOverrideTest(DjangoTestCase):
    def get_response_for_template(self, template_name):
        template = loader.get_template(template_name)
        return template.render(Context({}))

    def expect_template_error(self, template_name):
        template_error = False
        try:
            self.get_response_for_template(template_name)
        except TemplateDoesNotExist:
            template_error = True
        except:
            print 'Unexpected error fetching nonexistent template'
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
        reversion.get_unique_for_object(to)[1].revert()
        self.assertTrue(self.get_response_for_template('BLAARG.TEMPLATEOVERRIDE') == 'Hello')

        #   Delete the original template override and make sure you see nothing
        TemplateOverride.objects.filter(name='BLAARG.TEMPLATEOVERRIDE').delete()
        self.expect_template_error('BLAARG.TEMPLATEOVERRIDE')

def suite():
    """Choose tests to expose to the Django tester."""
    s = unittest.TestSuite()
    # Scan this file for TestCases
    s.addTest(unittest.defaultTestLoader.loadTestsFromModule(utils.tests))
    # Add doctests from esp.utils.__init__.py
    s.addTest(doctest.DocTestSuite(utils))
    return s



