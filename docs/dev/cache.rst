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
functions as-need. Also, such functions really shouldn't have
side-effects. Split up your functions if needed. Conceptually, each
cache maps keys to values, where keys correspond to function
arguments. The caches can invalidate keys in bulk by sets of keys, and
propagate invalidations up to dependant caches. We limit the types of
key sets that may be expressed so that this is implementable.


Invalidation Strategy
---------------------

Internally, invalidations are done by maintaining a signature along
with each cache entry. Before returning a value, we check that this
signature is current. If not, we pretend the value was never there in
the first place. This signature is computed from other cache values
called tokens which are shared so that, by reseting a particular
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
cache paramterized by a list of arguments. It exports a similar API to
Django's cache objects, but the keys are lists of Python objects
rather than strings. The marinade module (as a pun a Python's pickle)
handles stringifying these objects. In addition, ArgCache provides
methods to register dependencies and delete_key_set, which takes a
key_set and deletes everything in it. It may fallback on deleting more
if needbe (in the case that it lacks a Token for the job). Upon
deletion, it emits a signal with the key_set, so that other ArgCaches
may listen and react appropriately.


Key sets
--------

Key sets are represented by dictionaries. (We could use lists, but for
convenience, the names of the arguments are incorporated.) They map
the arguments of an ArgCache (by name) to sets of objects. You can
think of them as Cartesian products of these sets by
argument. Currently, the only expressable sets are wildcard (that is,
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
