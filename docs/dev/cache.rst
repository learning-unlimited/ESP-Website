ESP Caching Framework
==============================
*Technical documentation*

Authors: 
   - David Benjamin <davidben@mit.edu>

.. contents:: :local:

The ESP caching framework provides a (hopefully) easy-to-use set of
APIs to simplify caching functions and maintain correctness of their
values. The intent is to minimize boilerplate code and make it easy to
delete caches correctly. Also, all code related to a cache should be
in one place. The framework handles boring things such as key
creation, cache lookup, etc.

Caches are applied on a function-level granularity. So, split off
functions as-needed. Also, such functions really shouldn't have
side-effects. Split up your functions if needed. Conceptually, each
cache maps keys to values, where keys correspond to function
arguments. The caches can invalidate keys in bulk by sets of keys, and
propagate invalidations up to dependent caches. We limit the types of
key sets that may be expressed so that this is implementable.


Invalidation Strategy
---------------------

Internally, invalidations are done by maintaining a signature along
with each cache entry. Before returning a value, we check that this
signature is current. If not, we pretend the value was never there in
the first place. This signature is computed from other cache values
called tokens which are shared so that, by resetting a particular
token, we can implicitly bulk-invalidate a chosen subset of the keys,
notably the subset which depends on that token. Currently the stored
value is wrapped into a tuple with the signature. This is likely to
change in future to more easily support incr/decr. Unlike the
tiered-caching system, keys intentionally do not depend on tokens so
that they can be grabbed in bulk by get_many. This avoids the overhead
of multiple cache requests. An Asynchronous API to simplify and extend
this is underway.


ArgCache
--------

The core class in esp.cache is ArgCache. It handles a crapload of
stuff and is very much in need of splitting up. An ArgCache contains a
cache parameterized by a list of arguments. It exports a similar API to
Django's cache objects, but the keys are lists of Python objects
rather than strings. The marinade module (as a pun a Python's pickle)
handles stringifying these objects. In addition, ArgCache provides
methods to register dependencies and delete_key_set, which takes a
key_set and deletes everything in it. It may fallback on deleting more
if need be (in the case that it lacks a Token for the job). Upon
deletion, it emits a signal with the key_set, so that other ArgCaches
may listen and react appropriately.


Key sets
--------

Key sets are represented by dictionaries. (We could use lists, but for
convenience, the names of the arguments are incorporated.) They map
the arguments of an ArgCache (by name) to sets of objects. You can
think of them as Cartesian products of these sets by
argument. Currently, the only expressible sets are wildcard (that is,
everything) and a specific object, and the API is a little iffy. If a
(key,value) pair is missing for an argument, it should be assumed to
be wildcard (we may explicitly add them later). Exact objects are
represented by themselves, and wildcard is represented by a special
value, wildcard, in esp.cache.key_set. More special values will be
added when the infrastructure is in place. (Notably, I want to handle
ancestor/descendant stuff in DataTree.)


Tokens
------

[ NOTE: The following section is much more general than what is
currently implemented, but it's where I want to go with it all. ]

Each ArgCache maintains a list of Tokens. This will probably be
renamed to handles at some point. A Token, given a key to its
ArgCache, generates a signature (which will probably be renamed to
token). The ArgCache combines all of these signatures to form the
final signature. Most of the operations on an ArgCache are linear in
the number of tokens, so there shouldn't be too many per-cache. Tokens
know how to invalidate the signatures of various classes of key sets,
with a different class for each token. On delete_key_set, ArgCache
tries to find a token that can delete the given key set (or something
larger) and calls it. It will eventually find one because every
ArgCache comes with a token that invalidates the entire cache.

Currently, the only types of tokens are ones that can handle key sets
of the form (wildcard, wildcard, something, wildcard, something
else). That is, combinations of specified objects and wildcards. (To
give an idea of the flavor of these, this Tokens extracts its
specified argument and looks up a key based on that value.) Tokens are
currently created by the get_or_create_token function which is really
clumsy, but meh. It takes a tuple (or list) of the names of specified
arguments.


Dependencies
------------

Of course, all this would be pointless if we didn't have some way to
handle dependencies. Dependencies are implemented using signals. When
a model changes, we hook into Django's signals (and a couple we
monkey-patch in) and call delete_key_set as needed. This, however,
gets tedious and it's easy to forget to pass non-weak references, so
ArgCache provides a convenience method depend_on_row. You pass it a
model and function to provide the key set. The function is of the form
lambda instance: {'blah': blah, ...}. Because Python's lambda syntax
sucks, depend_on_row also takes an optional filter argument which is
another lambda returning True or False. Anything which does not pass
the filter gets ignored.

There are also other methods depend_on_cache and depend_on_m2m which
hook into cache change and m2m change signals, respectively. The m2m
signal has similar function as depend_on_row, but there are two of
them: add_func and rem_func. (If the latter is omitted, the former is
used.) Both also take similar filter arguments as depend_on_row.

depend_on_cache has a slightly special mapping function. Here, we take
advantage of the dictionary representation of key sets. The mapping
function should be of the form
::

  lambda arg1=wildcard, arg2=wildcard, arg3=wildcard, **kwargs: {.....}

The default arguments handle the implicit default attribute of key
sets (requirement will likely be removed later), and kwargs captures
arguments that were added later or that you don't care about. As a
convenience, doing most things with wildcard return more wildcards, so
you shouldn't need to explicitly check it often. (Similar to NaN.)

Finally, as an implementation detail, you may often have to refer to a
value before it is defined in Python. For instance, referring to a
class before it has been initialized or circular import issues. To
remedy this, ArgCache delays all dependency processing until after
everything has loaded. This processing is done in the esp.cache_loader
module which MUST be loaded last. After it has run, a flag is set that
makes it an error to define new caches. This does not fully solve the
problem, because Python is applicative-order. To deal with this, wrap
your model reference with lambda when needed. depend_on_* will notice
when it has a thunk and dethunk it. As an example of all this,
::

  depend_on_row(lambda:UserBit, lambda bit: {'user': bit.user},
  				lambda bit: bit.applies_to_verb('V/Administer/Edit'))


Decorator Interface
-------------------

All this does not handle the boilerplate code of checking the cache,
calling the actual function if missing, finding the function name,
etc. ArgCache has a subclass ArgCacheDecorator (with an alias
cache_function) that takes a function and extracts all the necessary
information with a ton of Python magic. It also wraps the function in
a cache lookup. Simply add @cache_decorator and you're set. As a full
example,

(Note: This example does have a slight problem if
Program.objects.get(...) throws an exception... ArgCache should
probably be set up to dump everything when an exception gets raised,
although in this case the correct response is to do nothing.)

::

    @cache_function
    def getAvailableTimes(self, program, ignore_classes=False):
        """ Return a list of the Event objects representing the times that a particular user
            can teach for a particular program. """
        from esp.resources.models import Resource
        from esp.cal.models import Event

        valid_events = Event.objects.filter(resource__user=self, anchor=program.anchor)

        if ignore_classes:
            #   Subtract out the times that they are already teaching.
            other_sections = self.getTaughtSections(program)

            other_times = [sec.meeting_times.values_list('id', flat=True) for sec in other_sections]
            for lst in other_times:
                valid_events = valid_events.exclude(id__in=lst)

        return valid_events
    getAvailableTimes.get_or_create_token(('self', 'program',))
    getAvailableTimes.depend_on_cache(getTaughtSections,
            lambda self=wildcard, program=wildcard, **kwargs:
                 {'self':self, 'program':program, 'ignore_classes':True})
    getAvailableTimes.depend_on_m2m(lambda:ClassSection, 'meeting_times', lambda sec, event: {'program': sec.parent_program})
    getAvailableTimes.depend_on_row(lambda:Resource, lambda resource:
                                        {'program': Program.objects.get(anchor=resource.event.anchor),
                                            'self': resource.user})


Writing cache dependencies
--------------------------

Getting the dependencies right is the hard part of using ``@cache_function``.
Too few dependencies and the site serves stale data, too many and the cache
is thrown away so often it stops helping.

A checklist
~~~~~~~~~~~

#. List every model, field, and relation the function body reads. This includes
   anything reached through a property or a helper it calls.
#. Declare a dependency for each one.
#. Choose a key set: which of the function's *arguments* does this change
   affect?
#. If the key set names only some of the arguments, add a matching token.
#. Ideally, write a test that asserts invalidation happens, *and* one that
   asserts an unrelated key survives.

A key set without a token does nothing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is the trap that catches people most often. Writing a scoped key set is
not enough::

    # getFullClasses_pretty(self, program) -- two arguments
    getFullClasses_pretty.depend_on_row('program.ClassSubject',
                                        lambda cls: {'program': cls.parent_program})

The key set names ``program`` but not ``self``, so it identifies a *set* of
cache entries rather than one entry. argcache needs a ``Token`` to delete a set
like that. Without one it falls back to the token every cache has (the one
that deletes everything) and the key set has no effect at all.

Declare the token explicitly::

    getFullClasses_pretty.get_or_create_token(('program',))

The exception is a key set that names *every* argument. That identifies exactly
one entry, so argcache deletes it directly and no token is needed. This is why
``timeslots(prog)`` works with just ``{'prog': ...}`` and no token, while
``ajax_lunch_timeslots_cached(self, prog)`` needs a ``('prog',)`` token.

Each key set needs its own token
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tokens cover key sets, not functions. A cache with one dependency keyed on
``{'self': ...}`` and another keyed on ``{'program': ...}`` needs *two* tokens.
A single ``('self', 'program')`` token covers neither, because it describes key
sets that specify both at once.

``depend_on_model`` dumps the whole cache
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``depend_on_model(Model)`` with no key set discards every entry in the cache
whenever any row of that model changes. That is sometimes correct: global
configuration models such as ``ProgramModule``, ``RegistrationType`` and
``ClassFlagType`` have no per-program rows, so any change really can affect
every program.

It is wrong when the model *does* map to something the cache is keyed on. Use
``depend_on_row`` with a selector instead::

    getTimeSlotList.depend_on_row('cal.Event',
                                  lambda e: {'self': e.program} if e.program_id else {})

Note that one wildcard dependency undoes the scoping of every other dependency
on the same cache. A cache is only as narrowly invalidated as its loosest
dependency.

Many-to-many changes do not trigger depend_on_row/depend_on_model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the cached value depends on a many-to-many relation, you need ``depend_on_m2m``::

    catalog_cached.depend_on_m2m('program.ClassSubject', 'teachers',
                                 lambda subj, teacher: {'program': subj.parent_program})

This is easy to miss because the relation is often read indirectly. The catalog
orders classes by their sections' meeting times, so rescheduling a class would otherwise change
the catalog without invalidating its cache.

Selectors must not raise
~~~~~~~~~~~~~~~~~~~~~~~~

argcache does not guard against exceptions in selectors. Where a selector
traverses relations that might be missing, catch broadly and return ``{}``:
over-invalidating costs a rebuild, under-invalidating serves wrong data.

Nullable foreign keys need a fallback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``Event.program`` and ``ResourceType.program`` are nullable. Returning
``{'prog': None}`` produces a key that matches nothing, so the real entries are
never invalidated. Fall back to ``{}`` instead::

    lambda e: {'prog': e.program} if e.program_id else {}

Prefer depend_on_cache over repeating yourself
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your function calls another cached function, depend on that cache rather than
re-declaring its dependencies. The coverage is transitive and stays correct when
the inner function changes. ``jsondatamodule.sections`` does this for
``get_teachers``, ``friendly_times`` and ``_get_capacity``.

Time-based caches need no dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``@cache_function_for(seconds)`` expires on a timer and ignores dependencies
entirely. Bounded staleness is the design, so do not add dependencies to one.

Testing invalidation
~~~~~~~~~~~~~~~~~~~~

Cached functions accept ``cache_only=True``, which returns ``None`` on a miss.
That is the hook for asserting on cache state directly, rather than trying to
construct a value that visibly changes::

    program.getTimeSlotList()                                    # warm
    assert program.getTimeSlotList(cache_only=True) is not None
    Event.objects.create(program=program, ...)
    assert program.getTimeSlotList(cache_only=True) is None      # invalidated

Always assert both directions. A test that only checks "the cache was cleared"
passes just as well against a wildcard dependency, so it cannot tell you whether
your scoping works. Warm two programs, write to one, and assert the other
survives. Then confirm the test actually fails without your change -- a
dependency test that passes either way is telling you nothing.

For views decorated with ``@cached_module_view`` the cache object hangs off the
wrapper, but the attribute path depends on the other decorators: some are
reached as ``view.cached_function``, others as ``view.method.cached_function``.
Follow whatever the function's own dependency declarations use.

See ``esp/esp/program/tests_cache_scoping.py`` and
``esp/esp/program/tests_m2m_cache_deps.py`` for worked examples.

The Memcached Backend
---------------------

``esp.utils.memcached_multikey.CacheClass`` is the cache backend configured in
``CACHES['default']``. It wraps Django's ``PyMemcacheCache`` and adds two things
on top of it: 1) key shortening and 2) transparent chunking of large values.

Keys
~~~~

Memcached limits keys to 250 characters. ``make_key`` prefixes each key with
``CACHE_PREFIX`` and, if the result is still too long, replaces the overflow
with a SHA-256 hash of the original key.

Large values
~~~~~~~~~~~~

Memcached also refuses to store any single item larger than 1MB (its ``-I``
setting). Before chunking existed, a value over that limit simply failed to
cache, silently, every time it was written.

Values whose pickled form exceeds ``MEMCACHED_MULTIKEY_CHUNK_SIZE`` are now
split across several keys. The original key holds a small metadata string::

    __ESP_MULTIKEY_V1__:<chunk_count>:<digest>

and the chunks live under keys derived from a hash of the original key. Reads
fetch the chunks in a single batched ``get_many``, reassemble them, and verify
the digest before unpickling.

Anything that goes wrong on read is logged and turned into a cache miss,
forcing the caller to recompute.

Settings
~~~~~~~~

``MEMCACHED_MULTIKEY_CHUNK_SIZE``
    Bytes per chunk. Defaults to 900KB, which leaves headroom under memcached's
    default 1MB item limit. Lower this if memcached runs with a smaller ``-I``.

``MEMCACHED_MULTIKEY_MAX_CHUNKS``
    Refuse to cache anything needing more chunks than this. Defaults to 16
    (roughly 14MB). Without a ceiling, one runaway value can evict the entire
    cache; when the limit is hit the value is not cached and a warning is
    logged.

``MEMCACHED_MULTIKEY_CHUNK_TTL``
    Expiry applied to chunks when the configured ``TIMEOUT`` resolves to "never
    expire". Defaults to 24 hours. Chunks must always expire: ``delete()``
    removes only the metadata key, and shrinking a value strands its tail
    chunks, so unreachable chunks would otherwise occupy memcached until
    evicted.

Operational notes
~~~~~~~~~~~~~~~~~

Chunking makes it possible to cache values that previously failed outright, so
memcached will hold more data than before. Check that ``-m`` is large enough --
the stock Debian default is 64MB, which a handful of multi-megabyte values will
fill. Watch the ``evictions`` counter after deploying.

Note also that memcached's ``slab_chunk_max`` defaults to 512KB, so a 900KB
chunk spans two slab chunks and occupies about 1MB of slab space.

Because the metadata format is versioned, mixing old and new code against one
memcached is unsafe: code without chunking support reads the metadata key and
hands the raw ``__ESP_MULTIKEY_V1__:...`` string back to its caller. Flush the
cache (``manage.py flushcache``) when rolling back.

Finally, cached values are pickled, so a Python upgrade or a rename of a cached
class can invalidate them. Both degrade to cache misses rather than errors, but
flushing the cache is still the right move after either.
