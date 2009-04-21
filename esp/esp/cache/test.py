from esp.miniblog.models import Entry, AnnouncementLink
#from esp.cache.tokened import FuncTokenedCache
from esp.cache.argcache import ArgCache, cache_function
from esp.cache.key_set import wildcard, is_wildcard
from esp.cache.function import describe_func

cacheA = ArgCache('cacheA', ('param1', 'param2', 'param3'))
# Make handlers
cacheA.get_or_create_token(('param1',))
cacheA.get_or_create_token(('param2',))
cacheA.get_or_create_token(('param3',))
cacheA.get_or_create_token(('param1','param3',))

cacheB = ArgCache('cacheB', ('monkey', 'frogs'))
# Make handlers
cacheB.get_or_create_token(('monkey',))
cacheB.get_or_create_token(('frogs',))

# Too bad Python's lambda is annoying
# Well, this could probably be done with and/or... meh
def AtoB(param1=wildcard, param3=wildcard, **kwargs):
    if param3 == 'a' or is_wildcard(param3):
        return {'frogs': param1}
    else:
        return None
cacheB.depend_on_cache(cacheA, AtoB)
cacheB.run_all_delayed()


# The above dependency should be something like...
# B is [cacheA(param1=frogs, param2='a', param3=i) for i in possible_values_of_param3].twiddled_by_in_some_way(monkey)
#
# So, inverting, if param2 is not 'a', we don't care. param1's value gets put
# into frogs, things are invalidated regardless of param2, and all values of
# monkey is affected.
#
# We can optionally be more explicit and write return {'frogs': param1,
# 'monkey': wildcard}, but missing keys are interpreted as wildcards

argsA = [(1,1,'a'),
         (1,2,'a'),
         (1,3,'a'),
         (2,1,'a'),
         (2,2,'b'),
         (2,3,'b'),
         (3,1,'b'),
         (3,2,'b'),
         (3,3,'b'),]

argsB = [(1,1),
         (1,2),
         (1,3),
         (2,1),
         (2,2),
         (2,3),
         (3,1),
         (3,2),
         (3,3)]

for i,args in enumerate(argsA):
    print "Setting A to", i, "at", args
    cacheA.set(args, i)
for args in argsA:
    print "A", args, '=', cacheA.get(args)
print "Deleting A at (*,2,'b')..."
print "We don't have a token at param2,param3, so it should delete too much."
cacheA.delete_key_set(param2=2, param3='b')
for args in argsA:
    print "A", args, '=', cacheA.get(args)
print 
print "Reseting..."
for i,args in enumerate(argsA):
    print "Setting A to", i, "at", args
    cacheA.set(args, i)
print "Deleting A at (2,*,'b')..."
cacheA.delete_key_set(param1=2, param3='b')
for args in argsA:
    print "A", args, '=', cacheA.get(args)
print 
print "Reseting..."
for i,args in enumerate(argsA):
    print "Setting A to", i, "at", args
    cacheA.set(args, i)
print
print "Now we init stuff into B..."


argsB = [(1,1),
         (1,2),
         (1,3),
         (2,1),
         (2,2),
         (2,3),
         (3,1),
         (3,2),
         (3,3),]
for i,args in enumerate(argsB):
    print "Setting B to", i, "at", args
    cacheB.set(args, i)
for args in argsB:
    print "B", args, '=', cacheB.get(args)
print "And now we delete stuff from A again... Let's delete everything with param3 = 'b'"
print "B should be unaffected."
cacheA.delete_key_set(param3 = 'b')
for args in argsA:
    print "A", args, '=', cacheA.get(args)
for args in argsB:
    print "B", args, '=', cacheB.get(args)
print 
print "Reseting..."
for i,args in enumerate(argsA):
    print "Setting A to", i, "at", args
    cacheA.set(args, i)
print "And now we delete stuff from A: param1 = 1"
cacheA.delete_key_set(param1 = 1)
for args in argsA:
    print "A", args, '=', cacheA.get(args)
for args in argsB:
    print "B", args, '=', cacheB.get(args)
print
print "Reseting..."
for i,args in enumerate(argsA):
    print "Setting A to", i, "at", args
    cacheA.set(args, i)
for i,args in enumerate(argsB):
    print "Setting B to", i, "at", args
    cacheB.set(args, i)
print "What about (*,*,'a'), should kill (*,*) in B"
cacheA.delete_key_set(param3 = 'a')
for args in argsA:
    print "A", args, '=', cacheA.get(args)
for args in argsB:
    print "B", args, '=', cacheB.get(args)

# decorator will be renamed...
@cache_function
def sum_stuff(a_id, e_id):
    # simulate expensive op...
    a = 0
    for i in range(1000000):
        a += 5
    return AnnouncementLink.objects.get(id=a_id).title + " " + Entry.objects.get(id=e_id).title + str(a)
sum_stuff.depend_on_row(AnnouncementLink, 'a_id')
sum_stuff.depend_on_row(Entry, 'e_id')


@cache_function
def sum_stuff_len(a_id, e_id):
    return len(sum_stuff(a_id, e_id))
sum_stuff_len.depend_on_cache(sum_stuff, lambda a_id=wildcard, e_id=wildcard: {'a_id':a_id, 'e_id':e_id})



class Argh:

    def foo():
        pass

    @cache_function
    def sum_stuff(self, a_id, e_id):
        # simulate expensive op...
        a = 0
        for i in range(1000000):
            a += 5
        return AnnouncementLink.objects.get(id=a_id).title + " " + Entry.objects.get(id=e_id).title + str(a)
    sum_stuff.depend_on_row(AnnouncementLink, 'a_id')
    sum_stuff.depend_on_row(Entry, 'e_id')

    @cache_function
    def sum_stuff_static(a_id, e_id):
        # simulate expensive op...
        a = 0
        for i in range(1000000):
            a += 5
        return AnnouncementLink.objects.get(id=a_id).title + " " + Entry.objects.get(id=e_id).title + str(a)
    sum_stuff_static.depend_on_row(AnnouncementLink, 'a_id')
    sum_stuff_static.depend_on_row(Entry, 'e_id')
    # This kind of works, except that you lose access to generated API
    # and I can't magically forward it and stuff. It's sad...
    sum_stuff_static = staticmethod(sum_stuff_static)

    def __marinade__(self):
        return ""

d = Argh()
