from django.db import models
from django.contrib.auth.models import User, AnonymousUser
from esp.datatree.models import DataTree, PermToString, GetNode, StringToPerm
#from peak.api import security, binding
from esp.workflow.models import Controller
from datetime import datetime
from django.db.models import Q
from esp.dblog.models import error
from django.db.models.query import QuerySet
from esp.lib.EmptyQuerySet import EMPTY_QUERYSET

class ESPUser(User, AnonymousUser):
    """ Create a user of the ESP Website
    This user extends the auth.User of django"""

    # this will allow a casting from User to ESPUser:
    #      foo = ESPUser(bar)   <-- foo is now an ``ESPUser''
    def __init__(self, userObj):
        self.__dict__ = userObj.__dict__

    def getVisible(self, objType):
        return UserBit.find_by_anchor_perms(objType, self, GetNode('V/Flags/Public'))

    def getEditable(self, objType):
        return UserBit.find_by_anchor_perms(objType, self, GetNode('V/Administer/Edit'))

    def getTaughtClasses(self):
        from esp.program.models import Class
        return UserBit.find_by_anchor_perms(Class, self, GetNode('V/Flags/Registration/Teacher'))

    def getEnrolledClasses(self):
        from esp.program.models import Class
        Conf = UserBit.find_by_anchor_perms(Class, self, GetNode('V/Flags/Registration/Confirmed'))
        Prel = UserBit.find_by_anchor_perms(Class, self, GetNode('V/Flags/Registration/Preliminary'))

        return (Conf | Prel).distinct()
        
    def canAdminister(self, nodeObj):
        return UserBit.UserHasPerms(self, nodeObj.anchor, GetNode('V/Administer'))

    def isTeacher(self):
        """Returns true if this user is a teacher"""
        return UserBit.UserHasPerms(self, GetNode('Q'), GetNode('V/Flags/UserRole/Teacher'),datetime.now())

    def canEdit(self, nodeObj):
        """Returns True or False if the user can edit the node object"""
        # Axiak
        return UserBit.UserHasPerms(self, nodeObj.anchor, GetNode('V/Administer/Edit'))

    def getMiniBlogEntries(self):
        """Return all miniblog posts this person has V/Subscribe bits for"""
        # Axiak 12/17
        from esp.miniblog.models import Entry
        return UserBit.find_by_anchor_perms(Entry, self, GetNode('V/Subscribe')).order_by('-timestamp')

    @staticmethod
    def isUserNameValid(username, checkForDuplicate = False):
        """Return true if the username is valid, a list of strings representing the error if it isn't"""
        #axiak 12-17
        errors = []
        validalphabet = "abcdefghijklmnopqrstuvwxyz _0123456789"
        if len(username) < 4:
            errors.append('is too short')
        if len(username) > 12:
            errors.append('is too long')
        #invalid characters
        if len(set(username.lower()) - set(validalphabet)) > 0:
            errors.append('contains invalid characters')

        if checkForDuplicate and User.objects.filter(username=username.lower()).count() > 0:
            errors.append('is already in use')
            
        if len(errors) == 0:
            return True
        else:
            return errors

    @staticmethod
    def isPasswordValid(password):
        """Return true if the password is valid, a list of strings representing the errors if it isn't"""
        #axiak 12-17
        errors = []
        if len(password) < 4:
            errors.append('is too short')
        if len(password) > 12:
            errors.append('is too long')

        if len(errors) == 0:
            return True
        else:
            return errors



class UserBit(models.Model):
    """ Grant a user a bit on a Q """
    user = models.ForeignKey(User, blank=True, null=True) # User to give this permission
    qsc = models.ForeignKey(DataTree, related_name='permission_related_field') # Controller to grant access to
    verb = models.ForeignKey(DataTree, related_name='subject_related_field') # Do we want to use Subjects?

    startdate = models.DateTimeField(blank=True, null=True)
    enddate = models.DateTimeField(blank=True, null=True)

    recursive = models.BooleanField(default=True)

    def __str__(self):
        curr_user = '?'
        curr_qsc = '?'
        curr_verb = '?'

        try:
            if self.user is None:
                curr_user = 'Everyone'
            else:
                curr_user = str(self.user)
        except Exception:
            pass

        try:
            curr_qsc = PermToString(self.qsc.tree_encode())
        except Exception:
            pass

        try:
            curr_verb = PermToString(self.verb.tree_encode())
        except Exception:
            pass

        if self.recursive:
            recurse = ""
        else:
            recurse = " (non-recursive)"
        
        if self.startdate != None and self.enddate != None:
            return 'GRANT ' + curr_user + ' ' + curr_verb + ' ON ' + curr_qsc + ' <' + str(self.startdate) + ' - ' + str(self.enddate) + '>' + recurse
        else:
            return 'GRANT ' + curr_user + ' ' + curr_verb + ' ON ' + curr_qsc + recurse

    @staticmethod
    def UserHasPerms(user, qsc, verb, now = datetime.now()):
        """ Given a user, a permission, and a subject, return True if the user, or all users, has been Granted [subject] on [permission]; False otherwise """
	test = []
        if user != None and type(user) != AnonymousUser:
            for bit in user.userbit_set.all().filter(Q(startdate__isnull=True) | Q(startdate__lte=now), Q(enddate__isnull=True) | Q(enddate__gt=now)):
                test.append(bit)
                if ((bit.recursive and bit.qsc.is_descendant(qsc)) or bit.qsc == qsc) and ((bit.recursive and bit.verb.is_descendant(verb)) or bit.verb == verb):
                    return True

            # This reeks of code redundancy; is there a way to combine the above and below loops into a single loop?
        for bit in UserBit.objects.filter(user__isnull=True).filter(Q(startdate__isnull=True) | Q(startdate__lte=now), Q(enddate__isnull=True) | Q(enddate__gt=now)):
            test.append(bit)
            if ((bit.recursive and bit.qsc.is_descendant(qsc)) or bit.qsc == qsc) and ((bit.recursive and bit.verb.is_descendant(verb)) or bit.verb == verb):
                return True

        return False
    
    # FIXME: This looks like it has been subject to extreme code rot
    @staticmethod
    def enforce_bits(controller_class, user):
        def call(proc, *args):
            """ Accepts a 'run' function, its associated Controller class (is there a way to getthat information automatically, from the function?), and a user; returns a function that runs the 'run' function and returns 'true' if the user can access this Controller class, and returns 'false' otherwise. """
            proc(args)
            return True

        if UserBit.objects.filter(permission__controller=controller_class.__name__).filter(user_pk=user.id).count() != 0:
            return decorator(call)
        else:
            return lambda : False

    @staticmethod
    def bits_get_users(qsc, verb, now = datetime.now(), end_of_now = None):
        """ Return all users who have been granted 'verb' on 'qsc' """
        if end_of_now == None: end_of_now = now

        #	Hopefully it's easier to understand this query now...
        Q_correct_userbit = Q(recursive = True, verb__rangestart__lte = verb.rangestart, verb__rangeend__gte = verb.rangeend)
        Q_correct_qsc = Q(qsc=qsc)
        Q_exact_match = Q(recursive = False, verb=verb, qsc=qsc)
        Q_after_start = Q(startdate__isnull = True) | Q(startdate__lte = end_of_now)
        Q_before_end = Q(enddate__isnull = True) | Q(enddate__gte = now)
		
        users = UserBit.objects.filter(Q_exact_match).filter(Q_after_start).filter(Q_before_end) | UserBit.objects.filter(Q_correct_qsc).filter(Q_correct_userbit).filter(Q_after_start).filter(Q_before_end)

        return users.distinct()
    

    @staticmethod
    def bits_get_qsc(user, verb, now = datetime.now(), end_of_now = None, qsc_root=None):
        """  Return all qsc structures to which 'user' has been granted 'verb'

        If 'qsc_root' is specified, only return qsc structures at or below the specified node """
        if end_of_now == None: end_of_now = now

        #	Hopefully it's easier to understand this query now...
        Q_correct_userbit = Q(recursive = True, verb__rangestart__lte = verb.rangestart, verb__rangeend__gte = verb.rangeend)
        Q_exact_match = Q(recursive = False, verb__pk = verb.id)
        Q_correct_user = Q(user__isnull = True) | Q(user__pk = user.id)
        Q_after_start = Q(startdate__isnull = True) | Q(startdate__lte = end_of_now)
        Q_before_end = Q(enddate__isnull = True) | Q(enddate__gte = now)
		
        if (UserBit.objects.filter(Q_correct_userbit).count() == 0):
            qscs = UserBit.objects.filter(Q_exact_match).filter(Q_correct_user).filter(Q_after_start).filter(Q_before_end)
        else:
            qscs = UserBit.objects.filter(Q_correct_userbit).filter(Q_correct_user).filter(Q_after_start).filter(Q_before_end)

        if qsc_root == None:
            return qscs.distinct()
        else:
            return qscs.filter(qsc__rangestart__gte=qsc_root.rangestart, qsc__rangeend__lte=qsc_root.rangeend).distinct()

    @staticmethod
    def bits_get_verb(user, qsc, now = datetime.now(), end_of_now = None):
        """ Return all verbs that 'user' has been granted on 'qsc' """
        if end_of_now == None: end_of_now = now

        #	Hopefully it's easier to understand this query now...
        Q_correct_userbit = Q(recursive = True, qsc__rangestart__lte = qsc.rangestart, qsc__rangeend__gte = qsc.rangeend)
        Q_exact_match = Q(recursive = False, qsc__pk = qsc.id)
        Q_correct_user = Q(user__isnull = True) | Q(user__pk = user.id)
        Q_after_start = Q(startdate__isnull = True) | Q(startdate__lte = end_of_now)
        Q_before_end = Q(enddate__isnull = True) | Q(enddate__gte = now)
		
        if (UserBit.objects.filter(Q_correct_userbit).count() == 0):
            verbs = UserBit.objects.filter(Q_exact_match).filter(Q_correct_user).filter(Q_after_start).filter(Q_before_end).distinct()
        else:
            verbs = UserBit.objects.filter(Q_correct_userbit).filter(Q_correct_user).filter(Q_after_start).filter(Q_before_end).distinct()

        return verbs
        
        #return UserBit.objects.filter(Q(recursive=True, qsc__rangestart__gte=qsc.rangestart, qsc__rangeend__lte=qsc.rangeend) | Q(qsc__pk=qsc.id)).filter(Q(user__isnull=True)|Q(user__pk=user.id)).filter(Q(startdate__isnul=True) | Q(startdate__lte=end_of_now), Q(enddate__isnull=True) | Q(enddate__gte=now))

    @staticmethod
    def has_bits(queryset):
        """ Returns False if there are no elements in queryset """
        return ( queryset.count() > 0 )

    @staticmethod
    def find_by_anchor_perms(module,user,verb,qsc=None):
    	""" Fetch a list of relevant items for a given user and verb in a module that has an anchor foreign key into the DataTree """
    	q_list = [ x.qsc for x in UserBit.bits_get_qsc( user, verb ) ]

    	# Extract entries associated with a particular branch

        res = None

        for q in q_list:
            query = module.objects.filter(anchor__rangestart__gte = q.rangestart, anchor__rangestart__lt = q.rangeend)
            if qsc is not None:
                query = query.filter(anchor__rangestart__gte=qsc.rangestart, anchor__rangeend__lte=qsc.rangeend)

            if res == None:
                res = query
            else:
                res = res | query

        if res != None:
            res = res.distinct()

        if res == None:
            return EMPTY_QUERYSET

	# Operation Complete!
	return res

    class Admin:
        pass

    

    
class ContactInfo(models.Model):
	""" ESP-specific contact information for (possibly) a specific user """
	user = models.ForeignKey(User, blank=True, null=True)
	full_name = models.CharField(maxlength=256)
	dob = models.DateField(blank=True, null=True)
	graduation_year = models.PositiveIntegerField(blank=True, null=True)
	e_mail = models.EmailField(blank=True, null=True)
	phone_day = models.PhoneNumberField(blank=True, null=True)
	phone_cell = models.PhoneNumberField(blank=True, null=True)
	phone_even = models.PhoneNumberField(blank=True, null=True)
	address_street = models.CharField(maxlength=100)
	address_city = models.CharField(maxlength=50)
	address_state = models.USStateField()
	address_zip = models.CharField(maxlength=5)

	def __str__(self):
            username = ""
            if self.user != None:
                username = self.user.username
                
            return self.full_name + ' (' + username + ')'
	
	class Admin:
		pass

def GetNodeOrNoBits(nodename, user = AnonymousUser(), verb = None):
    """ Get the specified node.  Create it only if the specified user has create bits on it """

    if verb == None:
        verb = GetNode("V/Administer/Program/Class")

    nodes = DataTree.objects.filter(name='ROOT', parent__isnull=True)
    node = None
    if nodes.count() < 1L:
        error("Trying to create a new root node here.  Dying...")
        assert False, "Trying to create a new root node here.  Dying..."
        node = DataTree()
        node.name = 'ROOT'
        node.parent = None
        node.save()
    elif nodes.count() == 1L:
        node = nodes[0]
    else:
        raise DataTree.NoRootNodeException(nodes.count())
    
    perm = StringToPerm(nodename)
    if nodename == '':
        perm = []

    try:
        return node.tree_decode(perm)
    except DataTree.NoSuchNodeException, e:
        if UserBit.UserHasPerms(user, e.anchor, verb):
            return e.anchor.tree_create(e.remainder)
        else:
            raise

