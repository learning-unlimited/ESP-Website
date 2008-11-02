# system dependencies
from django.core.cache import cache
from django.db import models
from django.contrib.auth.models import User, AnonymousUser
import datetime
import random
import string


# esp dependencies
from django.db.models.query import Q
from esp.db.models.prepared import ProcedureManager
from esp.db.fields import AjaxForeignKey

# model dependencies
from esp.users.models import ESPUser
from esp.datatree.models import DataTree, QTree
from esp.datatree.util import tree_filter

# Cache introspection
from django.core.cache.backends.memcached import CacheClass as MemcachedClass



__all__ = ['UserBit','UserBitImplication']

ascii_set = string.lowercase + string.uppercase + string.digits + '/=\:;.<>'

class UserBitManager(ProcedureManager):

    """
    UserBit manager...implements all of the non row-level
    operations for the UserBit Model.

    Examples of operations:

       UserBit.objects.bits_get_verbs(user,qsc)

       ...
    """

    class UserBitCache(object):
        """
        Allows you to shortcut the userbit caching mechanism::

            value = UserBit.objects.cache(user)['key']
            UserBit.objects.cache(user)['key'] = 'new value'
        """

        # 1 hour minute caching
        cache_time = 3600

        def __init__(self, user=None):
            self.user = user

        def _get_random_string(self, length=7):
            """ It's slow, but this function will generate a very dense random object. 
            (26 * 2 + 10 + 8) ** 7 == 8235430000000 different possibilities.
            """
            return ''.join(random.choice(ascii_set) for x in range(length))

        def get_global_key(self):
            """ Return the global userbit key. """
            new_key = 'UB_%s' % self._get_random_string()

            # Using .add here is much safer than set.
            KEY = 'UserBit_global'
            cache.add(KEY, new_key, 86400)
            global_key = cache.get(KEY)

            return global_key or new_key

        def delete_global_key(self):
            """ Delete the global key. """
            cache.delete('UserBit_global')

        def get_key_to_get_user_key(self):
            """ Returns the key to get the user key. """
            user = self.user
            user_id = 'none'
            if hasattr(user, 'id') and user.id is not None:
                user_id = str(user.id)
            elif isinstance(user, int):
                user_id = str(user)

            global_key = self.get_global_key()
            user_key = '%s_user_%s' % (global_key, user_id)

            return str(user_key)

        def get_key_for_user(self):
            """
            Returns the key of the user, regardless of
            anything about the user object.
            """
            user_key = self.get_key_to_get_user_key()
            new_key = 'UB_u_%s' % self._get_random_string()
            # Using .add here is much safer than set.
            cache.add(user_key, new_key, 86400)
            current_key = cache.get(user_key)
            return current_key or new_key

        def update(self):
            """ Purges all userbit-related cache. """
            if self.user or (hasattr(self.user, 'id') and self.user.id is not None):
                cache.delete(self.get_key_to_get_user_key())
            else:
                self.delete_global_key()


        def _prefix_user_key(self, key):
            user_key = self.get_key_for_user()
            current_key = user_key + '_%s' % key
            return current_key[:200]

        def __getitem__(self, key):
            return cache.get(self._prefix_user_key(key))

        def __setitem__(self, key, value):
            cache.set(self._prefix_user_key(key), value, self.cache_time)

        def __delitem__(self, key):
            return cache.delete(self._prefix_user_key(key))


    cache = UserBitCache

    def user_has_TYPE(self, user, node, node_type='qsc'):
        """
        Returns true if the user has the verb anywhere. False otherwise.
        """
        node_id = getattr(node, 'id', node)
        col_filter = '%s__above' % node_type
        cache_key  = 'has_%s__%s' % (node_type, node_id)

        retVal = self.cache(user)['has_%s__%s' % (node_type, node_id)]

        if retVal is not None:
            return retVal
        else:
            
            retVal = bool(self.filter(QTree(**{col_filter: node_id}), user = user))
            self.cache(user)[cache_key] = retVal

        return retVal

    user_has_verb = lambda self,user,verb: self.user_has_TYPE(user, verb, node_type='verb')
    user_has_qsc  = lambda self,user,qsc : self.user_has_TYPE(user, qsc, node_type='qsc')

    def bits_get_users(self, qsc, verb, now=None, end_of_now=None, user_objs=False):
        """ Return all userbits for users who have been granted 'verb' on 'qsc'. """

        if now is None:
            now = datetime.datetime.now()
        if end_of_now is None:
            end_of_now = now
            
        if user_objs:
            #assert False, qsc
            from esp.users.models import ESPUser
            users = ESPUser.objects.filter_by_procedure('userbit__bits_get_user_real',
                                                qsc, verb, now, end_of_now)
            return users

        else:
            userbits = self.filter_by_procedure('userbit__bits_get_user', qsc, verb, now, end_of_now)
            return userbits


    @staticmethod
    def bits_get_TYPE(self, user, node, now = None, end_of_now = None, node_root=None, node_type='qsc'):
        """ Return all qsc structures to which 'user' has been granted 'verb'.
        If 'qsc_root' is specified, only return qsc structures at or below the specified node.
        """

        user_cache_id = 'bit_get_%s__%s,%s,%s,%s' % (node_type, node.id, now, end_of_now,
                                                     node_root)

        retVal = self.cache(user)[user_cache_id]
        if retVal is not None:
            return retVal

        if now is None:
            now = datetime.datetime.now()
        if end_of_now is None:
            end_of_now = now

        procedure_name = 'userbit__bits_get_%s' % node_type

        if node_root:
            procedure_name += '_root'

        #Django accepts "None" for .filter(foo=None) now, and it does requre a user object rather than an integer
        #if user is None:
        #    user = -10

        if hasattr(user, 'id') and user.id is None:
            user = None
        #    user = -10

        if node_root:
            userbits = self.filter_by_procedure(procedure_name, user, node, now, end_of_now, node_root)
        else:
            userbits = self.filter_by_procedure(procedure_name, user, node, now, end_of_now)

        list(userbits)

        self.cache(user)[user_cache_id] = userbits
        
        return userbits

    # ``Axiak for conservation of code 2008.''
    bits_get_verb = lambda self,user,qsc,now=None,end_of_now=None,verb_root=None: \
             self.bits_get_TYPE(self,user,qsc,now,end_of_now,verb_root,node_type='verb')
    bits_get_qsc  = lambda self,user,verb,now=None,end_of_now=None,qsc_root=None: \
             self.bits_get_TYPE(self,user,verb,now,end_of_now,qsc_root,node_type='qsc')

    def find_by_anchor_perms(self,Model,user,verb,qsc=None):
    	"""
        Fetch a list of relevant items for a given user
        and verb in a module that has an anchor foreign
        key into the DataTree
        """

        user_cache_key = 'fbap__model__%s.%s__%s,%s,%s' % (Model.__module__,
                                                        Model.__name__,
                                                        hasattr(user,'id') and user.id or user,
                                                        hasattr(verb,'id') and verb.id or verb,
                                                        hasattr(qsc,'id') and qsc.id or qsc)

        retVal = self.cache(user)[user_cache_key]

        if retVal is not None: return retVal

        q_list = self.bits_get_qsc( user, verb )

        res = None

        for bit in q_list:
            try:
                q = bit.qsc
            except DataTree.DoesNotExist, e:
                bit.delete()
                continue

            if bit.recursive:
                qsc_children_ids = [q.id] + [x['id'] for x in q.descendants(False).values('id')]
                query = Model.objects.filter(anchor__in = qsc_children_ids)
            else:
                query = Model.objects.filter(anchor=q)
                
            if qsc is not None:
                query = query.filter(QTree(anchor__below = qsc))

            if res == None:
                res = query
            else:
                res = res | query

        if res != None:
            retVal = res.distinct()

        if res == None:
            retVal = Model.objects.none().distinct()

        list(retVal) # force retVal to evaluate itself
        self.cache(user)[user_cache_key] = retVal

	# Operation Complete!
	return retVal

    def UserHasPerms(self, user, qsc, verb, now = None, recursive_required = False):
        """ Given a user, a permission, and a subject, return True if the user, or all users,
        has been Granted [subject] on [permission]; False otherwise """
        
        # aseering: This reeks of code redundancy; is there a way to combine the above and below loops into a single loop?
        # aseering 1-11-2007: Even better; single query!
        # axiak 5/26/07: This is very different now.
        # axiak 6/9/07:  It even uses plpgsql functions.

        ##########################
        # Set caching parameters #
        ##########################
        if now == None:
            now = datetime.datetime.now()
            now_id = "None"
        else:
            now_id = "-".join(str(i) for i in datetime.datetime.now().timetuple())

        if isinstance(qsc, basestring):
            qsc_cache = 'S' + qsc
            qsc_id = qsc
        elif hasattr(qsc, 'id'):
            qsc_id = qsc.id
            qsc_cache = 'ID' + str(qsc.id)
        else:
            qsc_cache = 'ID' + str(qsc)
            qsc_id = qsc

        if isinstance(verb, basestring):
            verb_cache = 'S' + verb
            verb_id = verb
        elif hasattr(verb, 'id'):
            verb_cache = 'ID' + str(verb.id)
            verb_id = verb.id
        else:
            verb_cache = 'ID' + str(verb)
            verb_id = verb

        ###########
        # Caching #
        ###########
        user_cache_id = 'UserHasPerms:%s,%s,%s,%s' % (qsc_cache,verb_cache,now_id,recursive_required)

        retVal = self.cache(user)[user_cache_id]

        if retVal is not None:
            return retVal

        ###########
        # Query   #
        ###########
        if isinstance(verb_id, basestring):
            try:
                verb_id = DataTree.get_by_uri(verb_id).id
            except DataTree.NoSuchNodeException:
                retVal = False

        if isinstance(qsc_id, basestring):
            try:
                qsc_id = DataTree.get_by_uriL(qsc_id).id
            except DataTree.NoSuchNodeException:
                retVal = False

        if retVal is not None:
            self.cache(user)[user_cache_id] = retVal
            return retVal
        
        if user is None:
            user = -10

        if hasattr(user, 'id') and user.id is None:
            user = -10


        retVal = self.values_from_procedure('userbit__user_has_perms', user, qsc_id, verb_id, now, recursive_required)

        retVal = retVal[0].values()[0]

        self.cache(user)[user_cache_id] = retVal

        return retVal


class UserBit(models.Model):

    """ Grant a user a bit on a Q

    # some tests...
    >>> from esp.users.models import UserBit
    >>> from django.contrib.auth.models import User
    >>> from esp.datatree.models import GetNode,DataTree
    >>> lennon = User.objects.create(username='jlennon',last_name='Lennon',first_name='John',email='jlennon@axiak.net')
    >>> ringo  = User.objects.create(username='ringos',last_name='Star',first_name='Star',email='ringos@axiak.net')
    >>> harrison = User.objects.create(username='harrison',last_name='Harrison',first_name='George',email='harrison@axiak.net')
    >>> paul = User.objects.create(username='paul',last_name='McCartney',first_name='Paul',email='paulm@axiak.net')
    >>> root = DataTree.root()
    >>> root
    <DataTree: / (0--1)>

    # first some nouns
    >>> something = GetNode('Q/Albums/60s/Beatles/Abbey_Road/Something')
    >>> something
    <DataTree: Q/Albums/60s/Beatles/Abbey_Road/Something (6--7)    >>> darling = GetNode('Q/Albums/60s/Beatles/Abbey_Road/OhDarling')
    >>> for i in range(10):
    ...     song = GetNode('Q/Albums/Misc/Unknown%s/%s' % (i,i*5-1))
    ...
    >>> song
    <DataTree: Q/Albums/Misc/Unknown9/44 (53--54)>

    # now some verbs
    >>> GetNode('V/Produce')
    <DataTree: V/Produce (108--109)>
    >>> GetNode('V/Produce/Label')
    <DataTree: V/Produce/Label (109--110)>
    >>> GetNode('V/Listen')
    <DataTree: V/Listen (112--113)>
    >>> GetNode('V/Police/DMCA')
    <DataTree: V/Police/DMCA (115--116)>
    >>> GetNode('V/Produce/Label/Digitize')
    <DataTree: V/Produce/Label/Digitize (110--111)>

    >>> lennon.userbit_set.add(UserBit(verb = GetNode('V/Produce'), qsc=GetNode('Q/Albums/60s')))
    >>> UserBit.objects.create(verb = GetNode('V/Purchase'), qsc=GetNode('Q/Albums'))
    <UserBit: GRANT V/Purchase ON Q/Albums TO Everyone>
    >>> UserBit.objects.UserHasPerms(user=ringo,qsc=GetNode('Q/Albums/60s/Beatles/Abbey_Road'), verb = GetNode('V/Purchase'))
    True
    >>> UserBit.objects.UserHasPerms(user=ringo,qsc=GetNode('Q/Albums/60s/Beatles/Abbey_Road'), verb = GetNode('V/Purchase/Online'))
    True
    >>> UserBit.objects.UserHasPerms(user=ringo,qsc=GetNode('Q/Albums/60s/Beatles/Abbey_Road'), verb = GetNode('V/Sell'))
    False
    >>> UserBit.objects.UserHasPerms(user=lennon,qsc=GetNode('Q/Albums/60s/Beatles/Abbey_Road'), verb = GetNode('V/Produce'))
    True
    >>> UserBit.objects.UserHasPerms(user=ringo,qsc=GetNode('Q/Albums/60s/Beatles/Abbey_Road'), verb = GetNode('V/Produce'))
    False
    # test cache-spoiling
    >>> UserBit.objects.bits_get_verb(user=lennon,qsc=GetNode('Q/Albums/60s/Beatles'))[0].delete()
    >>> UserBit.objects.UserHasPerms(user=ringo,qsc=GetNode('Q/Albums/60s/Beatles/Abbey_Road'), verb = GetNode('V/Produce'))
    False

    >>> UserBit.objects.bits_get_qsc(user=ringo,verb=GetNode('V/Purchase'))
    [<UserBit: GRANT V/Purchase ON Q/Albums TO Everyone>]
    >>> UserBit.objects.bits_get_qsc(user=ringo,verb=GetNode('V/Purchase'))
    [<UserBit: GRANT V/Purchase ON Q/Albums TO Everyone>]
    >>> UserBit.objects.bits_get_qsc(user=ringo,verb=GetNode('V/Purchase'),qsc_root=GetNode('Q'))
    [<UserBit: GRANT V/Purchase ON Q/Albums TO Everyone>]
    >>> UserBit.objects.bits_get_qsc(user=ringo,verb=GetNode('V/Purchase'),qsc_root=GetNode('Q/Albums'))
    [<UserBit: GRANT V/Purchase ON Q/Albums TO Everyone>]
    >>> UserBit.objects.bits_get_qsc(user=ringo,verb=GetNode('V/Purchase'),qsc_root=GetNode('Q/Albums/60s'))
    []
    >>> UserBit.objects.bits_get_qsc(user=ringo,verb=GetNode('V/Purchase'),qsc_root=GetNode('Q/Books'))
    []
    >>> UserBit.objects.all().delete()
    # FIXME: make this not break.
    >>> UserBit.objects.bits_get_qsc(user=ringo,verb=GetNode('V/Purchase'),qsc_root=GetNode('Q/Albums'))
    [<UserBit: GRANT V/Purchase ON Q/Albums TO Everyone>]
    >>> UserBit.objects.create(verb = GetNode('V/Purchase'), qsc=GetNode('Q/Albums'))
    <UserBit: GRANT V/Purchase ON Q/Albums TO Everyone>
    >>> [ubit.delete() for ubit in UserBit.objects.all()]
    [None]
    >>> UserBit.objects.bits_get_qsc(user=ringo,verb=GetNode('V/Purchase'),qsc_root=GetNode('Q/Albums'))
    []
    """
    user = AjaxForeignKey(ESPUser, 'id', blank=True, null=True, default=None) # User to give this permission
    qsc = AjaxForeignKey(DataTree, related_name='userbit_qsc') # Controller to grant access to
    verb = AjaxForeignKey(DataTree, related_name='userbit_verb') # Do we want to use Subjects?

    startdate = models.DateTimeField(blank=True, null=True, default = datetime.datetime.now)
    enddate = models.DateTimeField(blank=True, null=True)
    recursive = models.BooleanField(default=True)

    objects = UserBitManager()

    class Meta:
        app_label = 'users'
        db_table = 'users_userbit'

    def __unicode__(self):
        
        
        def clean_node(node):
            if hasattr(node, 'uri'):
                return node.uri
            return '?'

        if self.user is None:
            user = 'Everyone'
        else:
            user = self.user.username

        if self.recursive:
            recurse = ""
        else:
            recurse = " (non-recursive)"
        
        if self.startdate != None and self.enddate != None:
            return 'GRANT %s ON %s TO %s <%s--%s>%s' % (clean_node(self.verb), clean_node(self.qsc),
                                                        user, self.startdate, self.enddate, recurse)
        else:
            return 'GRANT %s ON %s TO %s%s' % (clean_node(self.verb), clean_node(self.qsc),
                                               user, recurse)

    def save(self):
        super(UserBit, self).save()

        if not hasattr(self.user,'id') or self.user.id is None:
            UserBit.updateCache(None)
        else:
            UserBit.updateCache(self.user.id)


        UserBitImplication.addUserBit(self) # follow implications

    def delete(self):
        super(UserBit, self).delete()

        if not hasattr(self.user,'id') or self.user.id is None:
            UserBit.updateCache(None)
        else:
            UserBit.updateCache(self.user.id)

        
        UserBitImplication.deleteUserBit(self) #follow implications

    def expire(self):
        self.enddate = datetime.datetime.now()
        self.save()

    def updateCache(cls, user_id):
        cls.objects.cache(user_id).update()
    updateCache = classmethod(updateCache)

    @classmethod
    def time_cache(cls):
        from django.contrib.auth.models import User
        from esp.datatree.models import DataTree, GetNode
        import time

        axiak = User.objects.get(username='axiak')
        splash = GetNode('Q/Programs/Splash/2007')

        num_trials = 1000
        verbs = UserBit.objects.bits_get_verb(axiak, splash)
        old_time = time.time()

        for i in range(num_trials):
            verbs = UserBit.objects.bits_get_verb(axiak, splash)
        print "Finished %s trials in %0.4f milliseconds per trial." % (num_trials, 1000* (time.time() - old_time) / num_trials)

    @staticmethod
    def has_bits(queryset):
        """ Returns False if there are no elements in queryset """
        return ( len(queryset.values('id')[:1]) > 0 )

    @staticmethod
    def not_expired(prefix='', when=None):
        """ Returns a Q object for field prefix being valid at time when """
        if when is None:
            when = datetime.datetime.now()
        if prefix is not '' and not prefix.endswith('__'):
            prefix += '__'
        q = Q(**{prefix+'startdate__isnull': True}) | Q(**{prefix+'startdate__lte': when})
        q = q & (Q(**{prefix+'enddate__isnull': True}) | Q(**{prefix+'enddate__gte': when}))
        return q

    @staticmethod
    def valid_objects(when=None):
        """ Returns a QuerySet consisting of unexpired UserBits (at time when) """
        return UserBit.objects.filter(UserBit.not_expired(when=when))

    UserHasPerms   = classmethod(lambda cls,*args,**kwargs: cls.objects.UserHasPerms(*args,**kwargs))
    bits_get_qsc   = classmethod(lambda cls,*args,**kwargs: cls.objects.bits_get_qsc(*args,**kwargs))
    bits_get_users = classmethod(lambda cls,*args,**kwargs: cls.objects.bits_get_users(*args,**kwargs))
    bits_get_verb  = classmethod(lambda cls,*args,**kwargs: cls.objects.bits_get_verb(*args,**kwargs))
    find_by_anchor_perms = classmethod(lambda cls,*args,**kwargs: cls.objects.find_by_anchor_perms(*args,**kwargs))


#######################################
# UserBitImplications do scary things #
#######################################




class UserBitImplication(models.Model):
    """ This model will create implications for userbits...
      that is, if a user has A permission, they will get B """
    
    qsc_original  = AjaxForeignKey(DataTree, related_name = 'qsc_original',  blank=True, null=True)
    verb_original = AjaxForeignKey(DataTree, related_name = 'verb_original', blank=True, null=True)
    qsc_implied   = AjaxForeignKey(DataTree, related_name = 'qsc_implied',   blank=True, null=True)
    verb_implied  = AjaxForeignKey(DataTree, related_name = 'verb_implied',  blank=True, null=True)
    recursive     = models.BooleanField(default = True)
    created_bits  = models.ManyToManyField(UserBit, blank=True, null=True)

    class Meta:
        app_label = 'users'
        db_table = 'users_userbitimplication'


    def __unicode__(self):
        var = {}
        for k in ['verb_original_id', 'qsc_original_id',
                  'verb_implied_id',  'qsc_implied_id' ]:
            if getattr(self, k) is None:
                var[k[:-3]] = '*'
            else:
                var[k[:-3]] = str(getattr(self, k[:-3]))
                
        string = '%s on %s ==> %s on %s' % \
                 (var['verb_original'], var['qsc_original'],
                  var['verb_implied'],  var['qsc_implied'])
        
        if self.recursive:
            string += ' (recursive)'
        return string


    @staticmethod
    def get_under_bit(userbit):
        """ Return all implications under a userbit.
        That is, the set of all A ==> B such that A is true
        because of userbit. """
        Q_qsc_null  = Q(qsc_original__isnull = True)
        Q_verb_null = Q(verb_original__isnull = True)
        
        if not userbit.recursive:
            Q_qsc  = Q(qsc_original  = userbit.qsc)
            Q_verb = Q(verb_original = userbit.verb)
        else:
            Q_qsc  = QTree(qsc__original__below = userbit.qsc_id)

            Q_verb = QTree(verb_original__below = userbit.verb_id)

        # if one of the two are null, the other one can match and it'd be fine.
        Q_match = (Q_qsc & Q_verb) | (Q_qsc_null & Q_verb) | (Q_qsc & Q_verb_null)
        
        return UserBitImplication.objects.filter(Q_match).distinct()
                       

    @staticmethod
    def deleteUserBit(old_userbit):
        """ Delete all the userbits that depended on this one.
            This should be executed *after* a userbit has been deleted.
            (i.e. this should be run from UserBit.delete() 
        """
        implications = UserBitImplication.get_under_bit(old_userbit)

        # first we go through all implications
        for implication in implications:
            # now we get all the bits this implication created
            for bit in implication.created_bits.all():
                # if there is no other way this implication is valid for this user
                # delete...
                if not UserBit.UserHasPerms(user = bit.user,
                                            qsc  = old_userbit.qsc,
                                            verb = old_userbit.verb):
                    bit.delete()
        
        
    def impliedBit(self, originalBit):
        """ Returns the implied userbit if a bit is given. """
        qsc_implied = self.qsc_implied
        verb_implied = self.verb_implied

        if qsc_implied is None:
            qsc_implied = originalBit.qsc
        if verb_implied is None:
            verb_implied = originalBit.verb
        return UserBit(user = originalBit.user,
                       qsc  = qsc_implied,
                       verb = verb_implied,
                       recursive = self.recursive,
                       enddate = originalBit.enddate)


    @staticmethod
    def addUserBit(userbit):
        """ This will check to see if the addition of this userbit
            should force other userbits to be created via implications.
        """
        implications = UserBitImplication.get_under_bit(userbit)

        for implication in implications:
            newbit = implication.impliedBit(userbit)

            newbit.save()

            implication.created_bits.add(newbit)
            implication.save()

    def save(self):
        super(UserBitImplication, self).save()

        self.apply()
    
    def delete(self):
        for bit in self.created_bits.all():
            bit.delete()
            
        super(UserBitImplication, self).delete()



    def apply(self):
        " This will generate the userbits for this implication. "
        if self.qsc_original_id is None and self.verb_original_id is None:
            return
        if self.qsc_original_id is not None:
            Q_qsc = (QTree(qsc__above = self.qsc_original) &\
                     Q(recursive       = True)) \
                     | \
                     Q(qsc = self.qsc_original_id)
            
        if self.verb_original_id is not None:
            Q_verb = (QTree(verb__above = self.verb_original) &\
                      Q(recursive       = True)) \
                      | \
                      Q(verb = self.verb_original_id)

        userbits = UserBit.objects

        if self.qsc_original_id is not None:
            userbits = userbits.filter(Q_qsc)
        if self.verb_original_id is not None:
            userbits = userbits.filter(Q_verb)
        
        
        for userbit in userbits:
            # for each userbit we're going to create the correct
            # corresponding userbits.

            newbit = self.impliedBit(userbit) # get this bit this implies

            bits = UserBit.objects.filter(user = newbit.user,
                                          qsc  = newbit.qsc,
                                          verb = newbit.verb)
            if self.recursive:
                bits.filter(recursive = True)

            if len(bits.values('id')[:1]) == 0:
                newbit.save()
                self.created_bits.add(newbit)
                self.save()
        
    @staticmethod
    def applyAllImplications():
        """ This function will make implications work, no matter what.
          In the entire tree.
        """
        for implication in UserBitImplication.objects.all():
            implication.apply()

