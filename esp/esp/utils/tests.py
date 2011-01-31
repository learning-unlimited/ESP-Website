"""
Test cases for Django-ESP utilities
"""

import unittest
import doctest
import subprocess

try:
    import pylibmc as memcache
except:
    import memcache

import os
import sys
try:
    from utils.memcached_multihost import CacheClass as MultihostCacheClass
except:
    MultihostCacheClass = False
    print "Couldn't import MultihostCacheClass.  Not running tests against it."
from utils.defaultclass import defaultclass
from esp import utils
from esp import settings

from django.test import TestCase as DjangoTestCase

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
        self.tryImport("_imaging")  # Internal PIL module; PIL will import without it, but it won't have a lot of the functionality that we need
        self.tryImport("pylibmc")  # We currently depend specifically on the "pylibmc" Python<->memcached interface library.
        self.tryImport("DNS")  # Used for validating e-mail address hostnames.  Imports as DNS, but the package and egg are named "pydns".
        self.tryImport("simplejson")  # Used for some of our AJAX magic
        self.tryImport("icalendar")  # Currently not significantly used, but we have some hanging imports.  Originally used for exporting .ics calendar files, usable by many calendaring applications; we may do this again at some point.
        self.tryImport("twill")  # Used for unit testing against an actual server
        self.tryImport("flup")  # Used for interfacing with lighttpd via FastCGI
        self.tryImport("psycopg2")  # Used for talking with PostgreSQL.  Someday, we'll support psycopg2, but not today...
	self.tryImport("xlwt")  # Used in our giant statistics spreadsheet-generating code

        self.assert_(not self._failed_import)

        # Make sure that we're actually using pylibmc.
        # Note that this requires a patch to Django.
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
        self.servers = [ subprocess.Popen(["memcached", "-p %s" % cache[1]], stderr=open(os.devnull, "w"))
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

if MultihostCacheClass:
    class MultihostCacheClassTest(MemcachedTestCase):
        """
        Test cases for the memcached_multihost CacheClass class
        """

        CACHES = [ "127.0.0.1:11213",
                   "127.0.0.1:11214",
                   "127.0.0.1:11215",
                   "127.0.0.1:11216",
                   "127.0.0.1:11217",
                   "127.0.0.1:11218",
                   "127.0.0.1:11219" ]
        
        CACHE_BACKENDS = CACHES[:5] + [ ";".join(CACHES[5:7]) ]
        
        def setUp(self):
            """
            Create and configure a MultihostCacheClass instance to test.
            Also, our last two servers are actually joined; update accordingly.
            """
            super(MultihostCacheClassTest, self).setUp()
            
            for client in self.clients[5:7]:
                client.disconnect_all()
            self.clients = self.clients[:5] #+ [ memcache.Client(self.CACHES[5:7]) ]
            
            self._old_REMOTE_CACHE_SERVERS = getattr(settings, 'REMOTE_CACHE_SERVERS', None)
            settings.REMOTE_CACHE_SERVERS = self.CACHE_BACKENDS[1:3] + self.CACHE_BACKENDS[5:6]
            
            self._old_REMOTE_CACHES_TO_FLUSH = getattr(settings, 'REMOTE_CACHES_TO_FLUSH', None)
            settings.REMOTE_CACHES_TO_FLUSH = self.CACHE_BACKENDS[3:5]
            
            self._old_CACHE_PREFIX = settings.CACHE_PREFIX
            settings.CACHE_PREFIX = "TEST_"
            
            self.cacheclass = MultihostCacheClass(self.CACHE_BACKENDS[0], {})
            
        def tearDown(self):
            """
            Clean up our MultihostCacheClass instance
            """
            self.cacheclass.close()
            super(MultihostCacheClassTest, self).tearDown()
            
            settings.REMOTE_CACHE_SERVERS = self._old_REMOTE_CACHE_SERVERS
            settings.REMOTE_CACHES_TO_FLUSH = self._old_REMOTE_CACHES_TO_FLUSH
            settings.CACHE_PREFIX = self._old_CACHE_PREFIX

        def make_key(self, key):
            """
            Make a proper cache key from the given string, by prepending our cache prefix.
            Recall that the cache clients that we're given are raw memcached clients;
            they know nothing about Django at all, and they certainly don't know about the
            custom cache key setup that the Multihost class that we're testing, uses.
            """
            return settings.CACHE_PREFIX + key
        
        def validate_inAllClients(self, key, value):
            """ Validate that the given key is set in all clients to the given value """
            for client in self.clients:
                client_value = client.get( self.make_key(key) )
                self.assertEqual(client_value, value)

        def validate_inUpdatingClients(self, key, value):
            """ Validate that the given key is set in clients that we're updating, to the given value """
            for client in self.clients[0:3] + self.clients[5:6]:
                client_value = client.get( self.make_key(key) )
                self.assertEqual(client_value, value)
                
        def validate_inDeleteOnlyClients(self, key, value):
            """ Validate that the given key is set in clients that we're only flushing, to the given value """
            for client in self.clients[3:5]:
                client_value = client.get( self.make_key(key) )
                self.assertEqual(client_value, value)
            
        def testGet(self):
            # This is already tested implicitly by lots of other tests
            # (since it's the best way to validate that insert/update operations did the right thing).
            # Oh well, being explicit is good, and it's a cheap test.
            self.cacheclass.set('testGet', 'key')
            self.assertEqual('key', self.cacheclass.get('testGet'))

        def testAdd(self):
            # Wipe any existing key value, just in case
            self.cacheclass.delete("testAdd")

            # Do a straight add
            self.cacheclass.add('testAdd', 'key')
            self.validate_inUpdatingClients('testAdd', 'key')
            self.validate_inDeleteOnlyClients('testAdd', None)

            # Make sure we can't re-add stuffs
            self.cacheclass.add('testAdd', 'new_key')
            self.validate_inUpdatingClients('testAdd', 'key')
            self.validate_inDeleteOnlyClients('testAdd', None)

            # Make sure that, when we clobber stuff, it gets deleted from delete clients
            self.cacheclass.delete("testAddClobber")
            for client in self.clients[1:]:
                client.set( self.make_key("testAddClobber"), "some key" )

            self.cacheclass.add("testAddClobber", "another key!")
            self.validate_inDeleteOnlyClients('testAddClobber', None)
            
            # but only if we actually clobber things
            for client in self.clients[0:3] + self.clients[5:7]:
                client.set( self.make_key("testAddClobber"), "some key" )
            for client in self.clients[3:5]:
                client.set( self.make_key("testAddClobber"), "a third key!!" )

            self.cacheclass.add("testAddClobber", "key that's doomed to get ignored...")
            self.validate_inUpdatingClients('testAddClobber', 'some key')
            self.validate_inDeleteOnlyClients('testAddClobber', 'a third key!!')
        
        def testSet(self):
            # Clear out old cached keys, just in case
            self.cacheclass.delete('testSet')
            
            # Do a straight set
            self.cacheclass.set('testSet', 'key')
            self.validate_inUpdatingClients('testSet', 'key')
            self.validate_inDeleteOnlyClients('testSet', None)
        
            # Make sure we can clobber stuffs
            self.cacheclass.set('testSet', 'new_key')
            self.validate_inUpdatingClients('testSet', 'new_key')
            self.validate_inDeleteOnlyClients('testSet', None)

            # Make sure that, when we clobber stuff, it gets deleted from delete clients
            for client in self.clients:
                client.set( self.make_key("testSetClobber"), "some key" )

            self.cacheclass.set("testSetClobber", "another key!")
            self.validate_inUpdatingClients('testSetClobber', 'another key!')
            self.validate_inDeleteOnlyClients('testSetClobber', None)
        
        def testDelete(self):
            # Clear out old cached keys, just in case
            self.cacheclass.delete('testDelete')
            
            # Set a key, then make sure we can make it go away
            self.validate_inAllClients('testDelete', None)
            self.cacheclass.set('testDelete', 'key')
            self.validate_inUpdatingClients('testDelete', 'key')
            self.validate_inDeleteOnlyClients('testDelete', None)
            self.cacheclass.delete('testDelete')
            self.validate_inAllClients('testDelete', None)

        def testGetMany(self):
            # Set a bunch of keys, then try getting them
            keys = ['one', 'two', 'three']
            values = ['1', '2', '3']

            for key, value in zip(keys, values):
                self.cacheclass.set(key, value)

            self.assertEqual(dict(zip(keys, values)), self.cacheclass.get_many(keys))
            
        def testHasKey(self):
            # Test has_key() and __contains__() in the same function, since they're
            # supposed to have identical functionality:
            self.cacheclass.set('test_HasKey', 'Purple Water Buffalo')        
            
            self.assert_(self.cacheclass.has_key('test_HasKey'))
            self.assert_(self.cacheclass.__contains__('test_HasKey'))
            self.assert_('test_HasKey' in self.cacheclass)

        def testIncrDecr(self):
            # Also combine the incr() and decr() tests, 'cause I'm lazy:
            self.cacheclass.set('test_math', 1)
            self.cacheclass.decr('test_math')
            self.assertEqual(0, self.cacheclass.get('test_math'))
            self.cacheclass.incr('test_math')
            self.cacheclass.incr('test_math')
            self.cacheclass.incr('test_math')
            self.assertEqual(3, self.cacheclass.get('test_math'))
        

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
        

        
def suite():
    """Choose tests to expose to the Django tester."""
    s = unittest.TestSuite()
    # Scan this file for TestCases
    s.addTest(unittest.defaultTestLoader.loadTestsFromModule(utils.tests))
    # Add doctests from esp.utils.__init__.py
    s.addTest(doctest.DocTestSuite(utils))
    return s



