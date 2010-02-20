"""
Test cases for Django-ESP utilities
"""

import unittest
import subprocess
try:
    import pylibmc as memcache
except:
    import memcache
import os
from utils.memcached_multihost import CacheClass as MultihostCacheClass
from esp import settings

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
        
